#!/bin/bash

#######################################
# Chrome 130, 144 자동 설치 스크립트
# 실행하면 기존 폴더 확인 후 없으면 자동 설치
#######################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHROME_BASE_DIR="$SCRIPT_DIR/chrome-version"
CHROME_FOR_TESTING_URL="https://storage.googleapis.com/chrome-for-testing-public"

# 설치할 버전 (major version => full version)
declare -A VERSIONS=(
    ["130"]="130.0.6723.116"
    ["144"]="144.0.7500.2"
)

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Chrome 다운로드 및 설치
install_chrome() {
    local major=$1
    local version=$2
    local version_dir="${CHROME_BASE_DIR}/${major}"

    # 이미 설치되어 있는지 확인
    if [ -d "$version_dir" ] && [ -f "$version_dir/chrome-linux64/chrome" ]; then
        print_success "Chrome ${major} 이미 설치됨: $version_dir"
        return 0
    fi

    print_info "Chrome ${major} (v${version}) 다운로드 중..."

    mkdir -p "$version_dir"

    # 다운로드 URL
    local chrome_url="${CHROME_FOR_TESTING_URL}/${version}/linux64/chrome-linux64.zip"
    local zip_file="/tmp/chrome-${major}.zip"

    # 다운로드 (재시도 3회)
    local retry=0
    while [ $retry -lt 3 ]; do
        if wget -q --show-progress "$chrome_url" -O "$zip_file" 2>&1; then
            break
        fi
        retry=$((retry + 1))
        if [ $retry -lt 3 ]; then
            print_warning "다운로드 실패, 재시도 중 ($retry/3)..."
            sleep 2
        else
            print_error "다운로드 실패: $chrome_url"
            rm -f "$zip_file"
            return 1
        fi
    done

    print_info "압축 해제 중..."

    # 압축 해제
    if command -v unzip &> /dev/null; then
        unzip -q "$zip_file" -d "$version_dir"
    else
        print_error "unzip이 설치되지 않았습니다: sudo apt-get install unzip"
        rm -f "$zip_file"
        return 1
    fi

    rm -f "$zip_file"

    # 검증
    if [ -f "$version_dir/chrome-linux64/chrome" ]; then
        echo "$version" > "$version_dir/VERSION"
        chmod +x "$version_dir/chrome-linux64/chrome"
        print_success "Chrome ${major} 설치 완료: $version_dir"
        return 0
    else
        print_error "Chrome 바이너리를 찾을 수 없습니다"
        return 1
    fi
}

# 메인 실행
echo "============================================================"
echo "🔧 Chrome 130, 144 자동 설치"
echo "============================================================"
echo ""

mkdir -p "$CHROME_BASE_DIR"

installed=0
skipped=0
failed=0

for major in 130 144; do
    version="${VERSIONS[$major]}"

    if install_chrome "$major" "$version"; then
        if [ -d "${CHROME_BASE_DIR}/${major}" ]; then
            # 방금 설치되었는지, 이미 있었는지 구분
            if [ $? -eq 0 ]; then
                installed=$((installed + 1))
            fi
        fi
    else
        failed=$((failed + 1))
    fi
    echo ""
done

echo "============================================================"
echo "📊 설치 결과"
echo "============================================================"
echo ""

# 현재 설치된 버전 확인
echo -e "${GREEN}✅ 설치된 Chrome 버전:${NC}"
for major in 130 144; do
    version_dir="${CHROME_BASE_DIR}/${major}"
    if [ -d "$version_dir" ] && [ -f "$version_dir/chrome-linux64/chrome" ]; then
        version=$(cat "$version_dir/VERSION" 2>/dev/null || echo "unknown")
        echo "  • Chrome ${major}: v${version}"
    fi
done

echo ""

if [ $failed -gt 0 ]; then
    print_error "설치 실패: $failed 개"
    exit 1
else
    print_success "모든 Chrome 버전 준비 완료!"
    echo ""
    echo "다음 명령어로 테스트하세요:"
    echo "  python3 agent.py --version 130 --close"
    echo "  python3 agent.py --version 144 --close"
    echo ""
fi
