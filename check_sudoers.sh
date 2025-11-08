#!/bin/bash
# wg10N sudoers 설정 진단 스크립트

echo "🔍 1. /etc/sudoers.d/wg-workers 파일 확인"
echo "=========================================="
if [ -f "/etc/sudoers.d/wg-workers" ]; then
    echo "✅ 파일 존재"
    echo ""
    echo "📄 파일 내용:"
    sudo cat /etc/sudoers.d/wg-workers
    echo ""
    echo "🔐 파일 권한:"
    ls -l /etc/sudoers.d/wg-workers
else
    echo "❌ 파일 없음 - sudoers 설정 필요!"
fi

echo ""
echo "🔍 2. sudoers 문법 검증"
echo "=========================================="
if [ -f "/etc/sudoers.d/wg-workers" ]; then
    if sudo visudo -c -f /etc/sudoers.d/wg-workers; then
        echo "✅ 문법 정상"
    else
        echo "❌ 문법 오류 있음!"
    fi
fi

echo ""
echo "🔍 3. tech 사용자의 sudo 권한 확인"
echo "=========================================="
sudo -l -U tech 2>&1 | grep -A 5 "wg10"

echo ""
echo "🔍 4. wg101 사용자로 전환 테스트"
echo "=========================================="
if sudo -u wg101 whoami 2>&1; then
    echo "✅ 전환 성공"
else
    echo "❌ 전환 실패"
fi

echo ""
echo "🔍 5. wg101 사용자 정보"
echo "=========================================="
getent passwd wg101
id wg101 2>&1

echo ""
echo "🔍 6. nsswitch.conf 확인 (사용자 DB 조회 순서)"
echo "=========================================="
grep "^passwd:" /etc/nsswitch.conf

echo ""
echo "🔍 7. PAM sudoers 설정 확인"
echo "=========================================="
if [ -f "/etc/pam.d/sudo" ]; then
    cat /etc/pam.d/sudo
fi
