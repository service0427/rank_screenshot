#!/bin/bash
#
# 네트워크 와치독 cron 자동 설정 스크립트
#
# 이 스크립트는:
# 1. 기존 와치독 프로세스 확인 및 종료
# 2. crontab에 와치독 재시작 작업 추가
# 3. 시스템 재부팅 시 자동 시작 설정
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHDOG_SCRIPT="$SCRIPT_DIR/network_watchdog.sh"
LOG_FILE="/tmp/network_watchdog.log"

echo "=========================================="
echo "🛡️  네트워크 와치독 Cron 설정"
echo "=========================================="

# 1. 실행 권한 확인
if [ ! -x "$WATCHDOG_SCRIPT" ]; then
    echo "❌ 와치독 스크립트 실행 권한 없음"
    echo "   권한 부여 중..."
    chmod +x "$WATCHDOG_SCRIPT"
    echo "   ✓ 권한 부여 완료"
fi

# 2. 기존 와치독 프로세스 확인
echo ""
echo "📋 기존 와치독 프로세스 확인..."
existing_pid=$(pgrep -f "network_watchdog.sh" | grep -v $$)

if [ -n "$existing_pid" ]; then
    echo "   ⚠️  기존 와치독 프로세스 발견 (PID: $existing_pid)"
    echo "   종료 중..."
    kill $existing_pid 2>/dev/null
    sleep 2

    # 강제 종료 확인
    if pgrep -f "network_watchdog.sh" > /dev/null; then
        echo "   강제 종료 중..."
        pkill -9 -f "network_watchdog.sh"
    fi
    echo "   ✓ 기존 프로세스 종료 완료"
else
    echo "   ✓ 기존 프로세스 없음"
fi

# 3. crontab 설정
echo ""
echo "⏰ Crontab 설정 중..."

# 현재 crontab 백업
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null

# 기존 와치독 cron 작업 제거
crontab -l 2>/dev/null | grep -v "network_watchdog.sh" > /tmp/crontab_new.txt

# 새로운 cron 작업 추가
cat >> /tmp/crontab_new.txt <<EOF

# 네트워크 와치독 자동 재시작 (매 5분마다 실행 중인지 확인)
*/5 * * * * pgrep -f "network_watchdog.sh" > /dev/null || nohup $WATCHDOG_SCRIPT > $LOG_FILE 2>&1 &

# 시스템 재부팅 시 자동 시작
@reboot sleep 30 && nohup $WATCHDOG_SCRIPT > $LOG_FILE 2>&1 &
EOF

# crontab 적용
crontab /tmp/crontab_new.txt
echo "   ✓ Crontab 설정 완료"

# 4. 설정 확인
echo ""
echo "📋 설정된 Cron 작업:"
echo "----------------------------------------"
crontab -l | grep -A 1 "네트워크 와치독"
echo "----------------------------------------"

# 5. 즉시 와치독 시작
echo ""
echo "🚀 네트워크 와치독 즉시 시작..."
nohup "$WATCHDOG_SCRIPT" > "$LOG_FILE" 2>&1 &
sleep 2

# 6. 실행 확인
if pgrep -f "network_watchdog.sh" > /dev/null; then
    watchdog_pid=$(pgrep -f "network_watchdog.sh")
    echo "   ✅ 와치독 실행 중 (PID: $watchdog_pid)"
else
    echo "   ❌ 와치독 시작 실패"
    exit 1
fi

# 7. 로그 확인
echo ""
echo "📝 최근 로그 (3줄):"
echo "----------------------------------------"
tail -3 "$LOG_FILE" 2>/dev/null || echo "   (아직 로그 없음)"
echo "----------------------------------------"

echo ""
echo "=========================================="
echo "✅ 설정 완료!"
echo "=========================================="
echo ""
echo "📌 유용한 명령어:"
echo "   로그 실시간 확인: tail -f $LOG_FILE"
echo "   와치독 상태 확인: pgrep -f network_watchdog.sh"
echo "   와치독 수동 종료: pkill -f network_watchdog.sh"
echo "   Cron 확인:      crontab -l | grep watchdog"
echo ""
