#!/bin/bash

#######################################
# VPN 사용자가 tech 사용자로 명령 실행 가능하도록 sudoers 설정
# API 요청을 로컬 네트워크로 우회하기 위해 필요
#######################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================================"
echo "🔧 VPN → Tech Sudoers 설정"
echo "============================================================"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한이 필요합니다"
    echo "실행 방법: sudo ./setup-vpn-sudoers.sh"
    exit 1
fi

# 현재 sudoers 설정 확인
SUDOERS_FILE="/etc/sudoers.d/vpn-api-access"

log_info "VPN 사용자 확인..."
VPN_USERS=$(getent passwd | grep -E '^vpn[0-9]+:' | cut -d: -f1 | tr '\n' ' ')

if [ -z "$VPN_USERS" ]; then
    log_warn "VPN 사용자를 찾을 수 없습니다"
    log_info "예상 사용자: vpn0, vpn1, vpn2, ..."
    echo ""
    read -p "계속하시겠습니까? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 0
    fi
    VPN_USERS="vpn0 vpn1 vpn2 vpn3 vpn4 vpn5"
fi

log_success "VPN 사용자 발견: $VPN_USERS"

# Sudoers 설정 생성
log_info "Sudoers 설정 생성 중..."

cat > "$SUDOERS_FILE" << 'EOF'
# VPN 사용자가 tech 사용자로 명령 실행 가능
# API 요청을 로컬 네트워크로 우회하기 위해 필요

# 각 VPN 사용자가 tech로 python3 실행 가능 (NOPASSWD)
EOF

for vpn_user in $VPN_USERS; do
    echo "${vpn_user} ALL=(tech) NOPASSWD: /usr/bin/python3" >> "$SUDOERS_FILE"
done

# 권한 설정
chmod 0440 "$SUDOERS_FILE"

log_success "Sudoers 설정 파일 생성: $SUDOERS_FILE"

# 설정 검증
log_info "설정 검증 중..."
if visudo -c -f "$SUDOERS_FILE" > /dev/null 2>&1; then
    log_success "설정 검증 성공"
else
    log_error "설정 검증 실패 - 파일 삭제"
    rm -f "$SUDOERS_FILE"
    exit 1
fi

# 설정 내용 출력
echo ""
log_info "설정 내용:"
cat "$SUDOERS_FILE"

echo ""
echo "============================================================"
log_success "설정 완료!"
echo "============================================================"
echo ""
log_info "이제 VPN 환경에서 API 요청이 로컬 네트워크로 우회됩니다"
echo ""
