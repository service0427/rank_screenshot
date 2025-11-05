#!/usr/bin/env python3
"""
VPN 키 풀 클라이언트
동적 키 할당/반납 방식의 새로운 VPN 시스템 지원
"""

import requests
import json
import time
from typing import Optional, Dict


class VPNPoolClient:
    """VPN 키 풀 관리 클라이언트"""

    def __init__(self, api_server: str = "http://112.161.221.82:3000"):
        """
        Args:
            api_server: VPN 키 풀 API 서버 주소
        """
        self.api_server = api_server.rstrip('/')
        self.allocated_keys = {}  # {instance_id: key_info}

    def allocate_key(self, instance_id: int, timeout: int = 10) -> Optional[Dict]:
        """
        VPN 키 할당받기

        Args:
            instance_id: 워커 인스턴스 ID
            timeout: 타임아웃 (초)

        Returns:
            {
                'success': True,
                'server_ip': '112.161.221.82',
                'server_port': 55555,
                'server_pubkey': 'xxx',
                'private_key': 'xxx',
                'public_key': 'xxx',
                'internal_ip': '10.8.0.34',
                'config': 'WireGuard config...'
            }
            또는 None (실패 시)
        """
        try:
            print(f"🔑 VPN 키 할당 요청 중... (Worker-{instance_id})")

            response = requests.get(
                f"{self.api_server}/api/vpn/allocate",
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    # 할당 정보 저장
                    self.allocated_keys[instance_id] = data

                    print(f"   ✅ VPN 키 할당 성공!")
                    print(f"   📍 Internal IP: {data.get('internal_ip')}")
                    print(f"   🔐 Public Key: {data.get('public_key')[:20]}...")

                    return data
                else:
                    error = data.get('error', 'Unknown error')
                    print(f"   ❌ 할당 실패: {error}")
                    return None
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text}")
                return None

        except requests.exceptions.Timeout:
            print(f"   ❌ 타임아웃: VPN 키 풀 서버 응답 없음 ({timeout}초)")
            return None
        except requests.exceptions.ConnectionError:
            print(f"   ❌ 연결 실패: VPN 키 풀 서버에 연결할 수 없음")
            return None
        except Exception as e:
            print(f"   ❌ 키 할당 실패: {e}")
            return None

    def release_key(self, instance_id: int, timeout: int = 10) -> bool:
        """
        VPN 키 반납하기

        Args:
            instance_id: 워커 인스턴스 ID
            timeout: 타임아웃 (초)

        Returns:
            성공 여부
        """
        # 할당된 키가 없으면 반납 불필요
        if instance_id not in self.allocated_keys:
            print(f"   ⚠️  Worker-{instance_id}: 할당된 키가 없음 (반납 불필요)")
            return True

        key_info = self.allocated_keys[instance_id]
        public_key = key_info.get('public_key')

        if not public_key:
            print(f"   ⚠️  Worker-{instance_id}: Public Key 없음")
            return False

        try:
            print(f"🔓 VPN 키 반납 중... (Worker-{instance_id})")

            response = requests.post(
                f"{self.api_server}/api/vpn/release",
                headers={'Content-Type': 'application/json'},
                json={'public_key': public_key},
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    # 할당 정보 삭제
                    del self.allocated_keys[instance_id]

                    print(f"   ✅ VPN 키 반납 성공!")
                    return True
                else:
                    error = data.get('error', 'Unknown error')
                    print(f"   ❌ 반납 실패: {error}")
                    return False
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print(f"   ❌ 타임아웃: VPN 키 풀 서버 응답 없음 ({timeout}초)")
            return False
        except requests.exceptions.ConnectionError:
            print(f"   ❌ 연결 실패: VPN 키 풀 서버에 연결할 수 없음")
            return False
        except Exception as e:
            print(f"   ❌ 키 반납 실패: {e}")
            return False

    def get_status(self, timeout: int = 10) -> Optional[Dict]:
        """
        VPN 키 풀 상태 조회

        Args:
            timeout: 타임아웃 (초)

        Returns:
            {
                'statistics': {
                    'total': 100,
                    'available': 95,
                    'allocated': 5
                },
                'keys': [...]
            }
            또는 None (실패 시)
        """
        try:
            response = requests.get(
                f"{self.api_server}/api/vpn/status",
                timeout=timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text}")
                return None

        except Exception as e:
            print(f"   ❌ 상태 조회 실패: {e}")
            return None

    def save_config_file(self, instance_id: int, output_path: str) -> bool:
        """
        WireGuard 설정 파일 저장

        Args:
            instance_id: 워커 인스턴스 ID
            output_path: 저장할 파일 경로

        Returns:
            성공 여부
        """
        if instance_id not in self.allocated_keys:
            print(f"   ❌ Worker-{instance_id}: 할당된 키가 없음")
            return False

        key_info = self.allocated_keys[instance_id]
        config = key_info.get('config')

        if not config:
            print(f"   ❌ Worker-{instance_id}: 설정 파일 없음")
            return False

        try:
            with open(output_path, 'w') as f:
                f.write(config)

            print(f"   ✅ 설정 파일 저장: {output_path}")
            return True

        except Exception as e:
            print(f"   ❌ 파일 저장 실패: {e}")
            return False

    def get_allocated_ip(self, instance_id: int) -> Optional[str]:
        """
        할당된 Internal IP 반환

        Args:
            instance_id: 워커 인스턴스 ID

        Returns:
            Internal IP (예: "10.8.0.34") 또는 None
        """
        if instance_id not in self.allocated_keys:
            return None

        return self.allocated_keys[instance_id].get('internal_ip')

    def cleanup_all(self):
        """모든 할당된 키 반납"""
        print(f"🧹 모든 VPN 키 반납 중... ({len(self.allocated_keys)}개)")

        instance_ids = list(self.allocated_keys.keys())
        success_count = 0

        for instance_id in instance_ids:
            if self.release_key(instance_id):
                success_count += 1

        print(f"   ✅ {success_count}/{len(instance_ids)}개 반납 완료")
