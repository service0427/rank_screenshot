#!/bin/bash
# 전체 sudoers 설정 확인 스크립트

echo "🔍 1. /etc/sudoers.d/ 디렉토리 전체 파일 목록"
echo "=========================================="
ls -la /etc/sudoers.d/

echo ""
echo "🔍 2. wg101-112 사용자 존재 여부"
echo "=========================================="
for i in {101..112}; do
    if id "wg$i" &>/dev/null; then
        id "wg$i"
    else
        echo "❌ wg$i: 사용자 없음"
    fi
done | head -5

echo ""
echo "🔍 3. 전체 사용자 목록에서 wg 검색"
echo "=========================================="
getent passwd | grep "^wg" | head -5

echo ""
echo "🔍 4. UID 1101-1112 범위 사용자 확인"
echo "=========================================="
getent passwd | awk -F: '$3 >= 1101 && $3 <= 1112 {print $0}'

echo ""
echo "🔍 5. tech 사용자의 sudo 권한 확인"
echo "=========================================="
sudo -l -U tech 2>&1 | grep -E "User tech|RunAs|wg"
