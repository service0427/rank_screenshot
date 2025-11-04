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
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 창 위치 및 크기 설정 (미세조정용)
# ============================================================
WINDOW_WIDTH = 1300       # Chrome 창 너비
WINDOW_HEIGHT = 1200      # Chrome 창 높이
GRID_OFFSET_X = 1300      # 창 사이 가로 간격 (창 너비와 동일 = 간격 없이 붙음)
GRID_OFFSET_Y = 1200      # 창 사이 세로 간격
MAX_WORKERS = 6           # 최대 워커 수 (가로 3 x 세로 2)


class BlockedCombinationsManager:
    """
    VPN + Chrome 버전 조합의 차단 상태 관리

    차단된 조합은 JSON 파일에 저장하고, 3분간 재시도하지 않음.
    3분 후 재시도해서 성공하면 차단 목록에서 제거.
    """

    def __init__(self, json_path: str = None):
        if json_path is None:
            json_path = Path(__file__).parent / "blocked_combinations.json"
        self.json_path = Path(json_path)
        self.lock = threading.Lock()
        self.cooldown_minutes = 3
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
        차단 여부 확인 (3분 쿨다운 체크)

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
    워커 ID에 따라 창 위치 계산

    레이아웃:
    1(0,0)       2(X,0)     3(2X,0)
    4(0,Y)       5(X,Y)     6(2X,Y)

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

    # 행/열 계산 (0-based)
    row = (worker_id - 1) // 3  # 0 또는 1
    col = (worker_id - 1) % 3   # 0, 1, 2

    # 위치 계산 (GRID_OFFSET 전역 상수 사용)
    x = col * GRID_OFFSET_X
    y = row * GRID_OFFSET_Y

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

            # VPN 랜덤 선택
            selected_vpn = None
            iteration_str = f"{i}" if is_infinite else f"{i}/{iterations}"

            if vpn_list:
                selected_vpn = random.choice(vpn_list)
                if selected_vpn == 'L':
                    print(f"\n[Worker-{worker_id}] 작업 {iteration_str} 시작 (VPN: Local)")
                else:
                    print(f"\n[Worker-{worker_id}] 작업 {iteration_str} 시작 (VPN: {selected_vpn})")
            else:
                print(f"\n[Worker-{worker_id}] 작업 {iteration_str} 시작")
            print("=" * 60)

            # 차단 조합 확인 (Chrome version은 random이므로 모든 가능한 버전 체크)
            # 참고: agent.py가 실제로 선택한 버전은 실행 후에만 알 수 있음
            # 여기서는 대표적인 버전들만 체크하고, 실제 차단은 실행 후 판단
            skip_execution = False
            if blocked_manager and selected_vpn is not None and selected_vpn != 'L':
                # 주요 버전들 체크 (130, 144, beta, dev, canary)
                check_versions = ['130', '144', 'beta', 'dev', 'canary']
                blocked_versions = []

                for ver in check_versions:
                    is_blocked, remaining = blocked_manager.is_blocked(selected_vpn, ver)
                    if is_blocked:
                        blocked_versions.append((ver, remaining))

                # 모든 버전이 차단되었으면 1분 대기 후 재시도
                if len(blocked_versions) >= 3:  # 3개 이상 차단되었으면 대기
                    print(f"   ⏸️  차단된 조합이 너무 많음 (VPN {selected_vpn})")
                    for ver, remaining in blocked_versions[:3]:
                        print(f"      - Chrome {ver}: {remaining // 60}분 {remaining % 60}초 남음")
                    print(f"   ⏰ 1분 후 재시도...")
                    time.sleep(60)
                    # i를 증가시키지 않음 (재시도이므로 작업 횟수에 포함 안 함)
                    if not is_infinite:
                        i -= 1  # 다음 루프에서 i += 1 되므로 상쇄
                    continue

            # agent.py 실행 명령어 구성 (기본: --work-api --version random --close)
            cmd = [
                "python3", "agent.py",
                "--work-api",
                "--version", "random",
            ]

            # VPN 옵션 추가 (L이 아닌 경우만)
            if selected_vpn and selected_vpn != 'L':
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

            # agent.py 실행 (출력 캡처)
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent,
                capture_output=True,  # 출력 캡처 (차단 감지용)
                text=True
            )

            elapsed = time.time() - start_time
            success = (result.returncode == 0)

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

            # 차단 감지 및 처리
            if blocked_manager and selected_vpn is not None:
                # 출력에서 Chrome 버전 파싱
                chrome_version = None
                for line in result.stdout.split('\n'):
                    if 'Chrome Version:' in line:
                        # "Chrome Version: 144" -> "144" 추출
                        parts = line.split(':')
                        if len(parts) >= 2:
                            chrome_version = parts[1].strip()
                        break

                if chrome_version:
                    # 차단 키워드 검색 (full_output은 이미 Line 339에서 선언됨)
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

            if success:
                print(f"\n[Worker-{worker_id}] ✅ 작업 {iteration_str} 완료 ({elapsed:.1f}초)")
            else:
                print(f"\n[Worker-{worker_id}] ❌ 작업 {iteration_str} 실패 ({elapsed:.1f}초)")

        except Exception as e:
            print(f"\n[Worker-{worker_id}] ❌ 오류 발생: {e}")
            stats.add_result(False)

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

창 배치 레이아웃 (최대 6개 스레드):
  1  2  3
  4  5  6

차단 조합 관리:
  - http2 차단 발생 시 VPN+Chrome 버전 조합을 자동으로 차단 목록에 추가
  - 차단된 조합은 3분간 재시도하지 않음
  - 3분 후 재시도해서 성공하면 차단 목록에서 자동 제거
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
        print(f"VPN 리스트: {', '.join(vpn_list)} (랜덤 선택)")
    if adjust_mode:
        print(f"Adjust 모드: {adjust_mode}")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

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
