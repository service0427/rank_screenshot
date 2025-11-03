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
from datetime import datetime
from pathlib import Path


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


def run_worker(worker_id: int, iterations: int, stats: WorkerStats, adjust_mode: str = None, vpn_list: list = None):
    """
    개별 워커 실행

    Args:
        worker_id: 워커 ID (1부터 시작)
        iterations: 반복 횟수
        stats: 통계 객체
        adjust_mode: Adjust 모드 ("adjust", "adjust2", None)
        vpn_list: VPN 번호 리스트 (None: VPN 사용 안 함, ['L', '0', '1'] 등)
    """
    print(f"[Worker-{worker_id}] 시작 - {iterations}회 반복 (instance_id={worker_id})")

    for i in range(1, iterations + 1):
        try:
            start_time = time.time()

            # VPN 랜덤 선택
            selected_vpn = None
            if vpn_list:
                selected_vpn = random.choice(vpn_list)
                if selected_vpn == 'L':
                    print(f"\n[Worker-{worker_id}] 작업 {i}/{iterations} 시작 (VPN: Local)")
                else:
                    print(f"\n[Worker-{worker_id}] 작업 {i}/{iterations} 시작 (VPN: {selected_vpn})")
            else:
                print(f"\n[Worker-{worker_id}] 작업 {i}/{iterations} 시작")
            print("=" * 60)

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

            # 나머지 옵션 추가
            cmd.extend([
                "--close",
                "--instance", str(worker_id)  # 워커 ID를 instance_id로 사용
            ])

            # agent.py 실행
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent,
                capture_output=False,  # 출력을 콘솔에 표시
                text=True
            )

            elapsed = time.time() - start_time
            success = (result.returncode == 0)

            # 통계 업데이트
            stats.add_result(success)

            if success:
                print(f"\n[Worker-{worker_id}] ✅ 작업 {i}/{iterations} 완료 ({elapsed:.1f}초)")
            else:
                print(f"\n[Worker-{worker_id}] ❌ 작업 {i}/{iterations} 실패 ({elapsed:.1f}초)")

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
  # 3개 스레드로 각각 10회 실행 (기본: 순위 조정 없음)
  python3 run_workers.py --threads 3 --iterations 10

  # Adjust 모드로 5개 스레드 실행
  python3 run_workers.py -t 5 -i 20 --adjust

  # Adjust2 (Simple Swap) 모드로 실행
  python3 run_workers.py -t 3 -i 10 --adjust2

  # VPN 랜덤 선택 (0-5번 중 랜덤)
  python3 run_workers.py -t 3 -i 10 --vpn=0,1,2,3,4,5

  # 로컬 + VPN 0-5번 중 랜덤 선택 (L은 로컬/VPN 없음)
  python3 run_workers.py -t 3 -i 10 --vpn=L,0,1,2,3,4,5
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
        default=1,
        help="각 스레드당 반복 횟수 (기본: 1)"
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

    args = parser.parse_args()

    # 입력 검증
    if args.threads < 1:
        print("❌ 스레드 개수는 1 이상이어야 합니다")
        return

    if args.iterations < 1:
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

    # 스레드 생성 및 시작
    threads = []
    start_time = time.time()

    for worker_id in range(1, args.threads + 1):
        thread = threading.Thread(
            target=run_worker,
            args=(worker_id, args.iterations, stats, adjust_mode, vpn_list),
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
    print(f"성공률: {final_stats['success'] / final_stats['total'] * 100:.1f}%")
    print(f"총 소요 시간: {elapsed / 60:.1f}분 ({elapsed:.1f}초)")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
