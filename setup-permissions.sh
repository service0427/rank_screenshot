#!/bin/bash

#######################################
# Agent 권한 설정 스크립트
# VPN 사용자들이 agent를 실행할 수 있도록 필요한 권한 설정
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
echo "🔧 Agent 권한 설정"
echo "============================================================"
echo ""

# 현재 사용자 확인
CURRENT_USER=$(whoami)
log_info "Current user: $CURRENT_USER"

# 스크립트 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log_info "Agent directory: $SCRIPT_DIR"

# 홈 디렉토리 확인
HOME_DIR=$(eval echo ~$CURRENT_USER)
log_info "Home directory: $HOME_DIR"

# ===================================================================
# 1. Agent 디렉토리 권한 설정
# ===================================================================

log_info "Setting agent directory permissions..."

# Agent 디렉토리에 대한 읽기 및 실행 권한 부여 (others)
chmod o+rx "$HOME_DIR" 2>/dev/null || log_warn "Could not set permissions on $HOME_DIR"
chmod -R o+rX "$SCRIPT_DIR" 2>/dev/null || log_warn "Could not set read permissions on $SCRIPT_DIR"

log_success "Agent directory readable by VPN users"

# ===================================================================
# 2. Browser Profiles 디렉토리 권한 설정
# ===================================================================

log_info "Setting browser-profiles directory permissions..."

PROFILES_DIR="$SCRIPT_DIR/browser-profiles"
if [ -d "$PROFILES_DIR" ]; then
    chmod -R o+rwX "$PROFILES_DIR" 2>/dev/null || log_warn "Could not set full permissions on $PROFILES_DIR"
    log_success "Browser profiles writable by VPN users"
else
    mkdir -p "$PROFILES_DIR"
    chmod o+rwx "$PROFILES_DIR"
    log_success "Browser profiles directory created"
fi

# ===================================================================
# 3. Undetected ChromeDriver 디렉토리 권한 설정
# ===================================================================

log_info "Setting undetected_chromedriver directory permissions..."

UC_DIR="$HOME_DIR/.local/share/undetected_chromedriver"
if [ -d "$UC_DIR" ]; then
    chmod -R o+rwX "$UC_DIR" 2>/dev/null || log_warn "Could not set permissions on $UC_DIR"
    log_success "Undetected ChromeDriver directory writable"
else
    mkdir -p "$UC_DIR"
    chmod o+rwx "$UC_DIR"
    log_success "Undetected ChromeDriver directory created"
fi

# ===================================================================
# 4. Selenium 캐시 디렉토리 권한 설정
# ===================================================================

log_info "Setting selenium cache directory permissions..."

SELENIUM_CACHE="$HOME_DIR/.cache/selenium"
if [ -d "$SELENIUM_CACHE" ]; then
    chmod -R o+rwX "$SELENIUM_CACHE" 2>/dev/null || log_warn "Could not set permissions on $SELENIUM_CACHE"
    log_success "Selenium cache directory writable"
else
    mkdir -p "$SELENIUM_CACHE"
    chmod o+rwx "$SELENIUM_CACHE"
    log_success "Selenium cache directory created"
fi

# ===================================================================
# 5. VPN 사용자 확인
# ===================================================================

log_info "Checking VPN users..."

VPN_USERS=$(getent passwd | grep -E '^vpn[0-9]+:' | cut -d: -f1 | tr '\n' ' ')
if [ -z "$VPN_USERS" ]; then
    log_warn "No VPN users found (vpn0, vpn1, etc.)"
    log_info "VPN users will be created when VPN client is installed"
else
    log_success "Found VPN users: $VPN_USERS"
fi

# ===================================================================
# 6. ChromeDriver 디렉토리 권한 (있는 경우)
# ===================================================================

CHROMEDRIVER_DIR="$SCRIPT_DIR/chromedriver"
if [ -d "$CHROMEDRIVER_DIR" ]; then
    log_info "Setting chromedriver directory permissions..."
    chmod -R o+rX "$CHROMEDRIVER_DIR" 2>/dev/null || log_warn "Could not set permissions on $CHROMEDRIVER_DIR"
    log_success "ChromeDriver directory readable"
fi

# ===================================================================
# 7. Python site-packages 확인
# ===================================================================

log_info "Checking Python packages accessibility..."

PYTHON_SITE_PACKAGES="$HOME_DIR/.local/lib/python3.12/site-packages"
if [ -d "$PYTHON_SITE_PACKAGES" ]; then
    # 읽기 권한만 필요
    chmod o+rx "$HOME_DIR/.local" 2>/dev/null || true
    chmod o+rx "$HOME_DIR/.local/lib" 2>/dev/null || true
    chmod -R o+rX "$PYTHON_SITE_PACKAGES" 2>/dev/null || log_warn "Could not set read permissions on Python packages"
    log_success "Python packages readable by VPN users"
else
    log_warn "Python site-packages not found at $PYTHON_SITE_PACKAGES"
fi

# ===================================================================
# 완료
# ===================================================================

echo ""
echo "============================================================"
log_success "Permission setup completed!"
echo "============================================================"
echo ""
echo -e "${GREEN}✅ Next steps:${NC}"
echo "  1. Test with VPN: python3 agent.py --version 134 --vpn 1 --close"
echo "  2. If permission errors occur, run this script again"
echo ""
echo -e "${YELLOW}⚠️  Note:${NC}"
echo "  - This script needs to be run by the agent owner ($CURRENT_USER)"
echo "  - Run this after installing VPN client or when permission errors occur"
echo "  - Some directories may require sudo for permission changes"
echo ""
