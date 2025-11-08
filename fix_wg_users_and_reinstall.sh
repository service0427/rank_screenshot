#!/bin/bash
# 신서버 wg 사용자 수정 및 재설치 스크립트
# wg1101-1112 (잘못됨) → wg101-112 (정상)

echo "=============================================="
echo "🔧 wg 사용자 수정 및 재설치 스크립트"
echo "=============================================="
echo ""

# 1. 잘못된 사용자 삭제
echo "🗑️  1단계: 잘못된 사용자 삭제 (wg1101-1112)"
echo "=============================================="
for uid in {1101..1112}; do
    username="wg${uid}"
    if id "$username" &>/dev/null; then
        echo "   삭제 중: $username"
        sudo userdel -r "$username" 2>/dev/null || sudo userdel "$username" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "   ✓ 삭제 완료: $username"
        else
            echo "   ⚠️  삭제 실패: $username (수동 확인 필요)"
        fi
    fi
done

echo ""
echo "✅ 1단계 완료"
echo ""

# 2. 기존 sudoers 파일 삭제
echo "🗑️  2단계: 기존 sudoers 파일 정리"
echo "=============================================="
if [ -f "/etc/sudoers.d/vpn-pool-access" ]; then
    echo "   삭제 중: /etc/sudoers.d/vpn-pool-access"
    sudo rm -f /etc/sudoers.d/vpn-pool-access
    echo "   ✓ 삭제 완료"
fi

echo ""
echo "✅ 2단계 완료"
echo ""

# 3. 최신 코드 받기
echo "📥 3단계: 최신 코드 받기"
echo "=============================================="
git pull
if [ $? -eq 0 ]; then
    echo "✅ 3단계 완료"
else
    echo "❌ git pull 실패"
    exit 1
fi

echo ""

# 4. 올바른 사용자 생성 (setup.sh의 10/10 단계만 수동 실행)
echo "👥 4단계: 올바른 사용자 생성 (wg101-112)"
echo "=============================================="

for i in {1..12}; do
    uid=$((1100 + i))
    username="wg$((100 + i))"  # wg101, wg102, ...
    table_num=$((100 + i))

    if ! id "$username" &>/dev/null; then
        echo "   생성 중: $username (UID $uid)"
        sudo useradd -u $uid -m -s /bin/bash "$username" 2>/dev/null

        if [ $? -eq 0 ]; then
            echo "   ✓ 사용자 생성: $username"

            # 프로필 디렉토리 생성
            sudo mkdir -p "/home/tech/rank_screenshot/uc_browser-profiles/$username"
            sudo chown -R $username:$username "/home/tech/rank_screenshot/uc_browser-profiles/$username"
            sudo chmod -R 755 "/home/tech/rank_screenshot/uc_browser-profiles/$username"
            echo "   ✓ 프로필 디렉토리 생성"

            # 라우팅 규칙 추가
            if ! sudo ip rule list | grep -q "uidrange $uid-$uid"; then
                sudo ip rule add uidrange $uid-$uid lookup $table_num priority 100
                echo "   ✓ 라우팅 규칙 추가: UID $uid → 테이블 $table_num"
            fi
        else
            echo "   ❌ 사용자 생성 실패: $username"
        fi
    else
        echo "   ⊙ 사용자 존재: $username"
    fi
done

echo ""
echo "✅ 4단계 완료"
echo ""

# 5. sudoers 파일 생성
echo "🔐 5단계: sudoers 파일 생성"
echo "=============================================="

CURRENT_USER=$(whoami)
SUDOERS_FILE="/etc/sudoers.d/wg-access"

SUDOERS_CONTENT="# VPN 키 풀 워커 전환 권한 (wg101-112 시스템)
# tech 사용자가 wg101-112 사용자로 전환 가능
$CURRENT_USER ALL=(wg101,wg102,wg103,wg104,wg105,wg106,wg107,wg108,wg109,wg110,wg111,wg112) NOPASSWD: ALL"

# 임시 파일 생성
TMP_FILE=$(mktemp)
echo "$SUDOERS_CONTENT" > "$TMP_FILE"

# sudoers 문법 검증
if sudo visudo -c -f "$TMP_FILE" > /dev/null 2>&1; then
    sudo cp "$TMP_FILE" "$SUDOERS_FILE"
    sudo chmod 0440 "$SUDOERS_FILE"
    echo "✅ sudoers 파일 생성 완료: $SUDOERS_FILE"
else
    echo "❌ sudoers 문법 오류"
    rm -f "$TMP_FILE"
    exit 1
fi

rm -f "$TMP_FILE"

echo ""
echo "✅ 5단계 완료"
echo ""

# 6. 확인
echo "🔍 6단계: 설치 확인"
echo "=============================================="

echo ""
echo "📋 사용자 목록:"
getent passwd | grep "^wg10" | head -5

echo ""
echo "📋 sudoers 파일:"
ls -l /etc/sudoers.d/wg-access 2>/dev/null || echo "   ⚠️  sudoers 파일 없음"

echo ""
echo "📋 sudo 전환 테스트:"
if sudo -u wg101 whoami 2>/dev/null; then
    echo "   ✅ sudo -u wg101 whoami: 성공"
else
    echo "   ❌ sudo -u wg101 whoami: 실패"
fi

echo ""
echo "=============================================="
echo "✅ 전체 설치 완료!"
echo "=============================================="
echo ""
echo "다음 명령어로 최종 확인:"
echo "  ./check_sudoers_all.sh"
