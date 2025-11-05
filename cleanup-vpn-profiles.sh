#!/bin/bash

#######################################
# VPN 프로필 정리 스크립트
# VPN 사용자가 생성한 프로필 디렉토리를 삭제하여 권한 충돌 해결
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
echo "🧹 VPN 프로필 정리 스크립트"
echo "============================================================"
echo ""

# 현재 사용자 확인
CURRENT_USER=$(whoami)
log_info "현재 사용자: $CURRENT_USER"

# 스크립트 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILES_DIR="$SCRIPT_DIR/browser-profiles"

log_info "프로필 디렉토리: $PROFILES_DIR"
echo ""

# VPN 사용자가 소유한 프로필 디렉토리 찾기
log_info "VPN 사용자 소유 프로필 검색 중..."
echo ""

VPN_PROFILES=$(find "$PROFILES_DIR" -maxdepth 1 -type d -user vpn* 2>/dev/null || true)

if [ -z "$VPN_PROFILES" ]; then
    log_success "VPN 사용자 소유 프로필이 없습니다. 정리할 필요 없음!"
    echo ""
    exit 0
fi

# 발견된 프로필 목록 출력
log_warn "다음 VPN 프로필이 발견되었습니다:"
echo ""
echo "$VPN_PROFILES" | while read -r profile; do
    if [ -n "$profile" ]; then
        owner=$(stat -c '%U' "$profile")
        size=$(du -sh "$profile" | cut -f1)
        echo "  📁 $(basename "$profile") (소유자: $owner, 크기: $size)"
    fi
done
echo ""

# 사용자 확인
log_warn "이 프로필들을 삭제하시겠습니까?"
echo -e "${YELLOW}⚠️  주의: 삭제된 데이터는 복구할 수 없습니다!${NC}"
echo ""
read -p "계속하려면 'yes'를 입력하세요: " confirm

if [ "$confirm" != "yes" ]; then
    log_info "취소되었습니다."
    exit 0
fi

echo ""
log_info "프로필 삭제 중..."
echo ""

# 각 프로필 삭제
echo "$VPN_PROFILES" | while read -r profile; do
    if [ -n "$profile" ] && [ -d "$profile" ]; then
        owner=$(stat -c '%U' "$profile")
        log_info "삭제 중: $(basename "$profile") (소유자: $owner)"

        # sudo로 삭제 (다른 사용자 소유이므로)
        if sudo rm -rf "$profile"; then
            log_success "  ✓ 삭제 완료"
        else
            log_error "  ✗ 삭제 실패"
        fi
    fi
done

echo ""
log_success "모든 VPN 프로필이 정리되었습니다!"
echo ""

# 남은 프로필 확인
REMAINING=$(find "$PROFILES_DIR" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l)
log_info "남은 프로필 개수: $REMAINING"

if [ "$REMAINING" -gt 0 ]; then
    echo ""
    log_info "남은 프로필 목록:"
    ls -l "$PROFILES_DIR" | grep '^d' | awk '{print "  📁", $9, "(소유자:", $3")"}'
fi

echo ""
echo "============================================================"
log_success "정리 완료!"
echo "============================================================"
echo ""
echo -e "${GREEN}✅ 다음 단계:${NC}"
echo "  1. 일반 실행 테스트: python3 agent.py --version 144 --close"
echo "  2. VPN 사용 시 프로필은 자동으로 vpn 사용자 소유로 생성됩니다"
echo ""
