#!/bin/bash

###############################################################################
# VPN 키 풀 시스템 테스트 스크립트 (Bash)
###############################################################################

API_SERVER="http://112.161.221.82:3000"
TIMEOUT=5

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "============================================================"
echo "🧪 VPN 키 풀 시스템 테스트 (Bash)"
echo "============================================================"
echo ""

# 1. 서버 상태 확인
echo "📊 1. 서버 상태 확인"
echo "------------------------------------------------------------"

STATUS_RESPONSE=$(timeout $TIMEOUT curl -s $API_SERVER/api/vpn/status 2>&1)
STATUS_EXIT=$?

if [ $STATUS_EXIT -eq 0 ]; then
    echo "$STATUS_RESPONSE" | jq '.statistics'
    echo ""
else
    echo -e "${RED}   ❌ 서버에 연결할 수 없습니다.${NC}"
    echo -e "${YELLOW}   ⚠️  Exit code: $STATUS_EXIT${NC}"
    echo ""
    echo "   서버가 시작되지 않았거나 네트워크 문제가 있습니다."
    echo "   테스트를 중단합니다."
    echo ""
    exit 1
fi

# 2. VPN 키 할당
echo "🔑 2. VPN 키 할당"
echo "------------------------------------------------------------"

ALLOC_RESPONSE=$(timeout $TIMEOUT curl -s $API_SERVER/api/vpn/allocate 2>&1)
ALLOC_EXIT=$?

if [ $ALLOC_EXIT -ne 0 ]; then
    echo -e "${RED}   ❌ 키 할당 실패 (Exit code: $ALLOC_EXIT)${NC}"
    exit 1
fi

# 응답 저장
echo "$ALLOC_RESPONSE" > /tmp/vpn_test_response.json

# 성공 여부 확인
SUCCESS=$(echo "$ALLOC_RESPONSE" | jq -r '.success')

if [ "$SUCCESS" != "true" ]; then
    echo -e "${RED}   ❌ 키 할당 실패${NC}"
    echo "$ALLOC_RESPONSE" | jq
    exit 1
fi

# 정보 추출
PUBLIC_KEY=$(echo "$ALLOC_RESPONSE" | jq -r '.public_key')
INTERNAL_IP=$(echo "$ALLOC_RESPONSE" | jq -r '.internal_ip')
SERVER_IP=$(echo "$ALLOC_RESPONSE" | jq -r '.server_ip')
SERVER_PORT=$(echo "$ALLOC_RESPONSE" | jq -r '.server_port')

echo -e "${GREEN}   ✅ VPN 키 할당 성공!${NC}"
echo "   📍 Internal IP: $INTERNAL_IP"
echo "   🖥️  Server: $SERVER_IP:$SERVER_PORT"
echo "   🔐 Public Key: ${PUBLIC_KEY:0:20}..."
echo ""

# 3. 설정 파일 저장
echo "💾 3. 설정 파일 저장"
echo "------------------------------------------------------------"

CONFIG_FILE="/tmp/vpn_test_client.conf"
echo "$ALLOC_RESPONSE" | jq -r '.config' > "$CONFIG_FILE"

if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}   ✅ 설정 파일 저장: $CONFIG_FILE${NC}"
    echo ""
    echo "   --- 설정 파일 앞부분 ---"
    head -n 5 "$CONFIG_FILE" | sed 's/^/   /'
    echo "   ..."
    echo ""
else
    echo -e "${RED}   ❌ 설정 파일 저장 실패${NC}"
    echo ""
fi

# 4. 키 반납 대기
echo "⏸️  4. 키 반납 준비"
echo "------------------------------------------------------------"
echo "   Enter를 누르면 키를 반납합니다..."
read

# 5. VPN 키 반납
echo ""
echo "🔓 5. VPN 키 반납"
echo "------------------------------------------------------------"

RELEASE_RESPONSE=$(timeout $TIMEOUT curl -s -X POST $API_SERVER/api/vpn/release \
    -H "Content-Type: application/json" \
    -d "{\"public_key\": \"$PUBLIC_KEY\"}" 2>&1)

RELEASE_EXIT=$?

if [ $RELEASE_EXIT -ne 0 ]; then
    echo -e "${RED}   ❌ 키 반납 실패 (Exit code: $RELEASE_EXIT)${NC}"
    exit 1
fi

RELEASE_SUCCESS=$(echo "$RELEASE_RESPONSE" | jq -r '.success')

if [ "$RELEASE_SUCCESS" == "true" ]; then
    echo -e "${GREEN}   ✅ VPN 키 반납 성공!${NC}"
else
    echo -e "${RED}   ❌ 키 반납 실패${NC}"
    echo "$RELEASE_RESPONSE" | jq
fi

echo ""

# 6. 최종 상태 확인
echo "📊 6. 최종 상태 확인"
echo "------------------------------------------------------------"

FINAL_STATUS=$(timeout $TIMEOUT curl -s $API_SERVER/api/vpn/status 2>&1)

if [ $? -eq 0 ]; then
    echo "$FINAL_STATUS" | jq '.statistics'
else
    echo -e "${RED}   ❌ 상태 조회 실패${NC}"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 테스트 완료!${NC}"
echo "============================================================"
echo ""

# 정리
rm -f /tmp/vpn_test_response.json
