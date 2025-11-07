#!/usr/bin/env python3
"""
VPN 연결 상태 추적 모듈

목적:
- WireGuard 연결이 정상적으로 해제되지 않은 경우 감지
- 프로세스 종료 후에도 연결 상태 추적
- JSON 파일로 영구 저장

사용 예시:
    tracker = VPNConnectionTracker()

    # 연결 시작
    tracker.register_connection(worker_id=1, interface="wg-10-8-0-14", internal_ip="10.8.0.14")

    # 연결 해제
    tracker.unregister_connection(worker_id=1)

    # 미해제 연결 확인
    orphaned = tracker.get_orphaned_connections()
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class VPNConnectionTracker:
    """VPN 연결 상태 추적 클래스"""

    def __init__(self, state_file: str = "/tmp/vpn_connections_state.json"):
        """
        Args:
            state_file: 상태 파일 경로
        """
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """상태 파일 로드"""
        if not self.state_file.exists():
            return {"connections": {}}

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 파일이 손상된 경우 새로 시작
            return {"connections": {}}

    def _save_state(self):
        """상태 파일 저장"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            print(f"⚠️  상태 파일 저장 실패: {e}")

    def register_connection(
        self,
        worker_id: int,
        interface: str,
        internal_ip: str,
        server_ip: str = None,
        config_path: str = None
    ):
        """
        VPN 연결 등록

        Args:
            worker_id: 워커 ID
            interface: WireGuard 인터페이스명 (예: wg-10-8-0-14)
            internal_ip: 내부 IP (예: 10.8.0.14)
            server_ip: VPN 서버 IP (선택)
            config_path: 설정 파일 경로 (선택)
        """
        key = str(worker_id)

        self.state["connections"][key] = {
            "worker_id": worker_id,
            "interface": interface,
            "internal_ip": internal_ip,
            "server_ip": server_ip,
            "config_path": config_path,
            "registered_at": datetime.now().isoformat(),
            "pid": subprocess.os.getpid()
        }

        self._save_state()
        print(f"   📝 VPN 연결 추적 등록: Worker-{worker_id} → {interface} ({internal_ip})")

    def unregister_connection(self, worker_id: int):
        """
        VPN 연결 해제 등록

        Args:
            worker_id: 워커 ID
        """
        key = str(worker_id)

        if key in self.state["connections"]:
            conn_info = self.state["connections"][key]
            del self.state["connections"][key]
            self._save_state()
            print(f"   📝 VPN 연결 추적 해제: Worker-{worker_id} → {conn_info['interface']}")
        else:
            print(f"   ⚠️  VPN 연결 추적 해제 실패: Worker-{worker_id} (등록되지 않음)")

    def get_orphaned_connections(self) -> List[Dict]:
        """
        미해제 연결 조회 (실제 인터페이스는 없지만 JSON에만 남아있음)

        Returns:
            미해제 연결 목록
        """
        orphaned = []

        # 현재 시스템의 WireGuard 인터페이스 목록
        existing_interfaces = self._get_existing_interfaces()

        for key, conn_info in self.state["connections"].items():
            interface = conn_info["interface"]

            # JSON에는 있지만 실제 인터페이스가 없는 경우
            if interface not in existing_interfaces:
                orphaned.append(conn_info)

        return orphaned

    def get_active_connections(self) -> List[Dict]:
        """
        활성 연결 조회 (JSON에도 있고 실제 인터페이스도 있음)

        Returns:
            활성 연결 목록
        """
        active = []

        # 현재 시스템의 WireGuard 인터페이스 목록
        existing_interfaces = self._get_existing_interfaces()

        for key, conn_info in self.state["connections"].items():
            interface = conn_info["interface"]

            # JSON에도 있고 실제 인터페이스도 있는 경우
            if interface in existing_interfaces:
                active.append(conn_info)

        return active

    def get_untracked_connections(self) -> List[str]:
        """
        추적되지 않는 연결 조회 (실제 인터페이스는 있지만 JSON에는 없음)

        Returns:
            추적되지 않는 인터페이스 목록
        """
        untracked = []

        # 현재 시스템의 WireGuard 인터페이스 목록
        existing_interfaces = self._get_existing_interfaces()

        # JSON에 등록된 인터페이스 목록
        tracked_interfaces = {
            conn_info["interface"]
            for conn_info in self.state["connections"].values()
        }

        # 실제로는 있지만 JSON에는 없는 인터페이스
        for iface in existing_interfaces:
            if iface not in tracked_interfaces:
                untracked.append(iface)

        return untracked

    def _get_existing_interfaces(self) -> List[str]:
        """
        시스템에 존재하는 WireGuard 인터페이스 목록 조회

        Returns:
            인터페이스 목록
        """
        try:
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # wg로 시작하는 인터페이스 추출
            interfaces = []
            for line in result.stdout.split('\n'):
                # 예: "4: wg-10-8-0-14: <POINTOPOINT,NOARP,UP,LOWER_UP> ..."
                if ': wg' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        iface_name = parts[1].strip().split('@')[0]
                        if iface_name.startswith('wg'):
                            interfaces.append(iface_name)

            return interfaces

        except Exception as e:
            print(f"⚠️  인터페이스 조회 실패: {e}")
            return []

    def cleanup_orphaned_connections(self):
        """
        미해제 연결을 JSON에서 제거

        Returns:
            제거된 연결 수
        """
        orphaned = self.get_orphaned_connections()

        if not orphaned:
            print("   ℹ️  미해제 연결 없음")
            return 0

        print(f"   🧹 미해제 연결 {len(orphaned)}개 JSON에서 제거 중...")

        for conn_info in orphaned:
            worker_id = conn_info["worker_id"]
            self.unregister_connection(worker_id)

        return len(orphaned)

    def print_status(self):
        """현재 연결 상태 출력"""
        print("\n" + "=" * 60)
        print("📊 VPN 연결 상태")
        print("=" * 60)

        active = self.get_active_connections()
        orphaned = self.get_orphaned_connections()
        untracked = self.get_untracked_connections()

        print(f"\n✅ 활성 연결 (JSON + 실제): {len(active)}개")
        if active:
            for conn in active:
                print(f"   - Worker-{conn['worker_id']}: {conn['interface']} ({conn['internal_ip']})")

        print(f"\n⚠️  미해제 연결 (JSON만): {len(orphaned)}개")
        if orphaned:
            for conn in orphaned:
                print(f"   - Worker-{conn['worker_id']}: {conn['interface']} ({conn['internal_ip']})")
                print(f"     등록 시각: {conn['registered_at']}")

        print(f"\n❓ 추적 안 됨 (실제만): {len(untracked)}개")
        if untracked:
            for iface in untracked:
                print(f"   - {iface}")

        print("\n" + "=" * 60 + "\n")


# 싱글톤 인스턴스
_tracker_instance = None


def get_vpn_tracker() -> VPNConnectionTracker:
    """VPN 연결 추적기 싱글톤 인스턴스 반환"""
    global _tracker_instance

    if _tracker_instance is None:
        _tracker_instance = VPNConnectionTracker()

    return _tracker_instance


if __name__ == "__main__":
    # 테스트 및 CLI
    import sys

    tracker = VPNConnectionTracker()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "status":
            tracker.print_status()

        elif command == "cleanup":
            tracker.cleanup_orphaned_connections()
            tracker.print_status()

        else:
            print("사용법:")
            print("  python3 vpn_connection_tracker.py status   # 상태 확인")
            print("  python3 vpn_connection_tracker.py cleanup  # 미해제 연결 정리")
    else:
        tracker.print_status()
