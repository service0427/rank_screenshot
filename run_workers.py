#!/usr/bin/env python3
"""
멀티 워커 실행 스크립트
여러 스레드로 agent.py를 반복 실행
"""

import subprocess
import threading
import time
import argparse
import random
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 스크립트 디렉토리 및 로그 디렉토리 설정
# ============================================================
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = SCRIPT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def log_result(worker_id: int, vpn: str, chrome_version: str, success: bool, error_msg: str = None, screenshot_id: int = None):
    """
    VPN별 성공/실패 로그를 일자별 TXT 파일에 기록

    Args:
        worker_id: 워커 ID
        vpn: VPN 번호 또는 'L' (local)
        chrome_version: Chrome 버전
        success: 성공 여부
        error_msg: 에러 메시지 (실패 시)
        screenshot_id: 작업 ID (성공 시)
    """
    try:
        # 오늘 날짜로 파일명 생성
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOGS_DIR / f"{today}.txt"

        # 타임스탬프
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # VPN/Proxy 표시
        if vpn == 'L' or vpn is None:
            vpn_str = "Local"
        elif vpn == 'P':
            vpn_str = "Proxy"
        else:
            vpn_str = f"VPN {vpn}"

        # 상태 및 상세 정보
        if success:
            status = "SUCCESS"
            details = f"screenshot_id: {screenshot_id}" if screenshot_id else "no work assigned"
        else:
            status = "FAILED"
            details = error_msg if error_msg else "unknown error"

        # 로그 라인 생성
        log_line = f"{timestamp} | Worker-{worker_id} | {vpn_str:8} | Chrome {chrome_version:6} | {status:7} | {details}\n"

        # 파일에 append
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)

    except Exception as e:
        print(f"⚠️  로그 기록 실패: {e}")


def scan_chrome_versions() -> list:
    """
    chrome-version/ 폴더를 스캔하여 설치된 버전 목록 반환

    Returns:
        설치된 Chrome 버전 리스트 (예: ['130', '144', 'beta'])
    """
    chrome_dir = SCRIPT_DIR / "chrome-version"
    versions = []

    if not chrome_dir.exists():
        return versions

    for version_dir in chrome_dir.iterdir():
        if version_dir.is_dir():
            chrome_bin = version_dir / "chrome-linux64" / "chrome"
            if chrome_bin.exists():
                versions.append(version_dir.name)

    return sorted(versions)


def cleanup_all_chrome_processes():
    """
    모든 사용자의 Chrome 프로세스 정리 (워커 시작 시 한 번만 호출)
    """
    try:
        # tech 사용자의 Chrome 정리
        current_user = os.getenv('USER', 'tech')
        result = subprocess.run(
            f"ps aux | grep {current_user} | grep chrome | grep -v grep | wc -l",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        tech_count = int(result.stdout.strip()) if result.stdout.strip() else 0

        if tech_count > 0:
            print(f"   🧹 {current_user} 사용자의 Chrome {tech_count}개 정리 중...")
            subprocess.run(
                f"pkill -U {current_user} -f chrome",
                shell=True,
                capture_output=True,
                timeout=5
            )

        # 모든 VPN 사용자의 Chrome 정리
        vpn_users = []
        result = subprocess.run(
            "ps aux | grep chrome | grep -v grep | awk '{print $1}' | grep '^vpn' | sort -u",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.stdout.strip():
            vpn_users = result.stdout.strip().split('\n')

        for vpn_user in vpn_users:
            if vpn_user:
                # VPN 사용자의 Chrome 개수 확인
                result = subprocess.run(
                    f"ps aux | grep {vpn_user} | grep chrome | grep -v grep | wc -l",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                vpn_count = int(result.stdout.strip()) if result.stdout.strip() else 0

                if vpn_count > 0:
                    print(f"   🧹 {vpn_user} 사용자의 Chrome {vpn_count}개 정리 중...")
                    subprocess.run(
                        f"sudo -u {vpn_user} pkill -f chrome",
                        shell=True,
                        capture_output=True,
                        timeout=5
                    )

        total_cleaned = tech_count + sum([int(subprocess.run(
            f"ps aux | grep {u} | grep chrome | grep -v grep | wc -l",
            shell=True, capture_output=True, text=True, timeout=5
        ).stdout.strip() or 0) for u in vpn_users])

        if total_cleaned > 0:
            time.sleep(2)
            print(f"   ✓ 전체 Chrome 프로세스 정리 완료")

    except Exception as e:
        print(f"   ⚠️  Chrome 전체 정리 실패: {e}")


def zombie_reaper_thread():
    """
    백그라운드에서 주기적으로 좀비 프로세스 회수
    (daemon 스레드로 실행되어 프로그램 종료 시 자동 종료)
    """
    import os

    while True:
        try:
            # WNOHANG: 좀비가 없으면 즉시 반환
            while True:
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    if pid == 0:
                        break  # 더 이상 회수할 좀비 없음
                    # 좀비 회수 성공 (로그는 최소화)
                except ChildProcessError:
                    break  # 자식 프로세스 없음
        except Exception:
            pass  # 에러 무시

        time.sleep(10)  # 10초마다 체크


def cleanup_chrome_processes(vpn=None, instance_id=None):
    """
    남아있는 Chrome 프로세스를 강제 종료

    Args:
        vpn: VPN 번호, 'L' (Local), 'P' (Proxy)
        instance_id: 워커 ID (None이면 모든 Chrome 종료)
    """
    try:
        if vpn and vpn != 'L' and vpn != 'P':
            # VPN 사용자의 Chrome 프로세스 종료
            user = f"vpn{vpn}"

            # 프로세스 확인
            check_cmd = f"sudo -u {user} bash -c 'ps aux | grep chrome | grep -v grep'"
            result = subprocess.run(
                check_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.stdout.strip():
                print(f"   🧹 {user}의 Chrome 프로세스 정리 중...")
                # pkill로 종료 (stderr 무시)
                kill_cmd = f"sudo -u {user} pkill -f chrome"
                subprocess.run(kill_cmd, shell=True, capture_output=True, timeout=5)
                time.sleep(1)
                print(f"   ✓ {user}의 Chrome 프로세스 정리 완료")
        else:
            # Local/Proxy (현재 사용자)의 Chrome 프로세스만 종료
            current_user = os.getenv('USER', 'tech')

            # 현재 사용자의 Chrome 프로세스만 확인
            result = subprocess.run(
                f"ps aux | grep {current_user} | grep chrome | grep -v grep",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.stdout.strip():
                print(f"   🧹 Chrome 프로세스 정리 중 (사용자: {current_user})...")
                # 현재 사용자의 프로세스만 종료 (stderr 무시)
                subprocess.run(
                    f"pkill -U {current_user} -f chrome",
                    shell=True,
                    capture_output=True,  # stderr 출력 숨김
                    timeout=5
                )
                time.sleep(1)
                print(f"   ✓ Chrome 프로세스 정리 완료")

    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Chrome 프로세스 정리 타임아웃")
    except Exception as e:
        print(f"   ⚠️  Chrome 프로세스 정리 실패: {e}")


# ============================================================
# 창 위치 및 크기 설정 (워커별 수동 지정)
# ============================================================
WINDOW_WIDTH = 1300       # Chrome 창 너비
WINDOW_HEIGHT = 1200      # Chrome 창 높이

# 워커별 창 위치 (수동 조정 가능)
WORKER_POSITIONS = {
    1: {'x': 0,    'y': 0},
    2: {'x': 1260, 'y': 0},
    3: {'x': 2520, 'y': 0},
    4: {'x': 0,    'y': 1200},
    5: {'x': 1260, 'y': 1200},
    6: {'x': 2520, 'y': 1200},
}

MAX_WORKERS = 6           # 최대 워커 수


class BlockedCombinationsManager:
    """
    VPN + Chrome 버전 조합의 차단 상태 관리

    차단된 조합은 JSON 파일에 저장하고, 10분간 재시도하지 않음.
    10분 후 재시도해서 성공하면 차단 목록에서 제거.
    """

    def __init__(self, json_path: str = None):
        if json_path is None:
            json_path = SCRIPT_DIR / "blocked_combinations.json"
        self.json_path = Path(json_path)
        self.lock = threading.Lock()
        self.cooldown_minutes = 10
        self.data = self.load()

    def load(self):
        """JSON 파일에서 차단 목록 로드"""
        if not self.json_path.exists():
            return {}

        try:
            with open(self.json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  차단 목록 로드 실패: {e}")
            return {}

    def save(self):
        """JSON 파일에 차단 목록 저장"""
        try:
            with open(self.json_path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"⚠️  차단 목록 저장 실패: {e}")

    def _get_key(self, vpn, version):
        """VPN + 버전 조합 키 생성"""
        vpn_str = "local" if vpn == 'L' or vpn is None else f"vpn{vpn}"
        return f"{vpn_str}_{version}"

    def is_blocked(self, vpn, version):
        """
        차단 여부 확인 (10분 쿨다운 체크)

        Returns:
            tuple: (is_blocked: bool, remaining_seconds: int)
        """
        with self.lock:
            key = self._get_key(vpn, version)

            if key not in self.data:
                return False, 0

            blocked_at_str = self.data[key].get('blocked_at')
            if not blocked_at_str:
                return False, 0

            try:
                blocked_at = datetime.fromisoformat(blocked_at_str)
                now = datetime.now()
                elapsed = (now - blocked_at).total_seconds()
                cooldown_seconds = self.cooldown_minutes * 60

                if elapsed < cooldown_seconds:
                    remaining = int(cooldown_seconds - elapsed)
                    return True, remaining
                else:
                    # 쿨다운 시간이 지났으므로 재시도 가능
                    return False, 0
            except Exception as e:
                print(f"⚠️  차단 시간 파싱 실패: {e}")
                return False, 0

    def mark_blocked(self, vpn, version, reason=""):
        """조합을 차단 목록에 추가/업데이트"""
        with self.lock:
            key = self._get_key(vpn, version)
            self.data[key] = {
                'blocked_at': datetime.now().isoformat(),
                'vpn': vpn,
                'version': version,
                'reason': reason
            }
            self.save()

            vpn_str = "local" if vpn == 'L' or vpn is None else f"VPN {vpn}"
            print(f"   🚫 차단 조합 기록: {vpn_str} + Chrome {version}")
            print(f"   ⏰ {self.cooldown_minutes}분 후 재시도 가능")

    def mark_success(self, vpn, version):
        """성공 시 차단 목록에서 제거"""
        with self.lock:
            key = self._get_key(vpn, version)

            if key in self.data:
                del self.data[key]
                self.save()

                vpn_str = "local" if vpn == 'L' or vpn is None else f"VPN {vpn}"
                print(f"   ✅ 차단 해제: {vpn_str} + Chrome {version}")

    def get_stats(self):
        """차단 목록 통계"""
        with self.lock:
            active_blocks = []
            expired_blocks = []

            now = datetime.now()
            cooldown_seconds = self.cooldown_minutes * 60

            for key, info in self.data.items():
                try:
                    blocked_at = datetime.fromisoformat(info['blocked_at'])
                    elapsed = (now - blocked_at).total_seconds()

                    if elapsed < cooldown_seconds:
                        remaining = int(cooldown_seconds - elapsed)
                        active_blocks.append((key, remaining))
                    else:
                        expired_blocks.append(key)
                except Exception:
                    expired_blocks.append(key)

            return {
                'active': active_blocks,
                'expired': expired_blocks,
                'total': len(self.data)
            }


class WorkerStats:
    """워커 통계"""
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.lock = threading.Lock()

    def add_result(self, success: bool):
        with self.lock:
            self.total += 1
            if success:
                self.success += 1
            else:
                self.failed += 1

    def get_stats(self):
        with self.lock:
            return {
                "total": self.total,
                "success": self.success,
                "failed": self.failed
            }


def calculate_window_position(worker_id: int, window_width: int = None, window_height: int = None):
    """
    워커 ID에 따라 창 위치 반환 (WORKER_POSITIONS 딕셔너리에서 가져옴)

    Args:
        worker_id: 워커 ID (1부터 시작)
        window_width: 창 너비 (None이면 전역 상수 WINDOW_WIDTH 사용)
        window_height: 창 높이 (None이면 전역 상수 WINDOW_HEIGHT 사용)

    Returns:
        dict: {x, y, width, height}
    """
    # 창 크기 결정 (명령행 옵션 우선, 없으면 전역 상수)
    width = window_width if window_width is not None else WINDOW_WIDTH
    height = window_height if window_height is not None else WINDOW_HEIGHT

    # WORKER_POSITIONS 딕셔너리에서 위치 가져오기
    if worker_id in WORKER_POSITIONS:
        position = WORKER_POSITIONS[worker_id]
        x = position['x']
        y = position['y']
    else:
        # 정의되지 않은 워커 ID는 기본값 (0, 0)
        print(f"⚠️  Worker {worker_id}의 위치가 WORKER_POSITIONS에 정의되지 않았습니다. (0, 0) 사용")
        x = 0
        y = 0

    return {
        'x': x,
        'y': y,
        'width': width,
        'height': height
    }


def run_worker(worker_id: int, iterations: int, stats: WorkerStats, adjust_mode: str = None, vpn_list: list = None, window_config: dict = None, blocked_manager: BlockedCombinationsManager = None):
    """
    개별 워커 실행

    Args:
        worker_id: 워커 ID (1부터 시작)
        iterations: 반복 횟수 (None이면 무한 루프)
        stats: 통계 객체
        adjust_mode: Adjust 모드 ("adjust", "adjust2", None)
        vpn_list: VPN 번호 리스트 (None: VPN 사용 안 함, ['L', '0', '1'] 등)
        window_config: 창 설정 (width, height, x, y)
        blocked_manager: 차단 조합 관리자 (VPN + Chrome 버전 조합 차단 관리)
    """
    if iterations is None:
        print(f"[Worker-{worker_id}] 시작 - 무한 루프 (instance_id={worker_id})")
        is_infinite = True
    else:
        print(f"[Worker-{worker_id}] 시작 - {iterations}회 반복 (instance_id={worker_id})")
        is_infinite = False

    i = 0
    while True:
        i += 1

        # 무한 루프가 아니고 반복 횟수를 초과하면 종료
        if not is_infinite and i > iterations:
            break
        try:
            start_time = time.time()

            iteration_str = f"{i}" if is_infinite else f"{i}/{iterations}"

            # VPN 선택 전에 사용 가능한 VPN 필터링
            available_vpns = []
            # 실제로 설치된 Chrome 버전만 체크
            check_versions = scan_chrome_versions()
            if not check_versions:
                print(f"\n[Worker-{worker_id}] ❌ Chrome이 설치되어 있지 않습니다!")
                break

            if vpn_list and blocked_manager:
                # 각 VPN에 대해 모든 버전이 차단되었는지 확인
                for vpn in vpn_list:
                    # 'P'(프록시)는 매번 다른 프록시를 선택하므로 차단 체크 제외
                    if vpn == 'P':
                        available_vpns.append(vpn)
                        continue

                    blocked_count = 0
                    for ver in check_versions:
                        is_blocked, _ = blocked_manager.is_blocked(vpn, ver)
                        if is_blocked:
                            blocked_count += 1

                    # 모든 버전이 차단되지 않았으면 사용 가능
                    if blocked_count < len(check_versions):
                        available_vpns.append(vpn)
            elif vpn_list:
                # blocked_manager가 없으면 모든 VPN 사용 가능
                available_vpns = vpn_list.copy()

            # 사용 가능한 VPN이 없으면 1분 대기 후 재시도
            if vpn_list and len(available_vpns) == 0:
                print(f"\n[Worker-{worker_id}] 작업 {iteration_str}")
                print("=" * 60)
                print(f"   ⏸️  사용 가능한 VPN이 없음 (모든 VPN의 모든 Chrome 버전이 차단됨)")
                print(f"   ⏰ 1분 후 재시도...")
                time.sleep(60)
                # i를 증가시키지 않음 (재시도이므로 작업 횟수에 포함 안 함)
                if not is_infinite:
                    i -= 1  # 다음 루프에서 i += 1 되므로 상쇄
                continue

            # VPN 랜덤 선택 (사용 가능한 VPN 중에서)
            selected_vpn = None
            if available_vpns:
                selected_vpn = random.choice(available_vpns)

            # 선택된 VPN의 남아있는 Chrome 프로세스 정리
            cleanup_chrome_processes(vpn=selected_vpn, instance_id=worker_id)

            # 선택된 VPN에서 차단되지 않은 Chrome 버전 필터링
            selected_version = "random"  # 기본값
            blocked_versions = []

            if blocked_manager and selected_vpn is not None:
                available_versions = []
                for ver in check_versions:
                    is_blocked, remaining = blocked_manager.is_blocked(selected_vpn, ver)
                    if is_blocked:
                        blocked_versions.append((ver, remaining))
                    else:
                        available_versions.append(ver)

                # 차단되지 않은 버전 중 랜덤 선택
                if available_versions:
                    selected_version = random.choice(available_versions)
                else:
                    # 모든 버전이 차단됨 (이론적으로 발생하지 않아야 함)
                    selected_version = "random"

            # 작업 시작 메시지
            if selected_vpn == 'L':
                vpn_str = "Local"
            elif selected_vpn == 'P':
                vpn_str = "Proxy"
            elif selected_vpn:
                vpn_str = f"VPN: {selected_vpn}"
            else:
                vpn_str = ""

            chrome_str = f"Chrome {selected_version}"
            if selected_vpn:
                print(f"\n[Worker-{worker_id}] 작업 {iteration_str} 시작 ({vpn_str}, {chrome_str})")
            else:
                print(f"\n[Worker-{worker_id}] 작업 {iteration_str} 시작 ({chrome_str})")
            print("=" * 60)

            # 차단된 버전이 있으면 경고 출력
            if len(blocked_versions) > 0:
                if selected_vpn == 'L':
                    vpn_display = "Local"
                elif selected_vpn == 'P':
                    vpn_display = "Proxy"
                else:
                    vpn_display = f"VPN {selected_vpn}"
                print(f"   ⚠️  차단된 Chrome 버전 건너뜀 ({vpn_display})")
                for ver, remaining in blocked_versions:
                    print(f"      - Chrome {ver}: {remaining // 60}분 {remaining % 60}초 남음")
                print(f"   ✓ Chrome {selected_version} 선택")

            # agent.py 실행 명령어 구성 (차단되지 않은 버전으로 실행)
            cmd = [
                "python3", "agent.py",
                "--work-api",
                "--version", selected_version,
            ]

            # VPN 또는 프록시 옵션 추가
            if selected_vpn == 'P':
                # 프록시 사용 (API에서 자동 선택)
                cmd.append("--proxy")
            elif selected_vpn and selected_vpn != 'L':
                # VPN 사용
                cmd.extend(["--vpn", str(selected_vpn)])

            # Adjust 모드 옵션 추가 (선택 사항)
            if adjust_mode == "adjust":
                cmd.append("--adjust")
            elif adjust_mode == "adjust2":
                cmd.append("--adjust2")

            # 창 위치/크기 옵션 추가
            if window_config:
                cmd.extend([
                    "-W", str(window_config['width']),
                    "-H", str(window_config['height']),
                    "-X", str(window_config['x']),
                    "-Y", str(window_config['y'])
                ])

            # 나머지 옵션 추가
            cmd.extend([
                "--close",
                "--instance", str(worker_id)  # 워커 ID를 instance_id로 사용
            ])

            # agent.py 실행 (출력 캡처, timeout 600초 = 10분)
            try:
                result = subprocess.run(
                    cmd,
                    cwd=SCRIPT_DIR,
                    capture_output=True,  # 출력 캡처 (차단 감지용)
                    text=True,
                    timeout=600  # 10분 timeout
                )

                elapsed = time.time() - start_time
                success = (result.returncode == 0)

            except subprocess.TimeoutExpired as e:
                elapsed = time.time() - start_time
                success = False

                print(f"\n[Worker-{worker_id}] ⏰ Timeout 발생! (10분 초과)")
                print(f"   🔪 Chrome 프로세스 강제 정리 중...")

                # timeout 발생 시 Chrome 프로세스 강제 종료
                cleanup_chrome_processes(vpn=selected_vpn, instance_id=worker_id)

                # 결과 객체 생성 (stderr에 timeout 메시지 포함)
                result = type('obj', (object,), {
                    'returncode': -1,
                    'stdout': e.stdout if e.stdout else '',
                    'stderr': f"Timeout after 600 seconds\n{e.stderr if e.stderr else ''}"
                })()

                print(f"   ✓ Timeout 처리 완료")

                # 차단 목록에 추가 (timeout도 문제로 간주)
                if blocked_manager:
                    blocked_manager.add_blocked(selected_vpn, selected_version, "timeout")
                    print(f"   ⚠️  차단 목록 추가: {selected_vpn or 'Local'} + Chrome {selected_version} (10분)")

                # 다음 반복으로 진행 (작업 실패 처리)
                stats.add_failure()
                if screenshot_id:
                    log_result(worker_id, screenshot_id, selected_vpn, chrome_version, False, elapsed, api_client)
                continue

            # 출력 표시
            if result.stdout:
                print(result.stdout, end='')
            if result.stderr:
                print(result.stderr, end='')

            # 작업 할당 실패 감지 (1분 대기 후 재시도)
            full_output = result.stdout + result.stderr
            if '작업 할당 실패' in full_output or '할당 가능한 작업이 없습니다' in full_output:
                print(f"\n[Worker-{worker_id}] ⏸️  작업 할당 실패 - 1분 후 재시도...")
                time.sleep(60)
                # i를 증가시키지 않음 (재시도이므로 작업 횟수에 포함 안 함)
                if not is_infinite:
                    i -= 1  # 다음 루프에서 i += 1 되므로 상쇄
                continue

            # 출력에서 Chrome 버전 및 작업 ID 파싱
            chrome_version = None
            screenshot_id = None
            for line in result.stdout.split('\n'):
                if 'Chrome Version:' in line:
                    # "Chrome Version: 144" -> "144" 추출
                    parts = line.split(':')
                    if len(parts) >= 2:
                        chrome_version = parts[1].strip()

                # 작업 ID 파싱: "- ID: 4948534"
                if '- ID:' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        try:
                            screenshot_id = int(parts[1].strip())
                        except:
                            pass

            # 차단 감지 및 처리
            if blocked_manager and selected_vpn is not None and chrome_version:
                # 차단 키워드 검색 (full_output은 이미 Line 396에서 선언됨)
                is_blocked_error = any(keyword in full_output for keyword in [
                    '차단',
                    'http2_protocol_error',
                    'ERR_HTTP2_PROTOCOL_ERROR',
                    'blocked',
                    'rate limit'
                ])

                if is_blocked_error:
                    # 차단 발생: 차단 목록에 추가
                    blocked_manager.mark_blocked(selected_vpn, chrome_version, reason="http2/rate limit error")
                elif success:
                    # 성공: 차단 목록에서 제거 (이전에 차단되었다면)
                    blocked_manager.mark_success(selected_vpn, chrome_version)

            # 통계 업데이트
            stats.add_result(success)

            # 로그 기록 (일자별 TXT 파일)
            error_msg = None
            if not success:
                # 실패 시 에러 메시지 추출
                if 'http2_protocol_error' in full_output or 'ERR_HTTP2_PROTOCOL_ERROR' in full_output:
                    error_msg = "http2_protocol_error"
                elif '차단' in full_output or 'blocked' in full_output:
                    error_msg = "blocked/rate limit"
                elif '작업 할당 실패' in full_output:
                    error_msg = "no work assigned"
                else:
                    error_msg = f"exit code {result.returncode}"

            log_result(
                worker_id=worker_id,
                vpn=selected_vpn,
                chrome_version=chrome_version if chrome_version else "unknown",
                success=success,
                error_msg=error_msg,
                screenshot_id=screenshot_id
            )

            if success:
                print(f"\n[Worker-{worker_id}] ✅ 작업 {iteration_str} 완료 ({elapsed:.1f}초)")
            else:
                print(f"\n[Worker-{worker_id}] ❌ 작업 {iteration_str} 실패 ({elapsed:.1f}초)")

        except Exception as e:
            print(f"\n[Worker-{worker_id}] ❌ 오류 발생: {e}")
            stats.add_result(False)

            # 예외 발생 시에도 로그 기록
            log_result(
                worker_id=worker_id,
                vpn=selected_vpn if 'selected_vpn' in locals() else None,
                chrome_version="unknown",
                success=False,
                error_msg=f"Exception: {str(e)}"
            )

    print(f"\n[Worker-{worker_id}] 모든 작업 완료")


def main():
    parser = argparse.ArgumentParser(
        description="멀티 워커로 agent.py 반복 실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 무한 루프로 실행 (기본: 1 스레드)
  python3 run_workers.py

  # 3개 스레드로 무한 루프 실행 (창 자동 배치)
  python3 run_workers.py -t 3

  # 3개 스레드로 각각 10회 실행
  python3 run_workers.py -t 3 -i 10

  # 창 크기 지정 (기본: 1300x1200)
  python3 run_workers.py -t 3 -W 1000 -H 900

  # VPN 랜덤 선택 (0-5번 중 랜덤, 무한 루프)
  python3 run_workers.py -t 3 --vpn=0,1,2,3,4,5

  # 로컬 + VPN 0-5번 중 랜덤 선택 (L은 로컬/VPN 없음)
  python3 run_workers.py -t 3 --vpn=L,0,1,2,3,4,5

  # 프록시만 사용
  python3 run_workers.py -t 3 --proxy

  # 로컬 + VPN + 프록시 중 랜덤 선택
  python3 run_workers.py -t 3 --vpn=L,0,1,2 --proxy

창 배치 레이아웃 (최대 6개 스레드):
  1  2  3
  4  5  6

네트워크 모드:
  - Local (L): 직접 연결
  - VPN (0-9): VPN 서버 경유
  - Proxy (P): SOCKS5 프록시 경유 (API에서 자동 선택)

차단 조합 관리:
  - http2 차단 발생 시 VPN+Chrome 버전 조합을 자동으로 차단 목록에 추가
  - 차단된 조합은 10분간 재시도하지 않음
  - 10분 후 재시도해서 성공하면 차단 목록에서 자동 제거
  - 차단 목록: blocked_combinations.json
        """
    )

    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=1,
        help="동시 실행 스레드 개수 (기본: 1)"
    )

    parser.add_argument(
        "-i", "--iterations",
        type=int,
        default=None,
        help="각 스레드당 반복 횟수 (기본: 무한 루프)"
    )

    parser.add_argument(
        "--adjust",
        action="store_true",
        help="Adjust 모드 활성화 (미래 개발용)"
    )

    parser.add_argument(
        "--adjust2",
        action="store_true",
        help="Adjust2 모드 활성화 (미래 개발용)"
    )

    parser.add_argument(
        "--vpn",
        type=str,
        default=None,
        help="VPN 번호 리스트 (콤마로 구분, 예: L,0,1,2 - L은 로컬/VPN 없음)"
    )

    parser.add_argument(
        "--proxy",
        action="store_true",
        help="프록시 사용 (--vpn과 함께 사용 시 VPN 또는 프록시 중 랜덤 선택)"
    )

    parser.add_argument(
        "-W", "--window-width",
        type=int,
        default=1300,
        help="창 너비 (기본: 1300px)"
    )

    parser.add_argument(
        "-H", "--window-height",
        type=int,
        default=1200,
        help="창 높이 (기본: 1200px)"
    )

    args = parser.parse_args()

    # 입력 검증
    if args.threads < 1:
        print("❌ 스레드 개수는 1 이상이어야 합니다")
        return

    if args.threads > MAX_WORKERS:
        print(f"❌ 스레드 개수는 최대 {MAX_WORKERS}개까지 지원됩니다")
        print(f"   현재 요청: {args.threads}개")
        print(f"   최적 레이아웃: 가로 3개 x 세로 2개 = 최대 {MAX_WORKERS}개")
        print(f"   설정 변경: run_workers.py 상단의 MAX_WORKERS 상수 수정")
        return

    if args.iterations is not None and args.iterations < 1:
        print("❌ 반복 횟수는 1 이상이어야 합니다")
        return

    # Adjust 모드 결정
    adjust_mode = None
    if args.adjust and args.adjust2:
        print("❌ --adjust와 --adjust2는 동시에 사용할 수 없습니다")
        return
    elif args.adjust:
        adjust_mode = "adjust"
    elif args.adjust2:
        adjust_mode = "adjust2"

    # VPN 리스트 파싱
    vpn_list = None
    if args.vpn:
        vpn_list = [vpn.strip().upper() for vpn in args.vpn.split(",")]
        # 유효성 검사
        for vpn in vpn_list:
            if vpn != 'L' and not vpn.isdigit():
                print(f"❌ 잘못된 VPN 값: {vpn} (L 또는 숫자만 가능)")
                return

    # 프록시 플래그가 있으면 VPN 리스트에 'P' 추가
    if args.proxy:
        if vpn_list is None:
            vpn_list = ['P']  # 프록시만 사용
        else:
            vpn_list.append('P')  # VPN과 프록시 병행

    # 좀비 회수 스레드 시작 (daemon으로 백그라운드 실행)
    reaper_thread = threading.Thread(target=zombie_reaper_thread, daemon=True)
    reaper_thread.start()
    print("⚰️  좀비 프로세스 회수 스레드 시작")

    # 시작 정보 출력
    print("\n" + "=" * 60)
    print("🚀 멀티 워커 실행")
    print("=" * 60)
    print(f"스레드 개수: {args.threads}")
    if args.iterations is None:
        print(f"반복 횟수: 무한 루프 (Ctrl+C로 종료)")
        print(f"총 작업 수: 무한")
    else:
        print(f"반복 횟수: {args.iterations} (스레드당)")
        print(f"총 작업 수: {args.threads * args.iterations}")
    if vpn_list:
        # 'L'을 "Local", 'P'를 "Proxy"로 변환하여 표시
        display_list = []
        for v in vpn_list:
            if v == 'L':
                display_list.append("Local")
            elif v == 'P':
                display_list.append("Proxy")
            else:
                display_list.append(f"VPN-{v}")
        print(f"네트워크 모드: {', '.join(display_list)} (랜덤 선택)")
    if adjust_mode:
        print(f"Adjust 모드: {adjust_mode}")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # Chrome 프로세스 정리 (워커 시작 시 한 번만 실행)
    print("🧹 Chrome 프로세스 정리 시작...")
    cleanup_all_chrome_processes()
    print()

    # 통계 객체
    stats = WorkerStats()

    # 차단 조합 관리자 생성
    blocked_manager = BlockedCombinationsManager()
    print(f"📋 차단 목록 관리 활성화 (쿨다운: {blocked_manager.cooldown_minutes}분)")

    # 기존 차단 목록 통계
    block_stats = blocked_manager.get_stats()
    if block_stats['active']:
        print(f"   현재 차단 중인 조합: {len(block_stats['active'])}개")
        for key, remaining in block_stats['active'][:5]:  # 최대 5개만 표시
            print(f"      - {key}: {remaining // 60}분 {remaining % 60}초 남음")
    print()

    # 스레드 생성 및 시작
    threads = []
    start_time = time.time()

    for worker_id in range(1, args.threads + 1):
        # 워커별 창 위치 계산 (명령행 옵션 우선, 없으면 전역 상수)
        window_config = calculate_window_position(
            worker_id,
            window_width=args.window_width,
            window_height=args.window_height
        )

        thread = threading.Thread(
            target=run_worker,
            args=(worker_id, args.iterations, stats, adjust_mode, vpn_list, window_config, blocked_manager),
            name=f"Worker-{worker_id}"
        )
        threads.append(thread)
        thread.start()

        # 스레드 시작 간 간격 (브라우저/ChromeDriver 초기화 겹침 방지)
        time.sleep(3)

    # 모든 스레드 종료 대기
    for thread in threads:
        thread.join()

    # 최종 통계 출력
    elapsed = time.time() - start_time
    final_stats = stats.get_stats()

    print("\n" + "=" * 60)
    print("📊 최종 결과")
    print("=" * 60)
    print(f"총 작업 수: {final_stats['total']}")
    print(f"성공: {final_stats['success']}")
    print(f"실패: {final_stats['failed']}")
    if final_stats['total'] > 0:
        print(f"성공률: {final_stats['success'] / final_stats['total'] * 100:.1f}%")
    else:
        print(f"성공률: N/A")
    print(f"총 소요 시간: {elapsed / 60:.1f}분 ({elapsed:.1f}초)")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 차단 목록 통계
    block_stats = blocked_manager.get_stats()
    if block_stats['total'] > 0:
        print("\n🚫 차단 목록 요약:")
        print(f"   현재 차단 중: {len(block_stats['active'])}개")
        if block_stats['active']:
            for key, remaining in block_stats['active'][:5]:
                print(f"      - {key}: {remaining // 60}분 {remaining % 60}초 남음")
        if block_stats['expired']:
            print(f"   쿨다운 만료: {len(block_stats['expired'])}개 (재시도 가능)")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
