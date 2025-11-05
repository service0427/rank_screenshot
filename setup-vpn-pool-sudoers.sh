#!/bin/bash

###############################################################################
# VPN 키 풀 sudoers 설정 스크립트
# wg-quick 명령어를 sudo 없이 실행 가능하도록 설정
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "============================================================"
echo "🔧 VPN 키 풀 sudoers 설정"
echo "============================================================"
echo ""

# 현재 사용자 확인
CURRENT_USER=$(whoami)

if [ "$CURRENT_USER" == "root" ]; then
    echo -e "${RED}❌ root 사용자로 실행하지 마세요${NC}"
    echo "   sudo 없이 실행: ./setup-vpn-pool-sudoers.sh"
    exit 1
fi

echo "📋 설정 내용:"
echo "   사용자: $CURRENT_USER"
echo "   허용 명령어: wg-quick"
echo ""

# sudoers 파일 생성
SUDOERS_FILE="/etc/sudoers.d/vpn-pool-access"

echo "📝 sudoers 파일 생성 중..."

# 임시 파일에 작성
TEMP_FILE=$(mktemp)

cat > "$TEMP_FILE" <<EOF
# VPN 키 풀 시스템용 sudoers 설정
# wg-quick 명령어를 비밀번호 없이 실행 가능
# 생성일: $(date)

# tech 사용자가 wg-quick 명령어를 NOPASSWD로 실행 가능
${CURRENT_USER} ALL=(ALL) NOPASSWD: /usr/bin/wg-quick
EOF

echo "   임시 파일 생성: $TEMP_FILE"
echo ""

# sudoers 파일 내용 출력
echo "📄 sudoers 파일 내용:"
echo "------------------------------------------------------------"
cat "$TEMP_FILE"
echo "------------------------------------------------------------"
echo ""

# sudoers 문법 검사
echo "🔍 sudoers 문법 검사 중..."
sudo visudo -c -f "$TEMP_FILE" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ sudoers 문법 검사 통과${NC}"
    echo ""
else
    echo -e "${RED}   ❌ sudoers 문법 오류${NC}"
    rm -f "$TEMP_FILE"
    exit 1
fi

# sudoers 파일 복사
echo "📋 sudoers 파일 설치 중..."
sudo cp "$TEMP_FILE" "$SUDOERS_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ sudoers 파일 설치 완료: $SUDOERS_FILE${NC}"
else
    echo -e "${RED}   ❌ sudoers 파일 설치 실패${NC}"
    rm -f "$TEMP_FILE"
    exit 1
fi

# 권한 설정
sudo chmod 440 "$SUDOERS_FILE"
echo "   ✅ 파일 권한 설정: 440"
echo ""

# 임시 파일 삭제
rm -f "$TEMP_FILE"

# 테스트
echo "🧪 설정 테스트 중..."
sudo -n wg-quick 2>&1 | grep -q "Usage"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ wg-quick 명령어 sudo 실행 가능 (비밀번호 불필요)${NC}"
else
    echo -e "${YELLOW}   ⚠️  테스트 실패 (시스템 재로그인 필요할 수 있음)${NC}"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ VPN 키 풀 sudoers 설정 완료!${NC}"
echo "============================================================"
echo ""
echo "📌 다음 명령어로 테스트:"
echo "   sudo wg-quick  # 비밀번호 없이 실행되어야 함"
echo ""
echo "📌 VPN 키 풀 시스템 사용:"
echo "   python3 agent.py --vpn-pool --keyword \"테스트\""
echo "   python3 run_workers.py --use-vpn-pool -t 6"
echo ""
