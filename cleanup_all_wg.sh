#!/bin/bash
#
# 모든 WireGuard 연결 정리 스크립트
#
# 용도:
# - /home/tech/vpn/client의 sync.sh로 생성된 wg0~wg36 등 모든 연결 정리
# - VPN 키 풀의 wg-worker-N 연결 정리
# - VPN 테스트 연결 정리
#
# 사용법:
#   ./cleanup_all_wg.sh
#

echo "============================================"
echo "🧹 모든 WireGuard 연결 정리"
echo "============================================"

# 현재 WireGuard 인터페이스 목록 조회
echo ""
echo "📋 현재 WireGuard 인터페이스:"
echo "--------------------------------------------"
wg_interfaces=$(ip link show | grep -oE "wg[0-9]+|wg-[a-z0-9-]+")

if [ -z "$wg_interfaces" ]; then
    echo "   (없음)"
    echo ""
    echo "✅ 정리할 WireGuard 인터페이스가 없습니다."
    exit 0
fi

echo "$wg_interfaces" | while read iface; do
    echo "   - $iface"
done
echo "--------------------------------------------"

# 총 개수 계산
total_count=$(echo "$wg_interfaces" | wc -l)
echo ""
echo "총 $total_count 개의 인터페이스를 정리합니다..."

# 1. wg-quick down으로 정리 시도
echo ""
echo "🔌 Phase 1: wg-quick down으로 정리 중..."
success_count=0
fail_count=0

echo "$wg_interfaces" | while read iface; do
    # 설정 파일 경로 추측
    # - /home/tech/vpn/client/*.conf (sync.sh 방식)
    # - /tmp/vpn_configs/*.conf (VPN 키 풀 방식)
    config_path=""

    if [[ "$iface" =~ ^wg[0-9]+$ ]]; then
        # wg0, wg1, ... → /home/tech/vpn/client/wgN.conf (sync.sh 방식)
        config_path="/home/tech/vpn/client/${iface}.conf"
    elif [[ "$iface" =~ ^wgs[0-9]+-[0-9]+$ ]]; then
        # wgs218-190, wgs114-123, ... → /tmp/vpn_configs/wgsXXX-XXX.conf (VPN 키 풀, 서버 IP 기반)
        config_path="/tmp/vpn_configs/${iface}.conf"
    elif [[ "$iface" =~ ^wg-worker-[0-9]+$ ]]; then
        # wg-worker-1, wg-worker-2, ... → /tmp/vpn_configs/wg-worker-N.conf (구버전)
        config_path="/tmp/vpn_configs/${iface}.conf"
    elif [[ "$iface" =~ ^wg-[0-9]+-[0-9]+-[0-9]+-[0-9]+$ ]]; then
        # wg-10-8-0-14, ... → /tmp/vpn_configs/wg-10-8-0-14.conf (내부 IP 기반, 구버전)
        config_path="/tmp/vpn_configs/${iface}.conf"
    elif [[ "$iface" =~ ^wg-vpn-pool-[0-9]+$ ]]; then
        # wg-vpn-pool-1, ... → /tmp/vpn_configs/wg-vpn-pool-N.conf
        config_path="/tmp/vpn_configs/${iface}.conf"
    fi

    # 설정 파일이 있으면 wg-quick down 시도
    if [ -n "$config_path" ] && [ -f "$config_path" ]; then
        echo "   🔌 $iface (config: $config_path)"
        sudo wg-quick down "$config_path" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "      ✅ 성공"
            ((success_count++))
        else
            echo "      ⚠️  실패 (다음 단계에서 강제 종료)"
            ((fail_count++))
        fi
    else
        echo "   ⚠️  $iface: 설정 파일 없음 ($config_path) - 강제 종료 필요"
        ((fail_count++))
    fi
done

# 2. 남은 인터페이스 강제 종료 (ip link delete)
echo ""
echo "🔨 Phase 2: 남은 인터페이스 강제 종료 중..."
remaining_interfaces=$(ip link show | grep -oE "wg[0-9]+|wg-[a-z0-9-]+")

if [ -z "$remaining_interfaces" ]; then
    echo "   ✅ 남은 인터페이스 없음"
else
    echo "$remaining_interfaces" | while read iface; do
        echo "   💥 $iface 강제 종료"
        sudo ip link set "$iface" down 2>/dev/null
        sudo ip link delete "$iface" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "      ✅ 성공"
        else
            echo "      ⚠️  실패 (이미 삭제됨?)"
        fi
    done
fi

# 3. 정책 라우팅 테이블 정리 (200~249)
echo ""
echo "🗑️  Phase 3: 정책 라우팅 테이블 정리 중..."
for table_num in {200..249}; do
    # 테이블에 route가 있는지 확인
    if ip route show table $table_num 2>/dev/null | grep -q .; then
        echo "   🗑️  테이블 $table_num 정리"
        sudo ip route flush table $table_num 2>/dev/null
    fi
done
echo "   ✅ 정책 라우팅 테이블 정리 완료"

# 4. /tmp/vpn_configs 정리
echo ""
echo "🗑️  Phase 4: /tmp/vpn_configs 설정 파일 정리 중..."
if [ -d "/tmp/vpn_configs" ]; then
    conf_count=$(ls /tmp/vpn_configs/*.conf 2>/dev/null | wc -l)
    if [ $conf_count -gt 0 ]; then
        echo "   삭제: $conf_count 개 설정 파일"
        sudo rm -f /tmp/vpn_configs/*.conf
        echo "   ✅ 설정 파일 삭제 완료"
    else
        echo "   ✅ 삭제할 설정 파일 없음"
    fi
else
    echo "   ✅ /tmp/vpn_configs 디렉토리 없음"
fi

# 5. 메인 라우팅 확인
echo ""
echo "🔍 Phase 5: 메인 라우팅 확인 중..."
main_gateway="121.172.70.254"
main_interface="enp4s0"

if ip route show | grep -q "default via $main_gateway"; then
    echo "   ✅ 메인 라우팅 정상: default via $main_gateway dev $main_interface"
else
    echo "   ⚠️  메인 라우팅 없음 - 복구 시도"
    sudo ip route add default via "$main_gateway" dev "$main_interface" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ 메인 라우팅 복구 완료"
    else
        echo "   ⚠️  메인 라우팅 복구 실패 (이미 존재?)"
    fi
fi

# 6. 최종 확인
echo ""
echo "============================================"
echo "✅ 정리 완료!"
echo "============================================"

# 남은 WireGuard 인터페이스 확인
remaining=$(ip link show | grep -oE "wg[0-9]+|wg-[a-z0-9-]+" | wc -l)

if [ $remaining -eq 0 ]; then
    echo "✅ 모든 WireGuard 인터페이스가 정리되었습니다."
else
    echo "⚠️  남은 WireGuard 인터페이스: $remaining 개"
    echo ""
    echo "남은 인터페이스:"
    ip link show | grep -oE "wg[0-9]+|wg-[a-z0-9-]+" | while read iface; do
        echo "   - $iface"
    done
    echo ""
    echo "수동 정리 방법:"
    echo "   sudo ip link set <interface> down"
    echo "   sudo ip link delete <interface>"
fi

echo ""
echo "현재 라우팅 상태:"
ip route show | head -5

echo ""
