#!/usr/bin/env python3
"""
VPN 키 풀 시스템 테스트 스크립트
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.modules.vpn_pool_client import VPNPoolClient


def test_vpn_pool():
    """VPN 키 풀 전체 테스트"""

    print("=" * 60)
    print("🧪 VPN 키 풀 시스템 테스트")
    print("=" * 60)
    print()

    client = VPNPoolClient()

    # 1. 서버 상태 확인
    print("📊 1. 서버 상태 확인")
    print("-" * 60)
    status = client.get_status()

    if status:
        stats = status.get('statistics', {})
        print(f"   전체 키: {stats.get('total', 0)}개")
        print(f"   사용 가능: {stats.get('available', 0)}개")
        print(f"   할당됨: {stats.get('allocated', 0)}개")
    else:
        print("   ⚠️  서버에 연결할 수 없습니다.")
        print("   ⚠️  서버가 시작되지 않았거나 네트워크 문제가 있습니다.")
        print()
        print("   테스트를 중단합니다.")
        return

    print()
    time.sleep(1)

    # 2. 키 할당 테스트
    print("🔑 2. VPN 키 할당 테스트")
    print("-" * 60)
    key_info = client.allocate_key(instance_id=1)

    if not key_info:
        print("   ❌ 키 할당 실패!")
        return

    print()
    time.sleep(1)

    # 3. 설정 파일 저장 테스트
    print("💾 3. 설정 파일 저장 테스트")
    print("-" * 60)
    config_path = "/tmp/vpn_test_client.conf"
    if client.save_config_file(instance_id=1, output_path=config_path):
        print(f"   ✅ 설정 파일: {config_path}")

        # 파일 내용 일부 출력
        with open(config_path, 'r') as f:
            lines = f.readlines()[:5]
            print("\n   --- 설정 파일 앞부분 ---")
            for line in lines:
                print(f"   {line.rstrip()}")
            print(f"   ... (총 {len(f.readlines()) + 5}줄)")
    else:
        print("   ❌ 설정 파일 저장 실패!")

    print()
    time.sleep(1)

    # 4. 할당된 IP 확인
    print("📍 4. 할당된 IP 확인")
    print("-" * 60)
    internal_ip = client.get_allocated_ip(instance_id=1)
    if internal_ip:
        print(f"   Internal IP: {internal_ip}")
    else:
        print("   ❌ IP 정보 없음")

    print()
    time.sleep(1)

    # 5. 키 반납 대기
    print("⏸️  5. 키 반납 테스트 준비")
    print("-" * 60)
    print("   Enter를 누르면 키를 반납합니다...")
    input()

    # 6. 키 반납 테스트
    print("🔓 6. VPN 키 반납 테스트")
    print("-" * 60)
    if client.release_key(instance_id=1):
        print("   ✅ 키 반납 성공!")
    else:
        print("   ❌ 키 반납 실패!")

    print()
    time.sleep(1)

    # 7. 최종 상태 확인
    print("📊 7. 최종 상태 확인")
    print("-" * 60)
    status = client.get_status()

    if status:
        stats = status.get('statistics', {})
        print(f"   전체 키: {stats.get('total', 0)}개")
        print(f"   사용 가능: {stats.get('available', 0)}개")
        print(f"   할당됨: {stats.get('allocated', 0)}개")
    else:
        print("   ⚠️  상태 조회 실패")

    print()
    print("=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)


def test_multiple_allocation():
    """다중 키 할당 테스트"""

    print("=" * 60)
    print("🧪 다중 VPN 키 할당 테스트")
    print("=" * 60)
    print()

    client = VPNPoolClient()
    worker_count = 3

    # 서버 상태 확인
    print("📊 서버 상태 확인")
    print("-" * 60)
    status = client.get_status()

    if not status:
        print("   ⚠️  서버에 연결할 수 없습니다.")
        return

    stats = status.get('statistics', {})
    print(f"   사용 가능: {stats.get('available', 0)}개")
    print()

    # 다중 키 할당
    print(f"🔑 {worker_count}개 워커에 키 할당")
    print("-" * 60)

    for i in range(1, worker_count + 1):
        print(f"\n[Worker-{i}]")
        key_info = client.allocate_key(instance_id=i)

        if key_info:
            print(f"   ✅ 할당 성공: {key_info.get('internal_ip')}")
        else:
            print(f"   ❌ 할당 실패!")

        time.sleep(0.5)

    print()
    time.sleep(1)

    # 현재 상태
    print("📊 현재 상태")
    print("-" * 60)
    status = client.get_status()
    if status:
        stats = status.get('statistics', {})
        print(f"   할당됨: {stats.get('allocated', 0)}개")
        print(f"   사용 가능: {stats.get('available', 0)}개")

    print()
    print("⏸️  Enter를 누르면 모든 키를 반납합니다...")
    input()

    # 모든 키 반납
    print()
    print("🔓 모든 키 반납")
    print("-" * 60)
    client.cleanup_all()

    print()
    print("=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VPN 키 풀 테스트")
    parser.add_argument(
        "--multi",
        action="store_true",
        help="다중 키 할당 테스트"
    )

    args = parser.parse_args()

    if args.multi:
        test_multiple_allocation()
    else:
        test_vpn_pool()
