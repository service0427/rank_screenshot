#!/bin/bash
#
# VPN 연결 상태 확인 스크립트
#
# 용도:
# - 활성 VPN 연결 확인 (JSON + 실제)
# - 미해제 VPN 연결 확인 (JSON만)
# - 추적되지 않는 VPN 연결 확인 (실제만)
#
# 사용법:
#   ./check_vpn_status.sh         # 상태만 확인
#   ./check_vpn_status.sh cleanup # 미해제 연결 정리
#

cd "$(dirname "$0")"

echo "============================================"
echo "🔍 VPN 연결 상태 확인"
echo "============================================"

if [ "$1" == "cleanup" ]; then
    python3 lib/modules/vpn_connection_tracker.py cleanup
else
    python3 lib/modules/vpn_connection_tracker.py status
fi
