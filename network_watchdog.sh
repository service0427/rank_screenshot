#!/bin/bash
#
# 네트워크 와치독 (Network Watchdog) - wg101-112 전용
# 메인 이더넷 연결이 끊기면 자동으로 복구
#
# 사용법:
#   ./network_watchdog.sh
#
# Crontab 설정 (1분마다 체크):
#   * * * * * /home/tech/rank_screenshot/network_watchdog.sh >> /tmp/network_watchdog.log 2>&1
#   @reboot sleep 30 && /home/tech/rank_screenshot/network_watchdog.sh >> /tmp/network_watchdog.log 2>&1
#

# 설정
PING_TARGET="8.8.8.8"       # ping 테스트 대상
PING_COUNT=3                # ping 시도 횟수
FAIL_THRESHOLD=3            # 연속 실패 임계값
MAIN_GATEWAY="121.172.70.254"  # 메인 게이트웨이
MAIN_INTERFACE="enp4s0"     # 메인 인터페이스
STATE_FILE="/tmp/network_watchdog_state.txt"  # 상태 파일

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 상태 파일에서 연속 실패 횟수 읽기
get_failure_count() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "0"
    fi
}

# 상태 파일에 연속 실패 횟수 저장
set_failure_count() {
    echo "$1" > "$STATE_FILE"
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

    # 1. 모든 WireGuard 인터페이스 종료
    for iface in $(ip link show 2>/dev/null | grep -oE 'wg[0-9]+|wg-[a-z0-9-]+'); do
        log "   🔌 $iface 종료 중..."
        sudo ip link set "$iface" down 2>/dev/null || true
        sudo ip link delete "$iface" 2>/dev/null || true
    done

    # 2. 정책 라우팅 테이블 정리 (101-112)
    for table_num in {101..112}; do
        if ip route show table $table_num 2>/dev/null | grep -q .; then
            log "   🗑️  테이블 $table_num 정리"
            sudo ip route flush table $table_num 2>/dev/null || true
        fi
    done

    # 3. 메인 라우팅 확인 및 복구
    if ! ip route show | grep -q "default via $MAIN_GATEWAY"; then
        log "   ⚠️  기본 라우팅 없음 - 추가 중..."
        sudo ip route add default via "$MAIN_GATEWAY" dev "$MAIN_INTERFACE" 2>/dev/null || true
    fi

    # 4. DNS 확인 및 복구
    if ! grep -q "nameserver" /etc/resolv.conf 2>/dev/null; then
        log "   ⚠️  DNS 설정 없음 - 추가 중..."
        echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf > /dev/null
        echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf > /dev/null
    fi

    # 5. 인터페이스 재시작
    log "   🔄 메인 인터페이스 재시작..."
    sudo ip link set "$MAIN_INTERFACE" down 2>/dev/null
    sleep 1
    sudo ip link set "$MAIN_INTERFACE" up 2>/dev/null
    sleep 2

    # 6. DHCP 갱신
    log "   🔄 DHCP 갱신..."
    sudo dhclient -r "$MAIN_INTERFACE" 2>/dev/null || true
    sleep 1
    sudo dhclient "$MAIN_INTERFACE" 2>/dev/null || true

    log "✅ 메인 라우팅 복구 완료"
}

# 긴급 복구 함수 (5회 이상 실패 시)
emergency_recovery() {
    log "🚨🚨🚨 긴급 복구 모드 시작 🚨🚨🚨"

    # 모든 WireGuard 인터페이스 강제 종료
    for iface in $(ip link show 2>/dev/null | grep -oE 'wg[0-9]+|wg-[a-z0-9-]+'); do
        log "   💥 $iface 강제 종료"
        sudo ip link set "$iface" down 2>/dev/null || true
        sudo ip link delete "$iface" 2>/dev/null || true
    done

    # 정책 라우팅 테이블 정리 (101-112, 200-249)
    for table_num in {101..112} {200..249}; do
        if ip route show table $table_num 2>/dev/null | grep -q .; then
            log "   🗑️  테이블 $table_num 정리"
            sudo ip route flush table $table_num 2>/dev/null || true
        fi
    done

    # 메인 라우팅 복구
    restore_main_routing

    log "🚨 긴급 복구 완료"
}

# === 메인 로직 (1회 실행 후 종료) ===

consecutive_failures=$(get_failure_count)

if check_network; then
    # 네트워크 정상
    if [ "$consecutive_failures" -gt 0 ]; then
        log "✅ 네트워크 복구 확인 (연속 실패: $consecutive_failures → 0)"
        set_failure_count 0
    fi
else
    # 네트워크 실패
    consecutive_failures=$((consecutive_failures + 1))
    set_failure_count "$consecutive_failures"
    log "⚠️  네트워크 체크 실패 ($consecutive_failures/$FAIL_THRESHOLD)"

    if [ "$consecutive_failures" -ge "$FAIL_THRESHOLD" ]; then
        log "🚨 연속 실패 임계값 도달 - 자동 복구 시작"

        if [ "$consecutive_failures" -ge 5 ]; then
            # 5회 이상 실패 시 긴급 복구
            emergency_recovery
        else
            # 일반 복구
            restore_main_routing
        fi

        # 복구 후 확인
        sleep 5
        if check_network; then
            log "✅ 자동 복구 성공!"
            set_failure_count 0
        else
            log "❌ 자동 복구 실패 - 다음 체크에서 재시도"
        fi
    fi
fi
