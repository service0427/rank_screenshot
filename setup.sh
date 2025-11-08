#!/bin/bash

#######################################
# Coupang Agent V2 자동 설치 스크립트
# Ubuntu 22.04 LTS 지원
#
# 사용법:
#   ./setup.sh           # UC 시스템만 설치 (기본)
#   ./setup.sh --uc      # UC 시스템 설치
#   ./setup.sh --no      # nodriver 시스템 설치 (미구현)
#   ./setup.sh --win     # Windows UA 스푸핑 시스템 (미구현)
#   ./setup.sh --all     # 모든 시스템 설치
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

# 설치 옵션 파싱
INSTALL_UC=false
INSTALL_NO=false
INSTALL_WIN=false

if [ $# -eq 0 ]; then
    # 파라미터 없으면 UC만 설치 (기본)
    INSTALL_UC=true
else
    for arg in "$@"; do
        case $arg in
            --uc)
                INSTALL_UC=true
                ;;
            --no)
                INSTALL_NO=true
                ;;
            --win)
                INSTALL_WIN=true
                ;;
            --all)
                INSTALL_UC=true
                INSTALL_NO=true
                INSTALL_WIN=true
                ;;
            --help|-h)
                echo "사용법: $0 [옵션]"
                echo ""
                echo "옵션:"
                echo "  (없음)     UC 시스템만 설치 (기본)"
                echo "  --uc       UC (undetected-chromedriver) 시스템 설치"
                echo "  --no       nodriver 시스템 설치 (미구현)"
                echo "  --win      Windows UA 스푸핑 시스템 설치 (미구현)"
                echo "  --all      모든 시스템 설치"
                echo "  --help     이 도움말 표시"
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $arg"
                echo "도움말: $0 --help"
                exit 1
                ;;
        esac
    done
fi

echo "============================================================"
echo "🚀 Coupang Agent V2 자동 설치"
echo "============================================================"
echo ""
log_info "Installation directory: $SCRIPT_DIR"
log_info "Current user: $CURRENT_USER"
echo ""
log_info "설치 대상:"
if [ "$INSTALL_UC" = true ]; then
    echo "  ✓ UC (undetected-chromedriver)"
fi
if [ "$INSTALL_NO" = true ]; then
    echo "  ✓ nodriver (미구현)"
fi
if [ "$INSTALL_WIN" = true ]; then
    echo "  ✓ Windows UA 스푸핑 (미구현)"
fi
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
# 3. 시스템 라이브러리 설치 (Chrome 실행 + WireGuard)
# ===================================================================

log_step "3/9 시스템 라이브러리 설치 중..."
echo ""

log_info "필수 시스템 라이브러리 설치 중..."
log_info "  - WireGuard (VPN 키 풀용)"
log_info "  - Chrome 실행 라이브러리"
log_info "  - 네트워크 도구 (curl, jq 등)"
echo ""

sudo apt-get install -y \
    wireguard \
    wireguard-tools \
    openresolv \
    wget \
    curl \
    unzip \
    jq \
    git \
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
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    libnspr4 \
    xdg-utils \
    > /dev/null 2>&1

log_success "시스템 라이브러리 설치 완료"

# WireGuard 설치 확인
if command -v wg-quick &> /dev/null; then
    WG_VERSION=$(wg --version 2>&1 | head -1)
    log_success "WireGuard 설치 확인: $WG_VERSION"
else
    log_error "WireGuard 설치 실패!"
    exit 1
fi

# ===================================================================
# 4. Python 패키지 설치 (시스템 전역)
# ===================================================================

log_step "4/9 Python 패키지 설치 중 (시스템 전역)..."
echo ""

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    log_info "requirements.txt에서 패키지 설치 중..."
    log_warn "시스템 전역 설치 (모든 사용자가 접근 가능)"
    echo ""

    # Ubuntu 22.04+에서는 --break-system-packages 플래그 필요
    if pip3 install --help | grep -q "break-system-packages"; then
        sudo pip3 install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages
    else
        sudo pip3 install -r "$SCRIPT_DIR/requirements.txt"
    fi

    log_success "Python 패키지 설치 완료"

    # 설치 검증
    echo ""
    log_info "설치된 패키지 확인 중..."
    for pkg in undetected-chromedriver selenium Pillow requests pysocks psutil; do
        if python3 -c "import ${pkg//-/_}" 2>/dev/null; then
            log_success "  ✓ $pkg"
        else
            log_warn "  ⚠️  $pkg (설치 실패 또는 import 오류)"
        fi
    done
else
    log_error "requirements.txt not found!"
    exit 1
fi

# ===================================================================
# 5. Chrome 130, 144 설치
# ===================================================================

log_step "5/9 Chrome 130, 144 설치 중..."
echo ""

CHROME_BASE_DIR="$SCRIPT_DIR/chrome-version"
CHROME_FOR_TESTING_URL="https://storage.googleapis.com/chrome-for-testing-public"

mkdir -p "$CHROME_BASE_DIR"

# Chrome 130 설치
if [ -f "$CHROME_BASE_DIR/130/chrome-linux64/chrome" ]; then
    log_success "Chrome 130 이미 설치됨 (건너뛰기)"
else
    log_info "Chrome 130 (v130.0.6723.116) 다운로드 중..."

    CHROME_130_URL="${CHROME_FOR_TESTING_URL}/130.0.6723.116/linux64/chrome-linux64.zip"
    CHROME_130_ZIP="/tmp/chrome-130.zip"

    wget -q --show-progress "$CHROME_130_URL" -O "$CHROME_130_ZIP"

    if [ $? -eq 0 ]; then
        log_info "Chrome 130 압축 해제 중..."
        mkdir -p "$CHROME_BASE_DIR/130"
        unzip -q "$CHROME_130_ZIP" -d "$CHROME_BASE_DIR/130"
        chmod +x "$CHROME_BASE_DIR/130/chrome-linux64/chrome"
        rm -f "$CHROME_130_ZIP"
        log_success "Chrome 130 설치 완료"
    else
        log_error "Chrome 130 다운로드 실패"
        exit 1
    fi
fi

echo ""

# Chrome 144 설치
if [ -f "$CHROME_BASE_DIR/144/chrome-linux64/chrome" ]; then
    log_success "Chrome 144 이미 설치됨 (건너뛰기)"
else
    log_info "Chrome 144 (v144.0.7500.2) 다운로드 중..."

    CHROME_144_URL="${CHROME_FOR_TESTING_URL}/144.0.7500.2/linux64/chrome-linux64.zip"
    CHROME_144_ZIP="/tmp/chrome-144.zip"

    wget -q --show-progress "$CHROME_144_URL" -O "$CHROME_144_ZIP"

    if [ $? -eq 0 ]; then
        log_info "Chrome 144 압축 해제 중..."
        mkdir -p "$CHROME_BASE_DIR/144"
        unzip -q "$CHROME_144_ZIP" -d "$CHROME_BASE_DIR/144"
        chmod +x "$CHROME_BASE_DIR/144/chrome-linux64/chrome"
        rm -f "$CHROME_144_ZIP"
        log_success "Chrome 144 설치 완료"
    else
        log_error "Chrome 144 다운로드 실패"
        exit 1
    fi
fi

# ===================================================================
# 6. 디렉토리 생성
# ===================================================================

log_step "6/9 필요한 디렉토리 생성 중..."
echo ""

mkdir -p "$SCRIPT_DIR/browser-profiles"
mkdir -p "$SCRIPT_DIR/screenshots"
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/debug_logs"
mkdir -p "/tmp/vpn_configs"

chmod 755 "$SCRIPT_DIR/browser-profiles"
chmod 755 "$SCRIPT_DIR/screenshots"
chmod 755 "$SCRIPT_DIR/logs"
chmod 755 "$SCRIPT_DIR/debug_logs"
chmod 755 "/tmp/vpn_configs"

log_success "디렉토리 생성 완료"
log_info "  ✓ browser-profiles/ (브라우저 프로필)"
log_info "  ✓ screenshots/ (스크린샷 저장)"
log_info "  ✓ logs/ (워커 로그)"
log_info "  ✓ debug_logs/ (디버그 로그)"
log_info "  ✓ /tmp/vpn_configs/ (VPN 설정 임시 파일)"

# ===================================================================
# 7. VPN 키 풀 sudoers 설정 (WireGuard)
# ===================================================================

log_step "7/9 VPN 키 풀 sudoers 설정 중..."
echo ""

SUDOERS_FILE="/etc/sudoers.d/vpn-pool-access"

log_info "WireGuard wg-quick 명령어를 비밀번호 없이 실행하도록 설정 중..."
log_info "사용자: $CURRENT_USER"
echo ""

# sudoers 파일 생성
TEMP_SUDOERS=$(mktemp)

cat > "$TEMP_SUDOERS" <<EOF
# VPN 키 풀 시스템용 sudoers 설정
# wg-quick 명령어를 비밀번호 없이 실행 가능
# 생성일: $(date)

# $CURRENT_USER 사용자가 wg-quick 명령어를 NOPASSWD로 실행 가능
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/wg-quick
EOF

# sudoers 문법 검사
sudo visudo -c -f "$TEMP_SUDOERS" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    log_success "sudoers 문법 검사 통과"
    sudo cp "$TEMP_SUDOERS" "$SUDOERS_FILE"
    sudo chmod 440 "$SUDOERS_FILE"
    log_success "sudoers 파일 설치 완료: $SUDOERS_FILE"

    # 테스트
    if sudo -n wg-quick 2>&1 | grep -q "Usage"; then
        log_success "wg-quick 비밀번호 없이 실행 가능 ✓"
    else
        log_warn "테스트 실패 (재로그인 필요할 수 있음)"
    fi
else
    log_error "sudoers 문법 오류!"
fi

rm -f "$TEMP_SUDOERS"
echo ""

# ===================================================================
# 8. VPN 키 풀 서버 연결 테스트
# ===================================================================

log_step "8/8 VPN 키 풀 서버 연결 테스트..."
echo ""

VPN_API_SERVER="http://112.161.221.82:3000"
log_info "VPN 키 풀 API 서버: $VPN_API_SERVER"
echo ""

if curl -s --connect-timeout 5 "$VPN_API_SERVER/api/vpn/status" > /dev/null 2>&1; then
    log_success "VPN 키 풀 서버 연결 성공!"

    # 서버 상태 조회
    STATUS_JSON=$(curl -s "$VPN_API_SERVER/api/vpn/status")
    TOTAL_KEYS=$(echo "$STATUS_JSON" | jq -r '.statistics.total' 2>/dev/null || echo "?")
    AVAILABLE_KEYS=$(echo "$STATUS_JSON" | jq -r '.statistics.available' 2>/dev/null || echo "?")

    log_info "  📊 전체 키: $TOTAL_KEYS개"
    log_info "  📊 사용 가능: $AVAILABLE_KEYS개"
else
    log_warn "VPN 키 풀 서버 연결 실패"
    log_info "  서버가 실행 중인지 확인하세요"
    log_info "  URL: $VPN_API_SERVER"
fi

echo ""

# ===================================================================
# 9/9 WireGuard sudoers 설정 (VPN 키 풀 자동화)
# ===================================================================

log_step "9/9 WireGuard sudoers 설정 중..."
echo ""

SUDOERS_FILE="/etc/sudoers.d/wireguard"

log_info "WireGuard sudo 권한 설정 (비밀번호 없이 wg-quick 실행)"
log_info "  사용자: $CURRENT_USER"
log_info "  파일: $SUDOERS_FILE"
echo ""

# sudoers 파일 내용
SUDOERS_CONTENT="# WireGuard sudo 권한 (VPN 키 풀 시스템용)
# $CURRENT_USER 사용자가 비밀번호 없이 wg-quick 명령 실행 가능
# VPN 키 풀 시스템이 자동으로 WireGuard 연결/해제를 수행하기 위해 필요
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/wg-quick"

# 임시 파일에 작성
TMP_FILE=$(mktemp)
echo "$SUDOERS_CONTENT" > "$TMP_FILE"

# sudoers 문법 검증
log_info "sudoers 문법 검증 중..."
if sudo visudo -c -f "$TMP_FILE" > /dev/null 2>&1; then
    log_success "문법 검증 통과"

    # sudoers 파일 복사
    log_info "sudoers 파일 생성 중..."
    sudo cp "$TMP_FILE" "$SUDOERS_FILE"
    sudo chmod 0440 "$SUDOERS_FILE"

    log_success "WireGuard sudoers 설정 완료"
    log_info "  ✓ $CURRENT_USER는 이제 sudo wg-quick을 비밀번호 없이 실행 가능"
else
    log_error "sudoers 문법 오류 발생!"
    rm "$TMP_FILE"
fi

rm -f "$TMP_FILE"

echo ""

# ===================================================================
# 10/10 VPN 키 풀 워커 사용자 및 정책 라우팅 설정
# ===================================================================

log_step "10/10 VPN 키 풀 워커 사용자 및 정책 라우팅 설정 중..."
echo ""

log_info "VPN 키 풀 시스템용 시스템 사용자 생성 (wg101 ~ wg112)"
log_info "  UID 범위: 1101~1112"
log_info "  라우팅 테이블: 101~112"
echo ""

# VPN 워커 사용자 생성 및 정책 라우팅 설정
WORKERS_CREATED=0
RULES_ADDED=0

for i in {1..12}; do
    uid=$((1100 + i))          # Worker-1 → UID 1101, Worker-2 → UID 1102, ...
    username="wg$uid"          # wg101, wg102, ..., wg112
    table_num=$((100 + i))     # Table 101, 102, ..., 112

    # 사용자 생성 (이미 존재하면 스킵)
    if ! id "$username" &>/dev/null; then
        # ⚠️ -m 옵션으로 홈 디렉토리 생성
        # uc_run_workers.py가 브라우저 프로필을 /home/wg10N/ 아래에 저장
        sudo useradd -u $uid -m -s /bin/bash "$username" 2>/dev/null
        if [ $? -eq 0 ]; then
            ((WORKERS_CREATED++))
            log_info "  ✓ 사용자 생성: $username (UID $uid)"

            # 브라우저 프로필 디렉토리 생성 및 권한 설정
            sudo mkdir -p "$SCRIPT_DIR/uc_browser-profiles/$username"
            sudo chown -R $username:$username "$SCRIPT_DIR/uc_browser-profiles/$username"
            sudo chmod -R 755 "$SCRIPT_DIR/uc_browser-profiles/$username"
        fi
    else
        log_info "  ⊙ 사용자 존재: $username (UID $uid)"
        # 홈 디렉토리가 없으면 생성
        if [ ! -d "/home/$username" ]; then
            sudo mkdir -p "/home/$username"
            sudo chown $username:$username "/home/$username"
            sudo chmod 755 "/home/$username"
            log_info "  ✓ 홈 디렉토리 생성: /home/$username"
        fi

        # 브라우저 프로필 디렉토리 확인 및 생성
        if [ ! -d "$SCRIPT_DIR/uc_browser-profiles/$username" ]; then
            sudo mkdir -p "$SCRIPT_DIR/uc_browser-profiles/$username"
            sudo chown -R $username:$username "$SCRIPT_DIR/uc_browser-profiles/$username"
            sudo chmod -R 755 "$SCRIPT_DIR/uc_browser-profiles/$username"
            log_info "  ✓ 브라우저 프로필 디렉토리 생성: uc_browser-profiles/$username"
        fi
    fi

    # 정책 라우팅 규칙 추가 (중복 확인)
    if ! sudo ip rule list | grep -q "uidrange $uid-$uid"; then
        sudo ip rule add uidrange $uid-$uid lookup $table_num priority 100
        if [ $? -eq 0 ]; then
            ((RULES_ADDED++))
            log_info "  ✓ 라우팅 규칙 추가: UID $uid → 테이블 $table_num"
        fi
    else
        log_info "  ⊙ 라우팅 규칙 존재: UID $uid → 테이블 $table_num"
    fi
done

echo ""
log_success "VPN 워커 설정 완료"
log_info "  생성된 사용자: $WORKERS_CREATED개"
log_info "  추가된 라우팅 규칙: $RULES_ADDED개"

# sudoers 설정 (tech → wg10N 전환 가능)
VPNWORKER_SUDOERS="/etc/sudoers.d/wg-workers"

log_info "sudoers 설정 중 (tech → wg10N 전환 권한)..."

# sudoers 파일 내용
VPNWORKER_CONTENT="# VPN 키 풀 워커 전환 권한 (wg101-112 시스템)
# tech 사용자가 wg10N 사용자로 전환 가능 (Chrome 프로세스용)
$CURRENT_USER ALL=(wg101,wg102,wg103,wg104,wg105,wg106,wg107,wg108,wg109,wg110,wg111,wg112) NOPASSWD: ALL"

# 임시 파일 생성
TMP_FILE2=$(mktemp)
echo "$VPNWORKER_CONTENT" > "$TMP_FILE2"

# sudoers 문법 검증
if sudo visudo -c -f "$TMP_FILE2" > /dev/null 2>&1; then
    sudo cp "$TMP_FILE2" "$VPNWORKER_SUDOERS"
    sudo chmod 0440 "$VPNWORKER_SUDOERS"
    log_success "sudoers 설정 완료: $VPNWORKER_SUDOERS"
else
    log_warn "sudoers 설정 실패 (권한 확인 필요)"
fi

rm -f "$TMP_FILE2"

echo ""

# ===================================================================
# 11/11 네트워크 와치독 자동 실행 설정
# ===================================================================

log_step "11/11 네트워크 와치독 자동 실행 설정 중..."
echo ""

WATCHDOG_SCRIPT="$SCRIPT_DIR/network_watchdog.sh"

if [ -f "$WATCHDOG_SCRIPT" ]; then
    log_info "네트워크 와치독 스크립트 확인: $WATCHDOG_SCRIPT"

    # 실행 권한 부여
    chmod +x "$WATCHDOG_SCRIPT"

    # Crontab에 자동 실행 설정 추가
    log_info "Crontab 설정 중..."

    # 현재 crontab 백업
    crontab -l > /tmp/crontab_backup_$$.txt 2>/dev/null || true

    # 와치독 설정이 이미 있는지 확인
    if crontab -l 2>/dev/null | grep -q "network_watchdog.sh"; then
        log_info "  ⊙ 와치독 Crontab 설정 이미 존재"
    else
        # 새 crontab 설정 추가
        (
            crontab -l 2>/dev/null || true
            echo ""
            echo "# Network Watchdog - 네트워크 자동 복구 시스템"
            echo "# 5분마다 와치독 프로세스 확인 및 재시작"
            echo "*/5 * * * * pgrep -f \"network_watchdog.sh\" > /dev/null || nohup $WATCHDOG_SCRIPT > /tmp/network_watchdog.log 2>&1 &"
            echo ""
            echo "# 시스템 재부팅 시 자동 시작 (30초 대기 후)"
            echo "@reboot sleep 30 && nohup $WATCHDOG_SCRIPT > /tmp/network_watchdog.log 2>&1 &"
        ) | crontab -

        log_success "  ✓ Crontab 설정 완료"
        log_info "    - 5분마다 와치독 프로세스 확인"
        log_info "    - 재부팅 시 자동 시작"
    fi

    # 와치독 즉시 시작
    log_info "네트워크 와치독 시작 중..."

    if pgrep -f "network_watchdog.sh" > /dev/null; then
        log_info "  ⊙ 와치독 이미 실행 중"
    else
        nohup "$WATCHDOG_SCRIPT" > /tmp/network_watchdog.log 2>&1 &
        sleep 2

        if pgrep -f "network_watchdog.sh" > /dev/null; then
            log_success "  ✓ 네트워크 와치독 시작 완료"
            log_info "    로그: /tmp/network_watchdog.log"
        else
            log_warn "  ⚠️ 와치독 시작 실패 (수동 확인 필요)"
        fi
    fi
else
    log_warn "네트워크 와치독 스크립트 없음: $WATCHDOG_SCRIPT"
    log_info "  수동으로 network_watchdog.sh를 실행하세요"
fi

echo ""

# ===================================================================
# 설치 완료
# ===================================================================

echo ""
echo "============================================================"
log_success "🎉 설치 완료!"
echo "============================================================"
echo ""

# 설치된 구성 요소
echo -e "${GREEN}✅ 설치된 구성 요소:${NC}"
echo "  • Python $(python3 --version | awk '{print $2}')"
echo "  • pip $(pip3 --version | awk '{print $2}')"
echo "  • WireGuard $(wg --version 2>&1 | head -1)"
echo "  • undetected-chromedriver $(pip3 show undetected-chromedriver 2>/dev/null | grep Version | awk '{print $2}')"
echo "  • selenium $(pip3 show selenium 2>/dev/null | grep Version | awk '{print $2}')"
echo "  • psutil $(pip3 show psutil 2>/dev/null | grep Version | awk '{print $2}')"
echo "  • Chrome 130 (구버전 TLS)"
echo "  • Chrome 144 (최신 버전)"
echo "  • Network Watchdog (자동 네트워크 복구 시스템)"
echo ""

echo -e "${CYAN}🚀 다음 단계 (바로 실행 가능):${NC}"
echo ""
echo "  1️⃣  멀티 워커 실행 (권장):"
echo "     ${GREEN}python3 uc_run_workers.py -t 6${NC}"
echo ""
echo "  2️⃣  단일 Agent 테스트:"
echo "     ${GREEN}python3 uc_agent.py --version 130 --keyword \"노트북\" --close${NC}"
echo ""
echo "  3️⃣  네트워크 와치독 로그 확인:"
echo "     ${GREEN}tail -f /tmp/network_watchdog.log${NC}"
echo ""

echo -e "${BLUE}📚 추가 정보:${NC}"
echo "  • VPN_POOL_GUIDE.md: VPN 키 풀 시스템 설명"
echo "  • VPN_POOL_INTEGRATION_GUIDE.md: 통합 가이드"
echo "  • CLAUDE.md: 프로젝트 전체 가이드"
echo ""

echo -e "${YELLOW}⚠️  참고사항:${NC}"
echo "  • VPN 키 풀 방식 사용 (자동 키 할당/반납)"
echo "  • 네트워크 와치독 자동 실행 (5분마다 체크, 재부팅 시 자동 시작)"
echo "  • 네트워크 장애 시 자동 복구 (VPN 연결 정리 + 메인 라우팅 복구)"
echo "  • ${CURRENT_USER} 사용자만으로 모든 작업 가능"
echo "  • Chrome 버전 추가 설치: ./install-chrome-versions.sh [version]"
echo ""

log_info "모든 설치가 완료되었습니다. 바로 uc_run_workers.py를 실행할 수 있습니다!"
echo ""
