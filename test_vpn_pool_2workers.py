#!/usr/bin/env python3
"""
VPN Pool 2개 워커 테스트
- 헤드리스 모드로 IP만 체크
- 프로필 폴더 권한 확인
"""

import subprocess
import threading
import time
import sys
from pathlib import Path

# VPN API 클라이언트 임포트
from lib.modules.vpn_api_client import VPNAPIClient, VPNConnection


def test_worker(worker_id: int, headless: bool = True):
    """
    단일 워커 테스트

    Args:
        worker_id: 워커 ID (1부터 시작)
        headless: 헤드리스 모드 여부
    """
    print(f"\n{'='*60}")
    print(f"Worker {worker_id} 시작")
    print(f"{'='*60}")

    # 1. VPN API 클라이언트 생성
    vpn_client = VPNAPIClient()

    # 2. VPN 연결
    vpn_conn = VPNConnection(worker_id=worker_id, vpn_client=vpn_client)

    try:
        if not vpn_conn.connect():
            print(f"❌ Worker {worker_id}: VPN 연결 실패")
            return False

        print(f"✅ Worker {worker_id}: VPN 연결 성공")
        if vpn_conn.vpn_key_data:
            print(f"   Internal IP: {vpn_conn.vpn_key_data['internal_ip']}")
            print(f"   Server IP: {vpn_conn.vpn_key_data['server_ip']}")

        # 2. Agent 실행 (sudo -u vpn-worker-N)
        username = f"vpn-worker-{worker_id}"

        # Agent 명령어 구성
        cmd = [
            "sudo", "-u", username,
            "python3", "/home/tech/rank_screenshot/agent.py",
            "--version", "144",
            f"--vpn-pool-worker={worker_id}"
        ]

        if headless:
            # 헤드리스 모드: IP만 체크하고 종료
            cmd.append("--ip-check")
        else:
            # 일반 모드: 3초 후 자동 종료
            cmd.append("--close")

        print(f"\n실행 명령어: {' '.join(cmd)}")

        # X11 권한 부여
        subprocess.run(["xhost", f"+SI:localuser:{username}"],
                      capture_output=True, timeout=5)

        # Agent 실행
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env={'DISPLAY': ':0'}
        )

        print(f"\n--- Worker {worker_id} Output ---")
        print(result.stdout)
        if result.stderr:
            print(f"--- Worker {worker_id} Error ---")
            print(result.stderr)
        print(f"--- End Worker {worker_id} ---\n")

        success = result.returncode == 0

        if success:
            print(f"✅ Worker {worker_id}: Agent 실행 성공")
        else:
            print(f"❌ Worker {worker_id}: Agent 실행 실패 (exit code: {result.returncode})")

        return success

    except subprocess.TimeoutExpired:
        print(f"⏱️  Worker {worker_id}: 타임아웃 (60초)")
        return False
    except Exception as e:
        print(f"❌ Worker {worker_id}: 오류 발생: {e}")
        return False
    finally:
        # VPN 연결 해제
        print(f"\nWorker {worker_id}: VPN 연결 해제 중...")
        vpn_conn.disconnect()
        print(f"✅ Worker {worker_id}: VPN 연결 해제 완료")


def main():
    """메인 함수"""
    print("=" * 60)
    print("VPN Pool 2개 워커 테스트")
    print("=" * 60)

    # 헤드리스 모드 여부 확인
    headless = "--headless" in sys.argv

    print(f"\n모드: {'헤드리스' if headless else '일반'}")
    print(f"워커 수: 2개")
    print(f"Chrome 버전: 144")
    print()

    # 프로필 폴더 권한 확인
    print("프로필 폴더 권한 확인:")
    for i in range(1, 3):
        profile_dir = Path(f"/home/tech/rank_screenshot/browser-profiles/vpn-worker-{i}")

        if profile_dir.exists():
            stat = profile_dir.stat()
            perms = oct(stat.st_mode)[-3:]
            print(f"  vpn-worker-{i}: {perms} (exists)")
        else:
            print(f"  vpn-worker-{i}: (not exists yet)")

    print()

    # 순차 실행 (동시성 문제 없이 테스트)
    results = []

    for worker_id in [1, 2]:
        success = test_worker(worker_id, headless=headless)
        results.append((worker_id, success))

        # 워커 간 대기
        if worker_id < 2:
            print(f"\n⏸️  다음 워커 시작 전 5초 대기...\n")
            time.sleep(5)

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    for worker_id, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"Worker {worker_id}: {status}")

    total_success = sum(1 for _, success in results if success)
    print(f"\n총 성공: {total_success}/2")

    # 프로필 폴더 최종 상태
    print("\n프로필 폴더 최종 상태:")
    for i in range(1, 3):
        profile_dir = Path(f"/home/tech/rank_screenshot/browser-profiles/vpn-worker-{i}")

        if profile_dir.exists():
            import os
            size = sum(f.stat().st_size for f in profile_dir.rglob('*') if f.is_file())
            size_mb = size / 1024 / 1024
            stat = profile_dir.stat()
            perms = oct(stat.st_mode)[-3:]
            print(f"  vpn-worker-{i}: {size_mb:.1f}MB, perms={perms}")
        else:
            print(f"  vpn-worker-{i}: (not created)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단됨")
        sys.exit(1)
