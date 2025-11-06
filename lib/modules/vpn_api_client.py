#!/usr/bin/env python3
"""
VPN 키 풀 API Client
WireGuard 기반 동적 VPN 키 할당/반납 클라이언트
"""

import requests
import subprocess
import tempfile
import os
from typing import Dict, Optional
from pathlib import Path


class VPNAPIClient:
    """
    VPN 키 풀 API 클라이언트

    작업 시작 시 VPN 키를 동적으로 할당받고,
    작업 완료 시 키를 반납하는 방식

    API 엔드포인트: http://220.121.120.83/vpn_api/
    - /allocate: VPN 키 할당
    - /release: VPN 키 반납
    - /list: VPN 서버 목록 조회
    - /status: 키 사용 현황 조회
    """

    BASE_URL = "http://220.121.120.83/vpn_api"

    def __init__(self, timeout: int = 10):
        """
        Args:
            timeout: API 요청 타임아웃 (초)
        """
        self.timeout = timeout

    def allocate_key(self, server_ip: Optional[str] = None) -> Optional[Dict]:
        """
        VPN 키 할당받기

        Args:
            server_ip: 특정 VPN 서버 IP (None이면 자동 선택)

        Returns:
            {
                'server_ip': '123.123.123.123',
                'server_port': 51820,
                'server_pubkey': 'BHhF...',
                'private_key': 'aEGr...',
                'public_key': 'BMbX...',
                'internal_ip': '10.8.0.10',
                'config': '[Interface]\\nPrivateKey = ...'
            }
            실패 시 None
        """
        try:
            url = f"{self.BASE_URL}/allocate"
            params = {}
            if server_ip:
                params['ip'] = server_ip

            print(f"   🔑 VPN 키 할당 요청 중...")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                print(f"   ❌ VPN 키 할당 실패: {error_msg}")
                return None

            print(f"   ✅ VPN 키 할당 완료")
            print(f"      서버: {data['server_ip']}")
            print(f"      내부 IP: {data['internal_ip']}")

            return data

        except requests.RequestException as e:
            print(f"   ❌ VPN 키 할당 API 호출 실패: {e}")
            return None
        except Exception as e:
            print(f"   ❌ VPN 키 할당 중 오류: {e}")
            return None

    def release_key(self, public_key: str) -> bool:
        """
        VPN 키 반납하기

        Args:
            public_key: 할당받은 공개키

        Returns:
            성공 여부
        """
        try:
            url = f"{self.BASE_URL}/release"
            payload = {"public_key": public_key}

            print(f"   🔓 VPN 키 반납 중...")
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()

            data = response.json()

            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                print(f"   ❌ VPN 키 반납 실패: {error_msg}")
                return False

            print(f"   ✅ VPN 키 반납 완료")
            return True

        except requests.RequestException as e:
            print(f"   ❌ VPN 키 반납 API 호출 실패: {e}")
            return False
        except Exception as e:
            print(f"   ❌ VPN 키 반납 중 오류: {e}")
            return False

    def get_status(self, server_ip: Optional[str] = None) -> Optional[Dict]:
        """
        VPN 키 사용 현황 조회

        Args:
            server_ip: 특정 서버 IP (None이면 전체 조회)

        Returns:
            {
                'success': True,
                'statistics': {
                    'total_keys': 10,
                    'keys_in_use': 3,
                    'keys_available': 7
                },
                'active_connections': [...]
            }
        """
        try:
            url = f"{self.BASE_URL}/status"
            params = {}
            if server_ip:
                params['ip'] = server_ip

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return data if data.get('success') else None

        except requests.RequestException as e:
            print(f"   ❌ VPN 상태 조회 API 호출 실패: {e}")
            return None
        except Exception as e:
            print(f"   ❌ VPN 상태 조회 중 오류: {e}")
            return None

    def get_server_list(self) -> Optional[list]:
        """
        VPN 서버 목록 조회

        Returns:
            ['111.222.333.444', '112.161.221.82', ...] 또는 None
        """
        try:
            url = f"{self.BASE_URL}/list"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            if not data.get('success'):
                print(f"   ❌ VPN 서버 목록 조회 실패")
                return None

            return data.get('servers', [])

        except requests.RequestException as e:
            print(f"   ❌ VPN 서버 목록 API 호출 실패: {e}")
            return None
        except Exception as e:
            print(f"   ❌ VPN 서버 목록 조회 중 오류: {e}")
            return None


class VPNConnection:
    """
    VPN 연결 관리 클래스 (WireGuard)
    키 할당 → WireGuard 연결 → 키 반납을 한번에 처리
    """

    def __init__(self, worker_id: int, vpn_client: VPNAPIClient):
        """
        Args:
            worker_id: 워커 ID
            vpn_client: VPN API 클라이언트
        """
        self.worker_id = worker_id
        self.vpn_client = vpn_client
        self.interface_name = f"wg-worker-{worker_id}"
        self.config_path = None
        self.vpn_key_data = None

    def connect(self, server_ip: Optional[str] = None) -> bool:
        """
        VPN 연결 (키 할당 + WireGuard 시작)

        Args:
            server_ip: 특정 VPN 서버 IP (None이면 자동)

        Returns:
            성공 여부
        """
        try:
            # 1. VPN 키 할당
            self.vpn_key_data = self.vpn_client.allocate_key(server_ip)
            if not self.vpn_key_data:
                return False

            # 2. WireGuard 설정 파일 생성 (정책 라우팅 적용)
            config_content = self.vpn_key_data['config']

            # ⚠️ 정책 라우팅 설정: 메인 이더넷 우선순위 보존
            # Table = off: 메인 라우팅 테이블에 route를 추가하지 않음
            # PostUp: worker_id에 해당하는 정책 라우팅 테이블에만 default route 추가

            # 라우팅 테이블 번호 계산 (200~211)
            table_num = 199 + self.worker_id

            # Gateway 계산 (내부 IP 대역의 .1)
            # 예: 10.8.0.14/24 → 10.8.0.1
            internal_ip = self.vpn_key_data['internal_ip']
            gateway = '.'.join(internal_ip.split('.')[:3]) + '.1'

            # WireGuard 설정 수정
            config_lines = config_content.split('\n')
            modified_lines = []

            for line in config_lines:
                modified_lines.append(line)
                # [Interface] 섹션 다음에 DNS 및 정책 라우팅 설정 추가
                if line.strip() == '[Interface]':
                    modified_lines.append('DNS = 8.8.8.8, 8.8.4.4')
                    modified_lines.append(f'# VPN 키 풀 정책 라우팅 (UID {2000 + self.worker_id} → 테이블 {table_num})')
                    modified_lines.append('Table = off')
                    modified_lines.append(f'PostUp = ip route add default via {gateway} dev %i table {table_num}')
                    # DNS 설정 (resolvectl 사용)
                    modified_lines.append('PostUp = resolvectl dns %i 8.8.8.8 8.8.4.4')
                    modified_lines.append('PostUp = resolvectl domain %i \\~.')
                    modified_lines.append(f'PostDown = ip route del default table {table_num} 2>/dev/null || true')
                    modified_lines.append('PostDown = resolvectl revert %i || true')

            config_content = '\n'.join(modified_lines)

            # /tmp/vpn_configs 디렉토리 생성
            config_dir = Path("/tmp/vpn_configs")
            config_dir.mkdir(parents=True, exist_ok=True)

            self.config_path = config_dir / f"{self.interface_name}.conf"

            with open(self.config_path, 'w') as f:
                f.write(config_content)

            os.chmod(self.config_path, 0o600)  # 보안을 위해 600 권한 설정

            print(f"   📝 WireGuard 설정 파일 생성: {self.config_path}")
            print(f"      ✓ Table = off (메인 라우팅 테이블 보존)")
            print(f"      ✓ 정책 라우팅: UID {2000 + self.worker_id} → 테이블 {table_num}")

            # 3. WireGuard 연결
            print(f"   🔌 WireGuard 연결 중 ({self.interface_name})...")
            result = subprocess.run(
                ['sudo', 'wg-quick', 'up', str(self.config_path)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"   ❌ WireGuard 연결 실패:")
                print(f"      {result.stderr}")
                # 연결 실패 시 키 반납
                self.vpn_client.release_key(self.vpn_key_data['public_key'])
                return False

            print(f"   ✅ VPN 연결 완료 ({self.vpn_key_data['internal_ip']})")
            return True

        except Exception as e:
            print(f"   ❌ VPN 연결 중 오류: {e}")
            # 오류 발생 시 키 반납 시도
            if self.vpn_key_data:
                self.vpn_client.release_key(self.vpn_key_data['public_key'])
            return False

    def disconnect(self) -> bool:
        """
        VPN 연결 해제 (WireGuard 종료 + 키 반납)

        Returns:
            성공 여부
        """
        success = True

        try:
            # 1. WireGuard 종료
            if self.config_path and self.config_path.exists():
                print(f"   🔌 WireGuard 연결 해제 중 ({self.interface_name})...")
                result = subprocess.run(
                    ['sudo', 'wg-quick', 'down', str(self.config_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    print(f"   ⚠️  WireGuard 종료 실패 (계속 진행):")
                    print(f"      {result.stderr}")
                    success = False
                else:
                    print(f"   ✅ WireGuard 연결 해제 완료")

                # 설정 파일 삭제
                try:
                    self.config_path.unlink()
                except Exception as e:
                    print(f"   ⚠️  설정 파일 삭제 실패: {e}")

        except Exception as e:
            print(f"   ❌ WireGuard 종료 중 오류: {e}")
            success = False

        # 2. VPN 키 반납 (WireGuard 종료 실패해도 키는 반납)
        if self.vpn_key_data:
            if not self.vpn_client.release_key(self.vpn_key_data['public_key']):
                success = False

        return success

    def get_internal_ip(self) -> Optional[str]:
        """할당받은 VPN 내부 IP 주소 반환"""
        if self.vpn_key_data:
            return self.vpn_key_data.get('internal_ip')
        return None


if __name__ == "__main__":
    # 테스트
    print("🔍 VPN 키 풀 API 테스트\n")

    client = VPNAPIClient()

    # 1. 서버 목록 조회
    print("1️⃣  VPN 서버 목록 조회:")
    servers = client.get_server_list()
    if servers:
        print(f"   총 {len(servers)}개 서버")
        for i, server in enumerate(servers[:3], 1):
            print(f"   {i}. {server}")
    print()

    # 2. 상태 조회
    print("2️⃣  VPN 키 사용 현황 조회:")
    status = client.get_status()
    if status:
        stats = status.get('statistics', {})
        print(f"   전체 키: {stats.get('total_keys')}")
        print(f"   사용 중: {stats.get('keys_in_use')}")
        print(f"   사용 가능: {stats.get('keys_available')}")
    print()

    # 3. 키 할당 테스트
    print("3️⃣  VPN 키 할당 테스트:")
    vpn_key = client.allocate_key()
    if vpn_key:
        print(f"   할당 성공!")
        print(f"   Public Key: {vpn_key['public_key'][:20]}...")

        # 4. 키 반납 테스트
        print("\n4️⃣  VPN 키 반납 테스트:")
        if client.release_key(vpn_key['public_key']):
            print(f"   반납 성공!")
