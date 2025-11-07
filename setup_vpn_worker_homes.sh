#!/bin/bash
#
# VPN 워커 홈 디렉토리 생성 및 권한 설정
#
# 문제: undetected-chromedriver가 /home/vpn-worker-N 디렉토리에 접근하려고 하지만
#       홈 디렉토리가 없거나 권한이 없어서 Permission denied 오류 발생
#
# 해결: vpn-worker-1 ~ vpn-worker-12 홈 디렉토리를 생성하고 적절한 권한 부여
#

echo "==========================================="
echo "VPN 워커 홈 디렉토리 설정"
echo "==========================================="

# VPN 워커 개수
MAX_WORKERS=12

echo ""
echo "📂 홈 디렉토리 생성 및 권한 설정 중..."

for i in $(seq 1 $MAX_WORKERS); do
    username="vpn-worker-$i"
    homedir="/home/$username"

    # 1. 홈 디렉토리 생성
    if [ ! -d "$homedir" ]; then
        echo "   생성: $homedir"
        sudo mkdir -p "$homedir"
    else
        echo "   존재: $homedir"
    fi

    # 2. 소유권 설정
    sudo chown "$username:$username" "$homedir"

    # 3. 권한 설정 (755: 소유자는 rwx, 그룹/기타는 rx)
    sudo chmod 755 "$homedir"

    # 4. .local 디렉토리 생성 (undetected-chromedriver가 사용)
    local_dir="$homedir/.local"
    if [ ! -d "$local_dir" ]; then
        sudo mkdir -p "$local_dir"
        sudo chown "$username:$username" "$local_dir"
        sudo chmod 755 "$local_dir"
    fi

    # 5. .cache 디렉토리 생성 (Selenium이 사용)
    cache_dir="$homedir/.cache"
    if [ ! -d "$cache_dir" ]; then
        sudo mkdir -p "$cache_dir"
        sudo chown "$username:$username" "$cache_dir"
        sudo chmod 755 "$cache_dir"
    fi
done

echo ""
echo "✅ 홈 디렉토리 설정 완료"

# 6. 확인
echo ""
echo "📋 생성된 홈 디렉토리:"
echo "-------------------------------------------"
ls -la /home/ | grep vpn-worker
echo "-------------------------------------------"

echo ""
echo "==========================================="
echo "✅ 설정 완료!"
echo "==========================================="
