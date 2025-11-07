#!/bin/bash
#
# 네트워크 와치독 (Network Watchdog)
# 메인 이더넷 연결이 끊기면 자동으로 복구
#
# 사용법:
#   ./network_watchdog.sh
#
# 백그라운드 실행:
#   nohup ./network_watchdog.sh > /tmp/network_watchdog.log 2>&1 &
#

# 설정
CHECK_INTERVAL=60           # 체크 주기 (초)
PING_TARGET="8.8.8.8"       # ping 테스트 대상
PING_COUNT=3                # ping 시도 횟수
FAIL_THRESHOLD=3            # 연속 실패 임계값
MAIN_GATEWAY="121.172.70.254"  # 메인 게이트웨이
MAIN_INTERFACE="enp4s0"     # 메인 인터페이스

# 상태 변수
consecutive_failures=0
log_file="/tmp/network_watchdog.log"

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$log_file"
}

# 네트워크 체크 함수
check_network() {
    # 1. Ping 테스트
    if ping -c "$PING_COUNT" -W 2 "$PING_TARGET" > /dev/null 2>&1; then
        return 0  # 정상
    fi

    # 2. 게이트웨이 ping 테스트
    if ping -c "$PING_COUNT" -W 2 "$MAIN_GATEWAY" > /dev/null 2>&1; then
        return 0  # 게이트웨이는 살아있음
    fi

    return 1  # 실패
}

# 메인 라우팅 복구 함수
restore_main_routing() {
    log "🚨 메인 라우팅 복구 시작..."

    # 1. 모든 VPN 워커 인터페이스 종료
    for iface in $(ip link show | grep -o 'wg-worker-[0-9]*'); do
        log "   🔌 $iface 종료 중..."
        sudo ip link set "$iface" down 2>/dev/null || true
        sudo ip link delete "$iface" 2>/dev/null || true
    done

    # 2. 테스트 VPN 인터페이스 종료
    for iface in $(ip link show | grep -o 'test_vpn'); do
        log "   🔌 $iface 종료 중..."
        sudo ip link set "$iface" down 2>/dev/null || true
        sudo ip link delete "$iface" 2>/dev/null || true
    done

    # 3. 메인 라우팅 테이블 확인 및 복구
    if ! ip route show | grep -q "default via $MAIN_GATEWAY"; then
        log "   ⚠️  기본 라우팅 없음 - 추가 중..."
        sudo ip route add default via "$MAIN_GATEWAY" dev "$MAIN_INTERFACE" 2>/dev/null || true
    fi

    # 4. DNS 확인 및 복구
    if ! grep -q "nameserver" /etc/resolv.conf; then
        log "   ⚠️  DNS 설정 없음 - 추가 중..."
        echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf > /dev/null
        echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf > /dev/null
    fi

    # 5. 인터페이스 재시작
    log "   🔄 메인 인터페이스 재시작..."
    sudo ip link set "$MAIN_INTERFACE" down
    sleep 1
    sudo ip link set "$MAIN_INTERFACE" up
    sleep 2

    # 6. DHCP 갱신
    log "   🔄 DHCP 갱신..."
    sudo dhclient -r "$MAIN_INTERFACE" 2>/dev/null || true
    sleep 1
    sudo dhclient "$MAIN_INTERFACE" 2>/dev/null || true

    log "✅ 메인 라우팅 복구 완료"
}

# 긴급 복구 함수 (모든 VPN 강제 종료)
emergency_recovery() {
    log "🚨🚨🚨 긴급 복구 모드 시작 🚨🚨🚨"

    # 모든 WireGuard 인터페이스 강제 종료
    for iface in $(ip link show | grep -o 'wg[0-9]*\|wg-[a-z-]*'); do
        log "   💥 $iface 강제 종료"
        sudo ip link set "$iface" down 2>/dev/null || true
        sudo ip link delete "$iface" 2>/dev/null || true
    done

    # 메인 라우팅 복구
    restore_main_routing

    log "🚨 긴급 복구 완료"
}

# 메인 루프
log "=========================================="
log "🛡️  네트워크 와치독 시작"
log "=========================================="
log "설정:"
log "  - 체크 주기: ${CHECK_INTERVAL}초"
log "  - Ping 대상: $PING_TARGET"
log "  - 실패 임계값: $FAIL_THRESHOLD회 연속"
log "  - 메인 게이트웨이: $MAIN_GATEWAY"
log "=========================================="

while true; do
    if check_network; then
        # 네트워크 정상
        if [ $consecutive_failures -gt 0 ]; then
            log "✅ 네트워크 복구 확인 (연속 실패: $consecutive_failures → 0)"
        fi
        consecutive_failures=0
    else
        # 네트워크 실패
        consecutive_failures=$((consecutive_failures + 1))
        log "⚠️  네트워크 체크 실패 ($consecutive_failures/$FAIL_THRESHOLD)"

        if [ $consecutive_failures -ge $FAIL_THRESHOLD ]; then
            log "🚨 연속 실패 임계값 도달 - 자동 복구 시작"

            if [ $consecutive_failures -ge 5 ]; then
                # 5회 이상 실패 시 긴급 복구
                emergency_recovery
            else
                # 일반 복구
                restore_main_routing
            fi

            # 복구 후 10초 대기
            sleep 10

            # 복구 확인
            if check_network; then
                log "✅ 자동 복구 성공!"
                consecutive_failures=0
            else
                log "❌ 자동 복구 실패 - 수동 확인 필요"
            fi
        fi
    fi

    sleep "$CHECK_INTERVAL"
done
