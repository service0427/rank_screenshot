#!/usr/bin/env python3
"""
VPN 수동 연결 스크립트

API에서 VPN 키를 가져와서 수동으로 WireGuard 연결을 생성합니다.

사용법:
    # 자동 선택 (워커 ID 1로 연결)
    python3 connect_vpn_manual.py

    # 워커 ID 지정
    python3 connect_vpn_manual.py --worker-id 2

    # 특정 VPN 서버 지정
    python3 connect_vpn_manual.py --worker-id 3 --server-ip 175.210.218.190

    # 연결 해제
    python3 connect_vpn_manual.py --disconnect --worker-id 1

    # 모든 연결 해제
    python3 connect_vpn_manual.py --disconnect-all
"""

import argparse
import sys
from pathlib import Path

# VPN API 클라이언트 및 연결 관리
from lib.modules.vpn_api_client import VPNAPIClient, VPNConnection
from lib.modules.vpn_connection_tracker import get_vpn_tracker


def connect_vpn(worker_id: int, server_ip: str = None):
    """
    VPN 연결

    Args:
        worker_id: 워커 ID
        server_ip: VPN 서버 IP (선택)
    """
    print("\n" + "=" * 60)
    print(f"🔐 VPN 수동 연결 (Worker-{worker_id})")
    print("=" * 60)

    # 1. VPN API 클라이언트 생성
    vpn_client = VPNAPIClient()

    # 2. VPN 연결
    vpn_conn = VPNConnection(worker_id=worker_id, vpn_client=vpn_client)

    # 3. 연결 시도
    success = vpn_conn.connect(server_ip=server_ip)

    if success:
        print("\n✅ VPN 연결 성공!")
        print(f"   Interface: {vpn_conn.interface_name}")
        print(f"   Internal IP: {vpn_conn.vpn_key_data['internal_ip']}")
        print(f"   Server IP: {vpn_conn.vpn_key_data['server_ip']}")
        print(f"   Config: {vpn_conn.config_path}")

        print("\n⚠️  연결 유지 중 - 종료하려면 다음 명령어 실행:")
        print(f"   python3 connect_vpn_manual.py --disconnect --worker-id {worker_id}")
        print()

        return True
    else:
        print("\n❌ VPN 연결 실패")
        return False


def disconnect_vpn(worker_id: int):
    """
    VPN 연결 해제

    Args:
        worker_id: 워커 ID
    """
    print("\n" + "=" * 60)
    print(f"🔌 VPN 연결 해제 (Worker-{worker_id})")
    print("=" * 60)

    # 추적 정보 조회
    tracker = get_vpn_tracker()
    conn_info = tracker.state["connections"].get(str(worker_id))

    if not conn_info:
        print(f"\n⚠️  Worker-{worker_id}는 연결되어 있지 않습니다")
        print("\n현재 연결된 워커:")
        tracker.print_status()
        return False

    # VPN 연결 객체 생성
    vpn_client = VPNAPIClient()
    vpn_conn = VPNConnection(worker_id=worker_id, vpn_client=vpn_client)

    # 추적 정보에서 가져오기
    vpn_conn.interface_name = conn_info["interface"]
    vpn_conn.config_path = Path(conn_info["config_path"]) if conn_info["config_path"] else None
    vpn_conn.vpn_key_data = {
        "internal_ip": conn_info["internal_ip"],
        "public_key": conn_info.get("public_key"),  # JSON에 없을 수 있음
    }

    # 연결 해제
    print(f"\n📋 연결 정보:")
    print(f"   Interface: {conn_info['interface']}")
    print(f"   Internal IP: {conn_info['internal_ip']}")
    print(f"   Server IP: {conn_info.get('server_ip', 'N/A')}")
    print()

    success = vpn_conn.disconnect()

    if success:
        print("\n✅ VPN 연결 해제 완료")
        return True
    else:
        print("\n⚠️  VPN 연결 해제 중 일부 오류 발생 (계속 진행됨)")
        return True


def disconnect_all_vpn():
    """모든 VPN 연결 해제"""
    print("\n" + "=" * 60)
    print("🧹 모든 VPN 연결 해제")
    print("=" * 60)

    tracker = get_vpn_tracker()
    active_connections = tracker.get_active_connections()

    if not active_connections:
        print("\n✅ 활성 VPN 연결이 없습니다")
        return True

    print(f"\n활성 연결: {len(active_connections)}개")
    for conn in active_connections:
        print(f"   - Worker-{conn['worker_id']}: {conn['interface']} ({conn['internal_ip']})")

    print()
    for conn in active_connections:
        worker_id = conn["worker_id"]
        print(f"\n{'─' * 60}")
        disconnect_vpn(worker_id)

    print("\n" + "=" * 60)
    print("✅ 모든 VPN 연결 해제 완료")
    print("=" * 60)
    print()

    return True


def show_status():
    """현재 VPN 연결 상태 출력"""
    tracker = get_vpn_tracker()
    tracker.print_status()


def main():
    parser = argparse.ArgumentParser(
        description="VPN 수동 연결/해제 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # VPN 연결
  python3 connect_vpn_manual.py --worker-id 1
  python3 connect_vpn_manual.py --worker-id 2 --server-ip 175.210.218.190

  # VPN 연결 해제
  python3 connect_vpn_manual.py --disconnect --worker-id 1
  python3 connect_vpn_manual.py --disconnect-all

  # 상태 확인
  python3 connect_vpn_manual.py --status
        """
    )

    parser.add_argument(
        '--worker-id',
        type=int,
        default=1,
        help='워커 ID (기본: 1)'
    )

    parser.add_argument(
        '--server-ip',
        type=str,
        help='VPN 서버 IP 지정 (선택)'
    )

    parser.add_argument(
        '--disconnect',
        action='store_true',
        help='VPN 연결 해제'
    )

    parser.add_argument(
        '--disconnect-all',
        action='store_true',
        help='모든 VPN 연결 해제'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='현재 VPN 연결 상태 확인'
    )

    args = parser.parse_args()

    try:
        # 상태 확인
        if args.status:
            show_status()
            return 0

        # 모든 연결 해제
        if args.disconnect_all:
            success = disconnect_all_vpn()
            return 0 if success else 1

        # 개별 연결 해제
        if args.disconnect:
            success = disconnect_vpn(args.worker_id)
            return 0 if success else 1

        # VPN 연결
        success = connect_vpn(args.worker_id, args.server_ip)
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단됨")
        return 1
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
