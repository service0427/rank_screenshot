#!/bin/bash

#######################################
# Coupang Agent V2 자동 설치 스크립트
# Ubuntu 22.04 LTS 지원
#######################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# 현재 사용자 확인
CURRENT_USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "🚀 Coupang Agent V2 자동 설치"
echo "============================================================"
echo ""
log_info "Installation directory: $SCRIPT_DIR"
log_info "Current user: $CURRENT_USER"
echo ""

# ===================================================================
# 1. 시스템 패키지 업데이트
# ===================================================================

log_step "1/8 시스템 패키지 업데이트 중..."
echo ""

sudo apt-get update -qq
log_success "패키지 목록 업데이트 완료"

# ===================================================================
# 2. Python 3 설치 확인
# ===================================================================

log_step "2/8 Python 3 설치 확인 중..."
echo ""

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_success "Python 3 already installed: $PYTHON_VERSION"

    # Python 버전 확인 (3.10 이상 권장)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        log_warn "Python 3.10 이상 권장 (현재: $PYTHON_VERSION)"
        log_info "Python 3.10+ 설치 중..."
        sudo apt-get install -y python3.10 python3.10-distutils
    fi
else
    log_info "Python 3 설치 중..."
    sudo apt-get install -y python3 python3-pip python3-distutils
    log_success "Python 3 설치 완료"
fi

# pip 설치 확인
if ! command -v pip3 &> /dev/null; then
    log_info "pip3 설치 중..."
    sudo apt-get install -y python3-pip
    log_success "pip3 설치 완료"
else
    log_success "pip3 already installed"
fi

# ===================================================================
# 3. 시스템 라이브러리 설치 (Chrome 실행에 필요)
# ===================================================================

log_step "3/8 시스템 라이브러리 설치 중..."
echo ""

log_info "Chrome 실행에 필요한 시스템 라이브러리 설치 중..."

sudo apt-get install -y \
    wget \
    curl \
    unzip \
    jq \
    xvfb \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxrandr2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libxshmfence1 \
    > /dev/null 2>&1

log_success "시스템 라이브러리 설치 완료"

# ===================================================================
# 4. Python 패키지 설치
# ===================================================================

log_step "4/8 Python 패키지 설치 중..."
echo ""

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    log_info "requirements.txt에서 패키지 설치 중..."
    log_warn "시스템 전역 설치 (VPN 사용 시 필요)"
    sudo pip3 install -r "$SCRIPT_DIR/requirements.txt"
    log_success "Python 패키지 설치 완료"
else
    log_error "requirements.txt not found!"
    exit 1
fi

# ===================================================================
# 5. Chrome 버전 설치
# ===================================================================

log_step "5/8 Chrome 버전 설치 중..."
echo ""

if [ -x "$SCRIPT_DIR/install-chrome-versions.sh" ]; then
    # Chrome 130, 144 자동 설치
    "$SCRIPT_DIR/install-chrome-versions.sh"
else
    log_error "install-chrome-versions.sh not found or not executable!"
    exit 1
fi

# ===================================================================
# 6. 디렉토리 생성
# ===================================================================

log_step "6/8 필요한 디렉토리 생성 중..."
echo ""

mkdir -p "$SCRIPT_DIR/browser-profiles"
mkdir -p "$SCRIPT_DIR/screenshots"
mkdir -p "$SCRIPT_DIR/debug_logs"

log_success "디렉토리 생성 완료"

# ===================================================================
# 7. 권한 설정
# ===================================================================

log_step "7/8 권한 설정 중..."
echo ""

if [ -x "$SCRIPT_DIR/setup-permissions.sh" ]; then
    log_info "권한 설정 스크립트 실행 중..."
    "$SCRIPT_DIR/setup-permissions.sh"
    log_success "권한 설정 완료"
else
    log_warn "setup-permissions.sh not found or not executable"
fi

# ===================================================================
# 8. VPN 설정 안내
# ===================================================================

log_step "8/8 VPN 설정 확인..."
echo ""

if command -v vpn &> /dev/null || [ -f "$HOME/vpn-ip-rotation/client/vpn" ]; then
    log_success "VPN 클라이언트 발견!"

    # sudoers 설정 확인
    if [ -f "/etc/sudoers.d/vpn-access" ]; then
        log_success "VPN sudoers 설정 완료"
    else
        log_warn "VPN sudoers 설정이 필요합니다"
        log_info "다음 명령어로 설정하세요:"
        echo ""
        echo "  sudo ./setup-vpn-sudoers.sh"
        echo ""
    fi
else
    log_warn "VPN 클라이언트가 설치되지 않았습니다"
    log_info "VPN 사용을 원하시면 다음 저장소를 참고하세요:"
    echo ""
    echo "  https://github.com/service0427/vpn"
    echo ""
fi

# ===================================================================
# 설치 완료
# ===================================================================

echo ""
echo "============================================================"
log_success "🎉 설치 완료!"
echo "============================================================"
echo ""

# 테스트 명령어 안내
echo -e "${GREEN}✅ 설치된 구성 요소:${NC}"
echo "  • Python $(python3 --version | awk '{print $2}')"
echo "  • pip $(pip3 --version | awk '{print $2}')"
echo "  • undetected-chromedriver $(pip3 show undetected-chromedriver 2>/dev/null | grep Version | awk '{print $2}')"
echo "  • selenium $(pip3 show selenium 2>/dev/null | grep Version | awk '{print $2}')"
echo "  • Chrome 130 (구버전 TLS)"
echo "  • Chrome 144 (최신 버전)"
echo ""

echo -e "${CYAN}🚀 다음 단계:${NC}"
echo ""
echo "  1. Agent 테스트:"
echo "     python3 agent.py --version 134 --close"
echo ""
echo "  2. 키워드 검색 테스트:"
echo "     python3 agent.py --version 134 --keyword \"노트북\""
echo ""
echo "  3. VPN 사용 (VPN 설치 후):"
echo "     python3 agent.py --version 130 --vpn 0 --keyword \"게임\""
echo ""

echo -e "${YELLOW}⚠️  참고사항:${NC}"
echo "  • VPN 사용 시 setup-vpn-sudoers.sh 실행 필요"
echo "  • 권한 오류 발생 시 setup-permissions.sh 재실행"
echo "  • Chrome 버전 추가 설치: ./install-chrome-versions.sh [version]"
echo ""

log_info "설치 로그는 화면에 출력되었습니다"
echo ""
