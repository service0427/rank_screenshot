#!/bin/bash

# ========================================
# Chrome 버전별 최신 빌드 자동 다운로드 스크립트
# ========================================
#
# Chrome for Testing API를 사용하여 각 메이저 버전의
# 가장 높은 빌드 번호를 자동으로 찾아서 설치합니다.
#
# 사용법:
#   ./install-chrome-latest.sh 130 131 132    # 특정 버전 설치
#   ./install-chrome-latest.sh all            # 모든 버전 설치
#   ./install-chrome-latest.sh list           # 사용 가능한 버전 목록
#   ./install-chrome-latest.sh                # 인터랙티브 모드
#
# ========================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설치 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/chrome-version"
TEMP_DIR="/tmp/chrome-install-$$"

# Chrome for Testing API URL
API_URL="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"

# ========================================
# 유틸리티 함수
# ========================================

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ========================================
# Chrome 버전 정보 가져오기
# ========================================

fetch_versions() {
    print_info "Chrome for Testing API에서 버전 정보를 가져오는 중..."

    if ! curl -s "$API_URL" -o "$TEMP_DIR/versions.json"; then
        print_error "API 접근 실패"
        exit 1
    fi

    print_success "버전 정보 다운로드 완료"
}

# ========================================
# 메이저 버전별 최신 빌드 찾기
# ========================================

get_latest_build() {
    local major_version=$1
    local latest_version=$(jq -r --arg major "$major_version" '
        .versions[]
        | select(.version | startswith($major + "."))
        | .version
    ' "$TEMP_DIR/versions.json" | sort -V | tail -n1)

    echo "$latest_version"
}

# ========================================
# 다운로드 URL 가져오기
# ========================================

get_download_url() {
    local version=$1
    local url=$(jq -r --arg ver "$version" '
        .versions[]
        | select(.version == $ver)
        | .downloads.chrome[]?
        | select(.platform == "linux64")
        | .url
    ' "$TEMP_DIR/versions.json")

    echo "$url"
}

# ========================================
# Chrome 다운로드 및 설치
# ========================================

install_chrome() {
    local version=$1
    local major_version=$(echo "$version" | cut -d'.' -f1)
    local target_dir="${INSTALL_DIR}/${major_version}"

    # 이미 설치되어 있는지 확인
    if [ -f "$target_dir/chrome-linux64/chrome" ]; then
        local installed_version=$(cat "$target_dir/VERSION" 2>/dev/null || echo "unknown")
        if [ "$installed_version" = "$version" ]; then
            print_warning "Chrome $version 이미 설치됨 (건너뜀)"
            return 0
        else
            print_info "기존 버전 ($installed_version) 제거 후 재설치"
            rm -rf "$target_dir"
        fi
    fi

    print_header "Chrome $version 설치 중"

    # 다운로드 URL 가져오기
    local download_url=$(get_download_url "$version")

    if [ -z "$download_url" ]; then
        print_error "다운로드 URL을 찾을 수 없습니다: $version"
        return 1
    fi

    print_info "다운로드 URL: $download_url"

    # 임시 디렉토리 생성
    mkdir -p "$TEMP_DIR/download"

    # 다운로드
    print_info "다운로드 중..."
    if ! curl -# -L "$download_url" -o "$TEMP_DIR/download/chrome.zip"; then
        print_error "다운로드 실패"
        return 1
    fi

    # 압축 해제
    print_info "압축 해제 중..."
    if ! unzip -q "$TEMP_DIR/download/chrome.zip" -d "$TEMP_DIR/download"; then
        print_error "압축 해제 실패"
        return 1
    fi

    # 설치 디렉토리로 이동
    mkdir -p "$target_dir"
    mv "$TEMP_DIR/download/chrome-linux64" "$target_dir/"

    # VERSION 파일 생성
    echo "$version" > "$target_dir/VERSION"

    # 실행 권한 부여
    chmod +x "$target_dir/chrome-linux64/chrome"

    # 임시 파일 정리
    rm -rf "$TEMP_DIR/download"

    print_success "Chrome $version 설치 완료: $target_dir"

    # 설치 확인
    local chrome_path="$target_dir/chrome-linux64/chrome"
    if [ -f "$chrome_path" ]; then
        local actual_version=$("$chrome_path" --version 2>/dev/null | cut -d' ' -f3 || echo "unknown")
        print_info "실행 파일 버전: $actual_version"
    fi
}

# ========================================
# 사용 가능한 메이저 버전 목록
# ========================================

list_available_versions() {
    print_header "사용 가능한 Chrome 메이저 버전"

    fetch_versions

    # 메이저 버전 추출 (중복 제거)
    local major_versions=$(jq -r '.versions[].version' "$TEMP_DIR/versions.json" \
        | cut -d'.' -f1 \
        | sort -V \
        | uniq)

    echo ""
    echo -e "${BLUE}메이저 버전 | 최신 빌드${NC}"
    echo -e "${BLUE}-----------|------------${NC}"

    for major in $major_versions; do
        local latest=$(get_latest_build "$major")
        local status=""

        # 설치 상태 확인
        if [ -f "${INSTALL_DIR}/${major}/VERSION" ]; then
            local installed=$(cat "${INSTALL_DIR}/${major}/VERSION")
            if [ "$installed" = "$latest" ]; then
                status=" ${GREEN}[설치됨]${NC}"
            else
                status=" ${YELLOW}[구버전: $installed]${NC}"
            fi
        fi

        echo -e "${major}        | ${latest}${status}"
    done

    echo ""
}

# ========================================
# 현재 설치된 버전 표시
# ========================================

show_installed_versions() {
    print_header "현재 설치된 Chrome 버전"

    if [ ! -d "$INSTALL_DIR" ]; then
        print_warning "설치된 버전이 없습니다"
        return
    fi

    echo ""
    for version_dir in "$INSTALL_DIR"/*; do
        if [ -d "$version_dir" ]; then
            local major=$(basename "$version_dir")
            local version=$(cat "$version_dir/VERSION" 2>/dev/null || echo "unknown")
            local chrome_path="$version_dir/chrome-linux64/chrome"

            if [ -f "$chrome_path" ]; then
                local actual_version=$("$chrome_path" --version 2>/dev/null | cut -d' ' -f3 || echo "error")
                echo -e "${GREEN}Chrome $major${NC}: $version (실제: $actual_version)"
                echo "  경로: $version_dir"
            else
                echo -e "${RED}Chrome $major${NC}: $version (실행 파일 없음)"
            fi
            echo ""
        fi
    done
}

# ========================================
# 인터랙티브 모드
# ========================================

interactive_mode() {
    print_header "Chrome 버전 설치 (인터랙티브 모드)"

    # 현재 설치된 버전 표시
    show_installed_versions

    # 사용 가능한 버전 표시
    list_available_versions

    echo ""
    echo -e "${BLUE}설치할 메이저 버전을 입력하세요 (예: 130 131 132)${NC}"
    echo -e "${BLUE}또는 'all'을 입력하여 모든 버전 설치${NC}"
    echo -e "${BLUE}취소하려면 Enter를 누르세요${NC}"
    echo ""
    read -p "입력: " versions

    if [ -z "$versions" ]; then
        print_info "취소됨"
        exit 0
    fi

    if [ "$versions" = "all" ]; then
        install_all_versions
    else
        for version in $versions; do
            install_version "$version"
        done
    fi
}

# ========================================
# 특정 메이저 버전 설치
# ========================================

install_version() {
    local major_version=$1

    # 최신 빌드 찾기
    local latest_build=$(get_latest_build "$major_version")

    if [ -z "$latest_build" ]; then
        print_error "Chrome $major_version의 빌드를 찾을 수 없습니다"
        return 1
    fi

    print_info "Chrome $major_version의 최신 빌드: $latest_build"

    # 설치
    install_chrome "$latest_build"
}

# ========================================
# 모든 버전 설치
# ========================================

install_all_versions() {
    print_header "모든 Chrome 버전 설치"

    # 메이저 버전 목록 가져오기
    local major_versions=$(jq -r '.versions[].version' "$TEMP_DIR/versions.json" \
        | cut -d'.' -f1 \
        | sort -V \
        | uniq)

    local total=$(echo "$major_versions" | wc -l)
    local count=0

    for major in $major_versions; do
        count=$((count + 1))
        print_info "진행: $count/$total"
        install_version "$major"
        echo ""
    done

    print_success "모든 버전 설치 완료"
}

# ========================================
# 권장 버전 설치 (130, 140+)
# ========================================

install_recommended_versions() {
    print_header "권장 Chrome 버전 설치"
    print_info "구버전 TLS (130) + 최신 버전들 (140+)"

    # 130 버전 (구버전 TLS 대표)
    install_version 130

    # 140 이상의 모든 버전
    local major_versions=$(jq -r '.versions[].version' "$TEMP_DIR/versions.json" \
        | cut -d'.' -f1 \
        | sort -V \
        | uniq \
        | awk '$1 >= 140')

    for major in $major_versions; do
        install_version "$major"
    done

    print_success "권장 버전 설치 완료"
}

# ========================================
# 메인 실행 로직
# ========================================

main() {
    # 임시 디렉토리 생성
    mkdir -p "$TEMP_DIR"
    trap "rm -rf $TEMP_DIR" EXIT

    # 설치 디렉토리 생성
    mkdir -p "$INSTALL_DIR"

    # 버전 정보 다운로드
    fetch_versions

    # 인자 처리
    if [ $# -eq 0 ]; then
        # 인터랙티브 모드
        interactive_mode
    elif [ "$1" = "list" ]; then
        # 버전 목록 표시
        list_available_versions
    elif [ "$1" = "installed" ]; then
        # 설치된 버전 표시
        show_installed_versions
    elif [ "$1" = "all" ]; then
        # 모든 버전 설치
        install_all_versions
    elif [ "$1" = "recommended" ]; then
        # 권장 버전 설치
        install_recommended_versions
    else
        # 특정 버전 설치
        for version in "$@"; do
            install_version "$version"
            echo ""
        done
    fi

    echo ""
    print_success "완료!"

    # 최종 설치 상태 표시
    show_installed_versions
}

# 실행
main "$@"
