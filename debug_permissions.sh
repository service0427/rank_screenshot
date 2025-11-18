#!/bin/bash
# 배포 서버 권한 디버깅 스크립트

echo "=========================================="
echo "배포 서버 권한 진단 스크립트"
echo "=========================================="
echo ""

# 1. 프로젝트 경로 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "1. 프로젝트 경로"
echo "   $SCRIPT_DIR"
echo ""

# 2. 주요 파일 권한 확인
echo "2. 주요 파일 권한"
ls -la "$SCRIPT_DIR/uc_agent.py"
ls -la "$SCRIPT_DIR/uc_run_workers.py"
echo ""

# 3. 디렉토리 권한 확인
echo "3. 디렉토리 권한"
ls -ld "$SCRIPT_DIR"
ls -ld "$(dirname "$SCRIPT_DIR")"
echo ""

# 4. Python 경로 확인
echo "4. Python 경로"
which python3
python3 --version
echo ""

# 5. wg 사용자 확인
echo "5. wg101-112 사용자 확인"
for i in {101..112}; do
    user="wg$i"
    if id "$user" &>/dev/null; then
        echo "   ✓ $user (UID: $(id -u $user))"
    else
        echo "   ✗ $user (없음)"
    fi
done
echo ""

# 6. wg101로 파일 읽기 테스트
echo "6. wg101 사용자로 uc_agent.py 읽기 테스트"
if id wg101 &>/dev/null; then
    sudo -u wg101 cat "$SCRIPT_DIR/uc_agent.py" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✓ wg101이 uc_agent.py를 읽을 수 있음"
    else
        echo "   ✗ wg101이 uc_agent.py를 읽을 수 없음"
        echo "   에러:"
        sudo -u wg101 cat "$SCRIPT_DIR/uc_agent.py" 2>&1 | head -5
    fi
else
    echo "   ✗ wg101 사용자가 없음"
fi
echo ""

# 7. wg101로 Python 실행 테스트
echo "7. wg101 사용자로 Python 실행 테스트"
if id wg101 &>/dev/null; then
    sudo -u wg101 python3 -c "print('Hello')" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✓ wg101이 python3를 실행할 수 있음"
    else
        echo "   ✗ wg101이 python3를 실행할 수 없음"
        echo "   에러:"
        sudo -u wg101 python3 -c "print('Hello')" 2>&1
    fi
else
    echo "   ✗ wg101 사용자가 없음"
fi
echo ""

# 8. wg101로 uc_agent.py 실행 테스트
echo "8. wg101 사용자로 uc_agent.py 읽기 권한 테스트"
if id wg101 &>/dev/null; then
    sudo -u wg101 python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); open('$SCRIPT_DIR/uc_agent.py').close(); print('OK')" 2>&1
else
    echo "   ✗ wg101 사용자가 없음"
fi
echo ""

# 9. 절대 경로로 실행 테스트
echo "9. 절대 경로로 uc_agent.py --help 실행 테스트"
if id wg101 &>/dev/null; then
    sudo -u wg101 python3 "$SCRIPT_DIR/uc_agent.py" --help > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✓ wg101이 uc_agent.py를 실행할 수 있음"
    else
        echo "   ✗ wg101이 uc_agent.py를 실행할 수 없음"
        echo "   에러:"
        sudo -u wg101 python3 "$SCRIPT_DIR/uc_agent.py" --help 2>&1 | head -10
    fi
else
    echo "   ✗ wg101 사용자가 없음"
fi
echo ""

# 10. SELinux/AppArmor 확인
echo "10. 보안 모듈 확인"
if command -v getenforce &>/dev/null; then
    echo "   SELinux: $(getenforce)"
else
    echo "   SELinux: 설치 안됨"
fi

if systemctl is-active --quiet apparmor; then
    echo "   AppArmor: 활성화"
else
    echo "   AppArmor: 비활성화 또는 설치 안됨"
fi
echo ""

echo "=========================================="
echo "진단 완료"
echo "=========================================="
