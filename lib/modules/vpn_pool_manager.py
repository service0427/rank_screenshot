#!/usr/bin/env python3
"""
VPN 키 풀 매니저
WireGuard 연결/해제 자동화 및 키 관리
"""

import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Dict
from .vpn_pool_client import VPNPoolClient


class VPNPoolManager:
    """VPN 키 풀 + WireGuard 연결 자동 관리"""

    def __init__(self, api_server: str = "http://112.161.221.82:3000"):
        """
        Args:
            api_server: VPN 키 풀 API 서버 주소
        """
        self.client = VPNPoolClient(api_server=api_server)
        self.active_connections = {}  # {instance_id: {'key_info': ..., 'interface': ...}}
        self.config_dir = Path("/tmp/vpn_configs")
        self.config_dir.mkdir(exist_ok=True, mode=0o755)

    def connect(self, instance_id: int) -> Optional[Dict]:
        """
        VPN 연결 (키 할당 + WireGuard 연결)

        Args:
            instance_id: 워커 인스턴스 ID

        Returns:
            연결 정보 또는 None (실패 시)
            {
                'internal_ip': '10.8.0.X',
                'interface': 'wg-worker-X',
                'public_key': 'xxx'
            }
        """
        print(f"🔐 VPN 연결 중... (Worker-{instance_id})")

        # 1. VPN 키 할당
        key_info = self.client.allocate_key(instance_id=instance_id)

        if not key_info:
            print(f"   ❌ Worker-{instance_id}: VPN 키 할당 실패")
            return None

        internal_ip = key_info.get('internal_ip')
        public_key = key_info.get('public_key')

        # 2. WireGuard 설정 파일 저장
        config_path = self.config_dir / f"worker_{instance_id}.conf"
        if not self.client.save_config_file(instance_id, str(config_path)):
            print(f"   ❌ Worker-{instance_id}: 설정 파일 저장 실패")
            self.client.release_key(instance_id)
            return None

        # 3. WireGuard 인터페이스 이름
        interface_name = f"wg-worker-{instance_id}"

        # 4. WireGuard 연결
        try:
            # wg-quick up 명령어 실행
            # sudo 권한이 필요하지만, sudoers 설정으로 비밀번호 없이 실행 가능
            result = subprocess.run(
                ["sudo", "wg-quick", "up", str(config_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # 연결 정보 저장
                self.active_connections[instance_id] = {
                    'key_info': key_info,
                    'interface': interface_name,
                    'config_path': str(config_path)
                }

                print(f"   ✅ VPN 연결 성공!")
                print(f"   📍 Internal IP: {internal_ip}")
                print(f"   🌐 Interface: {interface_name}")

                # 연결 안정화 대기
                time.sleep(2)

                return {
                    'internal_ip': internal_ip,
                    'interface': interface_name,
                    'public_key': public_key
                }
            else:
                print(f"   ❌ WireGuard 연결 실패:")
                print(f"   {result.stderr}")

                # 키 반납
                self.client.release_key(instance_id)
                return None

        except subprocess.TimeoutExpired:
            print(f"   ❌ WireGuard 연결 타임아웃")
            self.client.release_key(instance_id)
            return None
        except FileNotFoundError:
            print(f"   ❌ wg-quick 명령어를 찾을 수 없습니다")
            print(f"   ⚠️  WireGuard가 설치되어 있는지 확인하세요: sudo apt install wireguard")
            self.client.release_key(instance_id)
            return None
        except Exception as e:
            print(f"   ❌ WireGuard 연결 중 오류: {e}")
            self.client.release_key(instance_id)
            return None

    def disconnect(self, instance_id: int) -> bool:
        """
        VPN 연결 해제 (WireGuard 해제 + 키 반납)

        Args:
            instance_id: 워커 인스턴스 ID

        Returns:
            성공 여부
        """
        if instance_id not in self.active_connections:
            print(f"   ⚠️  Worker-{instance_id}: 활성 연결이 없습니다")
            return True

        conn_info = self.active_connections[instance_id]
        config_path = conn_info['config_path']

        print(f"🔌 VPN 연결 해제 중... (Worker-{instance_id})")

        # 1. WireGuard 연결 해제
        try:
            result = subprocess.run(
                ["sudo", "wg-quick", "down", config_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"   ✅ WireGuard 연결 해제 성공")
            else:
                # 이미 해제되었거나 없는 경우도 성공으로 간주
                print(f"   ⚠️  WireGuard 해제: {result.stderr.strip()}")

        except Exception as e:
            print(f"   ⚠️  WireGuard 해제 중 오류 (무시): {e}")

        # 2. 설정 파일 삭제
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
        except Exception as e:
            print(f"   ⚠️  설정 파일 삭제 실패 (무시): {e}")

        # 3. VPN 키 반납
        success = self.client.release_key(instance_id)

        # 4. 연결 정보 삭제
        del self.active_connections[instance_id]

        return success

    def disconnect_all(self):
        """모든 활성 VPN 연결 해제"""
        instance_ids = list(self.active_connections.keys())

        if not instance_ids:
            print("   ℹ️  활성 VPN 연결이 없습니다")
            return

        print(f"🧹 모든 VPN 연결 해제 중... ({len(instance_ids)}개)")

        for instance_id in instance_ids:
            self.disconnect(instance_id)

        print("   ✅ 모든 VPN 연결 해제 완료")

    def get_connection_info(self, instance_id: int) -> Optional[Dict]:
        """
        연결 정보 조회

        Args:
            instance_id: 워커 인스턴스 ID

        Returns:
            연결 정보 또는 None
        """
        if instance_id not in self.active_connections:
            return None

        conn_info = self.active_connections[instance_id]
        key_info = conn_info['key_info']

        return {
            'internal_ip': key_info.get('internal_ip'),
            'interface': conn_info['interface'],
            'public_key': key_info.get('public_key')
        }

    def is_connected(self, instance_id: int) -> bool:
        """
        연결 여부 확인

        Args:
            instance_id: 워커 인스턴스 ID

        Returns:
            연결 여부
        """
        return instance_id in self.active_connections

    def get_server_status(self) -> Optional[Dict]:
        """
        VPN 키 풀 서버 상태 조회

        Returns:
            서버 상태 또는 None
        """
        return self.client.get_status()


# 싱글톤 인스턴스 (run_workers.py에서 공유)
_vpn_pool_manager = None


def get_vpn_pool_manager() -> VPNPoolManager:
    """VPN 키 풀 매니저 싱글톤 인스턴스 반환"""
    global _vpn_pool_manager

    if _vpn_pool_manager is None:
        _vpn_pool_manager = VPNPoolManager()

    return _vpn_pool_manager
