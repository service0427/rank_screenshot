#!/usr/bin/env python3
"""
멀티 워커 실행 스크립트
여러 스레드로 uc_agent.py를 반복 실행
"""

import subprocess
import threading
import time
import argparse
import random
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

# VPN API 클라이언트 (VPN 키 풀 동적 할당/반납)
# common/ 폴더에서 import (공통 모듈)
from common.vpn_api_client import VPNAPIClient, VPNConnection

# 작업 할당 API 클라이언트 (작업 할당/결과 제출)
from uc_lib.modules.work_api_client import WorkAPIClient


# ============================================================
# 스크립트 디렉토리 및 로그 디렉토리 설정
# ============================================================
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = SCRIPT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


# ============================================================
# VPN 동시 할당 관리
# ============================================================
class VPNAllocationManager:
    """
    VPN 동시 할당 관리 클래스
    - 하나의 VPN은 동시에 1개 워커만 사용 가능
    - Local('L')도 동시에 1개 워커만 사용 가능
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.allocated_vpns = set()  # 현재 사용 중인 VPN 목록

    def allocate(self, vpn: str) -> bool:
        """
        VPN 할당 시도

        Args:
            vpn: VPN 번호 ('L', '0', '1', ...)

        Returns:
            할당 성공 여부
        """
        with self.lock:
            if vpn in self.allocated_vpns:
                return False  # 이미 사용 중
            self.allocated_vpns.add(vpn)
            return True

    def release(self, vpn: str):
        """
        VPN 할당 해제

        Args:
            vpn: VPN 번호 ('L', '0', '1', ...)
        """
        with self.lock:
            self.allocated_vpns.discard(vpn)

    def get_allocated_count(self) -> int:
        """현재 할당된 VPN 개수"""
        with self.lock:
            return len(self.allocated_vpns)

    def get_available_vpns(self, all_vpns: list) -> list:
        """
        사용 가능한 VPN 목록 반환

        Args:
            all_vpns: 전체 VPN 목록

        Returns:
            사용 가능한 (아직 할당되지 않은) VPN 목록
        """
        with self.lock:
            return [vpn for vpn in all_vpns if vpn not in self.allocated_vpns]


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

        # VPN 표시
        if vpn == 'L' or vpn is None:
            vpn_str = "Local"
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


def cleanup_vpn_interface(worker_id: int) -> bool:
    """
    워커 ID에 해당하는 VPN 인터페이스 정리 (강제 종료로 남은 인터페이스 제거)

    Args:
        worker_id: 워커 ID (1~12)
            Worker-1 → wg101, Worker-2 → wg102, ...

    Returns:
        정리 성공 여부
    """
    # wg101-112 네이밍: Worker-1 → wg101, Worker-2 → wg102, ...
    user_id = 100 + worker_id
    interface_name = f"wg{user_id}"

    try:
        # 1. 인터페이스 존재 확인
        result = subprocess.run(
            ['ip', 'link', 'show', interface_name],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode != 0:
            # 인터페이스 없음 (정상)
            return True

        # 2. 인터페이스가 이미 존재 - 설정 파일만 확인
        config_path = Path(f"/tmp/vpn_configs/{interface_name}.conf")

        # 설정 파일이 없으면 이전 연결이 정상 종료되지 않은 것
        # 하지만 인터페이스가 UP 상태면 재사용 가능 (강제 삭제 시도하지 않음)
        if not config_path.exists():
            # 인터페이스가 UP 상태인지 확인
            if 'state UP' in result.stdout or 'state UNKNOWN' in result.stdout:
                # UP 상태: 이전 연결이 살아있음 - 재사용 가능
                # 삭제 시도하지 않고 그대로 둠 (VPNConnection이 재사용함)
                return True
            else:
                # DOWN 상태: 정리 필요
                print(f"   🧹 DOWN 상태 인터페이스 발견: {interface_name}")
                # ip link set down 후 삭제
                subprocess.run(
                    ['sudo', 'ip', 'link', 'set', interface_name, 'down'],
                    capture_output=True,
                    timeout=2
                )
                time.sleep(0.5)
                subprocess.run(
                    ['sudo', 'ip', 'link', 'del', interface_name],
                    capture_output=True,
                    timeout=2
                )
                return True
        else:
            # 설정 파일이 있으면 wg-quick down 시도
            result = subprocess.run(
                ['sudo', 'wg-quick', 'down', str(config_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"   ✅ wg-quick down 성공: {interface_name}")
            # 설정 파일 삭제 (성공 여부 무관)
            try:
                config_path.unlink()
            except Exception:
                pass
            return True

    except subprocess.TimeoutExpired:
        # 타임아웃 발생 시 재사용으로 간주 (강제 종료하지 않음)
        return True
    except Exception as e:
        # 기타 오류 발생 시에도 계속 진행 (인터페이스는 재사용됨)
        return True


# ============================================================
# 창 위치 및 크기 설정 (워커별 수동 지정)
# ============================================================
WINDOW_WIDTH = 1300       # Chrome 창 너비
WINDOW_HEIGHT = 1200      # Chrome 창 높이

# 워커별 창 위치 (4x3 그리드, 4K 해상도 최적화)
# 4K: 3840x2160, 창 크기: 1300x1200
# 가로 간격: 850px (450px 겹침), 세로 간격: 640px (560px 겹침)
WORKER_POSITIONS = {
    1:  {'x': 0,    'y': 0},
    2:  {'x': 850,  'y': 0},
    3:  {'x': 1700, 'y': 0},
    4:  {'x': 2540, 'y': 0},
    5:  {'x': 0,    'y': 640},
    6:  {'x': 850,  'y': 640},
    7:  {'x': 1700, 'y': 640},
    8:  {'x': 2540, 'y': 640},
    9:  {'x': 0,    'y': 1280},
    10: {'x': 850,  'y': 1280},
    11: {'x': 1700, 'y': 1280},
    12: {'x': 2540, 'y': 1280},
}

MAX_WORKERS = 20          # 최대 워커 수 (이론적 최대치, 권장: 12-16개)
                          # 실제 운영 시 시스템 리소스 고려 필요
                          # - 12개: 시스템 사용자 제약 (vpn-worker-1 ~ vpn-worker-12)
                          # - 16개: 안정적 운영 권장
                          # - 20개: 하드웨어 여유 있을 때만
                          # VPN 키 풀: 50개 용량 (5 서버 × 10 동시 접속)


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


def run_worker(worker_id: int, iterations: int, stats: WorkerStats, adjust_mode: str = None, vpn_list: list = None, window_config: dict = None, blocked_manager: BlockedCombinationsManager = None, vpn_allocation_manager: VPNAllocationManager = None, enable_fingerprint_spoof: bool = False, fingerprint_preset: str = 'full'):
    """
    개별 워커 실행 (VPN 키 풀 지원)

    Args:
        worker_id: 워커 ID (1부터 시작)
        iterations: 반복 횟수 (None이면 무한 루프)
        stats: 통계 객체
        adjust_mode: Adjust 모드 ("adjust", "adjust2", None)
        vpn_list: VPN 리스트 (None: 사용 안 함, ['L']: Local만, True: VPN 키 풀 사용)
        window_config: 창 설정 (width, height, x, y)
        blocked_manager: 차단 조합 관리자 (VPN + Chrome 버전 조합 차단 관리)
        vpn_allocation_manager: DEPRECATED - VPN 키 풀 API가 자동 관리
        enable_fingerprint_spoof: 핑거프린트 스푸핑 활성화 여부
        fingerprint_preset: 스푸핑 프리셋 (minimal, light, medium, full)

    VPN 키 풀 사용법:
        - vpn_list=None: VPN 사용 안 함 (Local)
        - vpn_list=['L']: Local 명시적 사용
        - vpn_list=True: VPN 키 풀 사용 (동적 할당/반납)
    """
    if iterations is None:
        print(f"[Worker-{worker_id}] 시작 - 무한 루프 (instance_id={worker_id})")
        is_infinite = True
    else:
        print(f"[Worker-{worker_id}] 시작 - {iterations}회 반복 (instance_id={worker_id})")
        is_infinite = False

    i = 0
    vpn_client = VPNAPIClient() if vpn_list and vpn_list != ['L'] else None
    vpn_conn = None  # VPN 연결 객체 (작업마다 새로 생성)

    while True:
        i += 1

        # 무한 루프가 아니고 반복 횟수를 초과하면 종료
        if not is_infinite and i > iterations:
            break
        try:
            start_time = time.time()

            iteration_str = f"{i}" if is_infinite else f"{i}/{iterations}"

            # 실제로 설치된 Chrome 버전만 체크
            check_versions = scan_chrome_versions()
            if not check_versions:
                print(f"\n[Worker-{worker_id}] ❌ Chrome이 설치되어 있지 않습니다!")
                break

            # VPN 모드 결정: Local / VPN 키 풀
            use_vpn = False
            selected_vpn = None  # 'L' (Local) 또는 'VPN' (키 풀)

            if vpn_list == ['L']:
                # Local 명시적 사용
                selected_vpn = 'L'
                use_vpn = False
            elif vpn_list and vpn_list != ['L']:
                # VPN 키 풀 사용
                selected_vpn = 'VPN'
                use_vpn = True
            else:
                # vpn_list가 None이면 Local
                selected_vpn = None
                use_vpn = False

            # 선택된 모드의 남아있는 Chrome 프로세스 정리
            cleanup_chrome_processes(vpn=selected_vpn, instance_id=worker_id)

            # 작업 할당 먼저 받기 (VPN 연결 전)
            # - 작업이 있을 때만 VPN 연결하여 리소스 절약
            work_data = None
            work_api_client = WorkAPIClient()

            print(f"\n[Worker-{worker_id}] 작업 {iteration_str}")
            print("=" * 60)

            # 작업 할당 요청
            work_data = work_api_client.allocate_work()

            if not work_data or not work_data.get("success"):
                print(f"\n[Worker-{worker_id}] ⏸️  할당 가능한 작업 없음 - 1분 후 재시도...")
                time.sleep(60)
                if not is_infinite:
                    i -= 1  # 반복 횟수에서 제외
                continue  # VPN 연결 건너뛰고 다음 반복

            # 작업 정보 추출
            screenshot_id = work_data.get("id")
            keyword = work_data.get("keyword")
            product_id = work_data.get("product_id")
            item_id = work_data.get("item_id")
            vendor_item_id = work_data.get("vendor_item_id")
            min_rank = work_data.get("min_rank")

            print(f"\n✅ 작업 할당 완료:")
            print(f"   📝 작업 ID: {screenshot_id}")
            print(f"   🔍 키워드: {keyword}")
            print(f"   📦 상품 ID: {product_id}")
            if min_rank:
                print(f"   📊 최소 순위: {min_rank}")
            print()

            # VPN 키 풀 연결 (use_vpn=True이고 작업이 있을 경우)
            if use_vpn and vpn_client:
                # 이전 작업의 강제 종료로 남은 VPN 인터페이스 정리
                cleanup_vpn_interface(worker_id)

                # 로그 파일을 wg 사용자로 미리 초기화 (VPN 연결 전)
                # /tmp는 sticky bit가 설정되어 있어서 다른 사용자가 만든 파일에 쓸 수 없음
                # wg 사용자가 직접 로그 파일을 생성하도록 함
                user_id = 100 + worker_id  # Worker-1 → 101
                wg_user = f"wg{user_id}"
                log_file = f"/tmp/vpn_events_{wg_user}.log"

                # 파일이 없거나, tech 소유라면 wg 사용자로 재생성
                needs_init = False
                if not os.path.exists(log_file):
                    needs_init = True
                else:
                    # 파일 소유자 확인
                    import stat
                    file_stat = os.stat(log_file)
                    import pwd
                    wg_uid = pwd.getpwnam(wg_user).pw_uid
                    if file_stat.st_uid != wg_uid:
                        # tech 또는 다른 사용자 소유 → 삭제 후 재생성
                        os.remove(log_file)
                        needs_init = True

                if needs_init:
                    try:
                        # wg 사용자로 새 파일 생성 (umask 0으로 666 권한 보장)
                        result = subprocess.run(
                            ['sudo', '-u', wg_user, 'sh', '-c', f'umask 0 && touch {log_file}'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            print(f"   ✓ 로그 파일 초기화: {log_file} (소유자: {wg_user}, 권한: 666)")
                    except Exception as e:
                        print(f"   ⚠️ 로그 파일 초기화 실패: {e}")

                vpn_conn = VPNConnection(worker_id=worker_id, vpn_client=vpn_client)
                if not vpn_conn.connect():
                    print(f"   ❌ VPN 연결 실패 - 1분 후 재시도...")
                    time.sleep(60)
                    if not is_infinite:
                        i -= 1
                    continue
                # VPN 연결 성공 후 selected_vpn을 VPN 내부 IP로 업데이트 (로깅용)
                vpn_internal_ip = vpn_conn.get_internal_ip()

                # X11 권한 부여 (wgN 사용자가 GUI 실행 가능하도록)
                try:
                    display = os.environ.get('DISPLAY', ':0')
                    result = subprocess.run(
                        ['xhost', f'+SI:localuser:{wg_user}'],
                        env={'DISPLAY': display},
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        print(f"   ✓ X11 권한 부여: {wg_user}")
                except Exception:
                    pass  # 실패해도 계속 진행
            else:
                vpn_internal_ip = None

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
            elif selected_vpn == 'VPN':
                vpn_str = f"VPN 키 풀 ({vpn_internal_ip})" if vpn_internal_ip else "VPN 키 풀"
            else:
                vpn_str = ""

            chrome_str = f"Chrome {selected_version}"
            if not use_vpn:  # VPN 연결이 없을 때만 출력 (VPN은 이미 연결 메시지 출력됨)
                print(f"\n[Worker-{worker_id}] 작업 {iteration_str} 시작")
                print("=" * 60)

            if vpn_str:
                print(f"   🌐 네트워크: {vpn_str}")
            print(f"   🌐 브라우저: {chrome_str}")

            # 차단된 버전이 있으면 경고 출력
            if len(blocked_versions) > 0:
                if selected_vpn == 'L':
                    vpn_display = "Local"
                elif selected_vpn == 'VPN':
                    vpn_display = "VPN 키 풀"
                else:
                    vpn_display = f"VPN {selected_vpn}"
                print(f"   ⚠️  차단된 Chrome 버전 건너뜀 ({vpn_display})")
                for ver, remaining in blocked_versions:
                    print(f"      - Chrome {ver}: {remaining // 60}분 {remaining % 60}초 남음")
                print(f"   ✓ Chrome {selected_version} 선택")

            # uc_agent.py 실행 명령어 구성 (차단되지 않은 버전으로 실행)
            # ⚠️ WireGuard 키 풀 사용 시:
            #    1. sudo -u wgN으로 직접 실행 (프로세스 격리)
            #       Worker-1 → wg101 (UID 101), Worker-2 → wg102 (UID 102), ...
            #    2. uc_agent.py에서 os.execvpe() 재실행하지 않음 (멀티스레드 충돌 방지)
            #    3. X11, HOME, XDG 환경 변수 전달
            current_user_home = os.path.expanduser('~')
            display = os.environ.get('DISPLAY', ':0')

            if use_vpn and vpn_conn:
                # WireGuard 키 풀: sudo -u wgN env ... python3 /absolute/path/uc_agent.py ...
                # Worker-1 → wg101, Worker-2 → wg102, ... (UID/Table과 숫자 통일)
                user_id = 100 + worker_id
                wg_user = f"wg{user_id}"
                wg_home = f"/home/{wg_user}"
                vpn_interface = vpn_conn.interface_name if vpn_conn.interface_name else f"wg{user_id}"
                agent_path = str(SCRIPT_DIR / "uc_agent.py")  # 절대 경로 사용 (Permission denied 방지)
                cmd = [
                    "sudo", "-u", wg_user,
                    "env",
                    f"HOME={wg_home}",
                    f"DISPLAY={display}",
                    f"XDG_CACHE_HOME={current_user_home}/.cache",
                    f"XDG_DATA_HOME={current_user_home}/.local/share",
                    f"VPN_INTERFACE={vpn_interface}",  # VPN 인터페이스 정보 전달
                    "python3", agent_path,  # 절대 경로 사용
                    "--work-api",
                    "--screenshot-id", str(screenshot_id),
                    "--keyword", keyword,
                    "--version", selected_version,
                    "--vpn-pool-worker", str(worker_id),
                ]
            else:
                # Local: python3 /absolute/path/uc_agent.py ...
                agent_path = str(SCRIPT_DIR / "uc_agent.py")  # 절대 경로 사용 (일관성 유지)
                cmd = [
                    "python3", agent_path,  # 절대 경로 사용
                    "--work-api",
                    "--screenshot-id", str(screenshot_id),
                    "--keyword", keyword,
                    "--version", selected_version,
                ]

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
                "--instance", str(worker_id),  # 워커 ID를 instance_id로 사용
                "--ip-check"  # VPN 연결 확인을 위해 자동으로 IP 체크
            ])

            # 핑거프린트 스푸핑 옵션 추가
            if enable_fingerprint_spoof:
                cmd.append("--enable-fingerprint-spoof")
                cmd.append("--fingerprint-preset")
                cmd.append(fingerprint_preset)

            # uc_agent.py 실행 (출력 캡처, timeout 600초 = 10분)
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
                    blocked_manager.mark_blocked(selected_vpn, selected_version, reason="timeout")
                    print(f"   ⚠️  차단 목록 추가: {selected_vpn or 'Local'} + Chrome {selected_version} (10분)")

                # 다음 반복으로 진행 (작업 실패 처리)
                stats.add_result(False)  # Timeout도 실패로 기록
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

        finally:
            # VPN 연결 해제 및 키 반납 (모든 경우에 실행)
            if vpn_conn:
                try:
                    vpn_conn.disconnect()
                except Exception as e:
                    print(f"   ⚠️  VPN 연결 해제 중 오류: {e}")
                finally:
                    vpn_conn = None  # 다음 작업을 위해 초기화

            # DEPRECATED: VPN 할당 관리자 (하위 호환성 유지)
            if vpn_allocation_manager and 'selected_vpn' in locals() and selected_vpn:
                vpn_allocation_manager.release(selected_vpn)

    print(f"\n[Worker-{worker_id}] 모든 작업 완료")


def main():
    parser = argparse.ArgumentParser(
        description="멀티 워커로 uc_agent.py 반복 실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 6개 스레드로 무한 루프 실행 (VPN API 자동 조회)
  python3 run_workers.py

  # 12개 스레드로 무한 루프 실행
  python3 run_workers.py -t 12

  # 6개 스레드로 각각 100회 실행
  python3 run_workers.py -t 6 -i 100

  # 로컬 모드 (VPN 사용 안 함)
  python3 run_workers.py -t 1 -i 1 --local

  # 창 크기 지정 (기본: 1300x1200)
  python3 run_workers.py -t 6 -W 1000 -H 900

  # 핑거프린트 스푸핑 활성화 (TLS 차단 우회)
  python3 run_workers.py -t 6 --enable-fingerprint-spoof

창 배치 레이아웃 (최대 12개 스레드):
  1   2   3   4
  5   6   7   8
  9  10  11  12

네트워크 모드:
  - VPN 목록은 API에서 자동 조회 (http://220.121.120.83/vpn_socks5/api/list.php)
  - Local + VPN 0~N (API에서 가져온 IP 개수만큼)
  - 각 VPN은 동시에 1개 워커만 사용 (동시 할당 제한)

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
        default=6,
        help="동시 실행 스레드 개수 (기본: 6, 최대: 12)"
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

    parser.add_argument(
        "--enable-fingerprint-spoof",
        action="store_true",
        default=False,
        help="브라우저 핑거프린트 스푸핑 활성화 (Canvas, WebGL, Hardware 등 랜덤 변조)"
    )

    parser.add_argument(
        "--fingerprint-preset",
        type=str,
        choices=['minimal', 'light', 'medium', 'full'],
        default='full',
        help="스푸핑 프리셋 (minimal=GPU+Canvas+Audio, light=+Hardware, medium=+Screen, full=+Touch 권장)"
    )

    parser.add_argument(
        "--local",
        action="store_true",
        default=False,
        help="로컬 모드 (VPN 사용 안 함)"
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

    # VPN 모드 결정 (VPN 키 풀 또는 Local)
    if args.local:
        # --local 옵션: 강제 로컬 모드
        print("🏠 로컬 모드 (VPN 사용 안 함)")
        vpn_list = ['L']
    else:
        # VPN 키 풀 API 확인
        print("🔍 VPN 키 풀 API 확인 중...")
        try:
            vpn_client = VPNAPIClient()
            servers = vpn_client.get_server_list()
            if servers and len(servers) > 0:
                # VPN 키 풀 사용 (True로 설정하면 워커가 동적 할당 사용)
                vpn_list = True
                print(f"   ✓ VPN 키 풀 사용 가능 (서버 {len(servers)}개)")
                print(f"   ✓ VPN 키 동적 할당 모드 활성화")
            else:
                print(f"   ⚠️  VPN 서버 없음 - Local 모드 사용")
                vpn_list = ['L']
        except Exception as e:
            print(f"   ⚠️  VPN API 조회 실패: {e}")
            print(f"   ⚠️  Local 모드만 사용합니다")
            vpn_list = ['L']

    # VPN 동시 할당 관리자 생성
    vpn_allocation_manager = VPNAllocationManager()

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
    # 네트워크 모드 표시
    if vpn_list == True:
        print(f"네트워크 모드: VPN 키 풀 (동적 할당)")
    elif vpn_list == ['L']:
        print(f"네트워크 모드: Local (VPN 없음)")
    else:
        print(f"네트워크 모드: {vpn_list}")
    if adjust_mode:
        print(f"Adjust 모드: {adjust_mode}")
    print(f"핑거프린트 스푸핑: {'✅ 활성화' if args.enable_fingerprint_spoof else '❌ 비활성화'}")
    if args.enable_fingerprint_spoof:
        print(f"스푸핑 프리셋: {args.fingerprint_preset}")
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
            args=(worker_id, args.iterations, stats, adjust_mode, vpn_list, window_config, blocked_manager, vpn_allocation_manager, args.enable_fingerprint_spoof, args.fingerprint_preset),
            name=f"Worker-{worker_id}"
        )
        threads.append(thread)
        thread.start()

        # 스레드 시작 간 간격 (ERR_NETWORK_CHANGED 방지)
        # 2025-11-07: 3초 고정 → 0.3~0.7초 랜덤 지연
        # netlink 이벤트 폭주를 계단형으로 분산하여 Chrome 네트워크 변경 감지 방지
        time.sleep(random.uniform(0.3, 0.7))

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
