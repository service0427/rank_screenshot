#!/bin/bash

###############################################################################
# VPN 실제 연결 테스트 스크립트
# sudo 권한 필요 (WireGuard 연결용)
###############################################################################

API_SERVER="http://112.161.221.82:3000"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "============================================================"
echo "🔐 VPN 실제 연결 테스트"
echo "============================================================"
echo ""

# 1. 현재 IP 확인
echo "📍 1. 현재 IP 확인 (VPN 연결 전)"
echo "------------------------------------------------------------"
BEFORE_IP=$(curl -s https://api.ipify.org)
echo "   현재 IP: $BEFORE_IP"
echo ""

# 2. VPN 키 할당
echo "🔑 2. VPN 키 할당"
echo "------------------------------------------------------------"
RESPONSE=$(curl -s $API_SERVER/api/vpn/allocate)
SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

if [ "$SUCCESS" != "true" ]; then
    echo -e "${RED}   ❌ VPN 키 할당 실패${NC}"
    echo "$RESPONSE" | jq
    exit 1
fi

PUBLIC_KEY=$(echo "$RESPONSE" | jq -r '.public_key')
INTERNAL_IP=$(echo "$RESPONSE" | jq -r '.internal_ip')

echo -e "${GREEN}   ✅ VPN 키 할당 성공!${NC}"
echo "   📍 Internal IP: $INTERNAL_IP"
echo "   🔐 Public Key: ${PUBLIC_KEY:0:30}..."
echo ""

# 3. WireGuard 설정 파일 저장
echo "💾 3. WireGuard 설정 파일 저장"
echo "------------------------------------------------------------"
CONFIG_FILE="/tmp/vpn_test_$(date +%s).conf"
echo "$RESPONSE" | jq -r '.config' > "$CONFIG_FILE"

echo -e "${GREEN}   ✅ 설정 파일 저장: $CONFIG_FILE${NC}"
echo ""

# 4. WireGuard 연결
echo "🌐 4. WireGuard 연결"
echo "------------------------------------------------------------"
echo "   연결 중..."

sudo wg-quick up "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ VPN 연결 성공!${NC}"
    echo ""
else
    echo -e "${RED}   ❌ VPN 연결 실패${NC}"
    echo ""

    # 키 반납
    echo "🔓 VPN 키 반납 (연결 실패)"
    curl -s -X POST $API_SERVER/api/vpn/release \
        -H "Content-Type: application/json" \
        -d "{\"public_key\": \"$PUBLIC_KEY\"}" > /dev/null

    rm -f "$CONFIG_FILE"
    exit 1
fi

# 5. VPN을 통한 IP 확인
echo "📍 5. VPN을 통한 IP 확인"
echo "------------------------------------------------------------"
sleep 2  # 연결 안정화 대기

AFTER_IP=$(curl -s https://api.ipify.org)
echo "   VPN IP: $AFTER_IP"
echo ""

# 6. IP 변경 확인
echo "✅ 6. IP 변경 확인"
echo "------------------------------------------------------------"
if [ "$BEFORE_IP" != "$AFTER_IP" ]; then
    echo -e "${GREEN}   ✅ IP 변경 성공!${NC}"
    echo "   Before: $BEFORE_IP"
    echo "   After:  $AFTER_IP"
else
    echo -e "${YELLOW}   ⚠️  IP가 변경되지 않았습니다${NC}"
    echo "   IP: $BEFORE_IP"
fi
echo ""

# 7. 대기
echo "⏸️  7. 테스트 완료 - Enter를 누르면 VPN 연결을 해제합니다..."
read

# 8. WireGuard 연결 해제
echo ""
echo "🔌 8. WireGuard 연결 해제"
echo "------------------------------------------------------------"
sudo wg-quick down "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ VPN 연결 해제 성공${NC}"
else
    echo -e "${YELLOW}   ⚠️  연결 해제 실패 (수동 정리 필요)${NC}"
fi
echo ""

# 9. VPN 키 반납
echo "🔓 9. VPN 키 반납"
echo "------------------------------------------------------------"
RELEASE_RESPONSE=$(curl -s -X POST $API_SERVER/api/vpn/release \
    -H "Content-Type: application/json" \
    -d "{\"public_key\": \"$PUBLIC_KEY\"}")

RELEASE_SUCCESS=$(echo "$RELEASE_RESPONSE" | jq -r '.success')

if [ "$RELEASE_SUCCESS" == "true" ]; then
    echo -e "${GREEN}   ✅ VPN 키 반납 성공!${NC}"
else
    echo -e "${RED}   ❌ VPN 키 반납 실패${NC}"
fi
echo ""

# 10. 원래 IP 복원 확인
echo "📍 10. 원래 IP 복원 확인"
echo "------------------------------------------------------------"
sleep 1
FINAL_IP=$(curl -s https://api.ipify.org)
echo "   현재 IP: $FINAL_IP"

if [ "$FINAL_IP" == "$BEFORE_IP" ]; then
    echo -e "${GREEN}   ✅ IP 복원 성공!${NC}"
else
    echo -e "${YELLOW}   ⚠️  IP가 다릅니다${NC}"
    echo "   Before: $BEFORE_IP"
    echo "   Final:  $FINAL_IP"
fi
echo ""

# 정리
rm -f "$CONFIG_FILE"

echo "============================================================"
echo -e "${GREEN}✅ 테스트 완료!${NC}"
echo "============================================================"
echo ""
echo "요약:"
echo "  VPN 연결 전 IP: $BEFORE_IP"
echo "  VPN 연결 후 IP: $AFTER_IP"
echo "  VPN 해제 후 IP: $FINAL_IP"
echo ""
