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

# VPN 연결 추적 모듈
from .vpn_connection_tracker import get_vpn_tracker

# 통합 이벤트 로거 import
try:
    from .unified_event_logger import log_event, EventType
    UNIFIED_LOGGER_AVAILABLE = True
except ImportError:
    UNIFIED_LOGGER_AVAILABLE = False


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
                'gateway': '10.8.0.1',  # 권장: API 서버에서 제공
                'config': '[Interface]\\nPrivateKey = ...'
            }
            실패 시 None

            Note: 'gateway' 필드가 없으면 internal_ip 기반 fallback 사용
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
        self.interface_name = None  # IP 할당 후 동적으로 설정됨
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

            # 2. 인터페이스 이름 생성 (워커 ID 기반)
            # Worker-1 → wg101, Worker-2 → wg102, ... (숫자 통일)
            # 같은 VPN 서버에 여러 워커가 연결 가능 (서버당 최대 10개 동시 접속)
            #
            # WireGuard 인터페이스 이름 제약: 영문자로 시작, 최대 15자
            # 예: worker_id 1 → wg101
            #     worker_id 5 → wg105
            #     worker_id 12 → wg112
            user_id = 100 + self.worker_id  # Worker-1 → 101, Worker-2 → 102, etc.
            self.interface_name = f"wg{user_id}"

            # 3. WireGuard 설정 파일 생성 (정책 라우팅 적용)
            config_content = self.vpn_key_data['config']

            # ⚠️ 정책 라우팅 설정: 메인 이더넷 우선순위 보존
            # Table = off: 메인 라우팅 테이블에 route를 추가하지 않음
            # PostUp: worker_id에 해당하는 정책 라우팅 테이블에만 default route 추가

            # UID/Table 설정
            # Worker-1 → wg101 (UID 1101) → Table 101
            # Worker-2 → wg102 (UID 1102) → Table 102
            # ...
            uid = 1000 + user_id    # 1101, 1102, ... (시스템 서비스 충돌 방지)
            table_num = user_id     # 101, 102, ... (라우팅 테이블)

            # Gateway 정보 가져오기
            # Option 1: API 응답에서 직접 가져오기 (권장)
            # Option 2: 없으면 내부 IP 대역의 .1로 fallback
            internal_ip = self.vpn_key_data['internal_ip']
            gateway = self.vpn_key_data.get('gateway')
            if not gateway:
                # Fallback: 내부 IP 대역의 .1 (예: 10.8.0.14 → 10.8.0.1)
                gateway = '.'.join(internal_ip.split('.')[:3]) + '.1'
                print(f"   ⚠️  API에 gateway 정보 없음, fallback 사용: {gateway}")

            # WireGuard 설정 수정
            config_lines = config_content.split('\n')
            modified_lines = []

            for line in config_lines:
                # 원본 설정의 DNS 줄은 제거 (중복 방지)
                if line.strip().startswith('DNS ='):
                    continue  # DNS 줄 건너뛰기

                modified_lines.append(line)

                # [Interface] 섹션 다음에 정책 라우팅 설정 추가
                if line.strip() == '[Interface]':
                    # Table = off를 가장 먼저 설정
                    modified_lines.append('Table = off')
                    modified_lines.append(f'# WireGuard 정책 라우팅 (wg{user_id} / UID {uid} → 테이블 {table_num})')

                    # PostUp: 커널이 자동으로 추가한 메인 테이블 경로 제거
                    # ⚠️  주석 처리 (2025-11-07): Table = off이면 메인 테이블에 경로가 추가되지 않으므로 불필요
                    # 이 명령이 여러 워커 동시 실행 시 ERR_NETWORK_CHANGED를 유발할 수 있음
                    # modified_lines.append(f'PostUp = ip route del {gateway.rsplit(".", 1)[0]}.0/24 dev %i 2>/dev/null || true')

                    # UID 기반 라우팅 규칙 추가 (중복 방지: 기존 규칙 먼저 삭제)
                    modified_lines.append(f'PostUp = ip rule del uidrange {uid}-{uid} table {table_num} 2>/dev/null || true')
                    modified_lines.append(f'PostUp = ip rule add uidrange {uid}-{uid} table {table_num} priority 10{table_num}')

                    # 정책 라우팅 테이블에 default route 추가
                    # WireGuard는 Point-to-Point이므로 "via gateway" 없이 인터페이스로 직접 라우팅
                    modified_lines.append(f'PostUp = ip route add default dev %i table {table_num}')

                    # DNS 설정 제거 (2025-11-07)
                    # ⚠️ resolvectl은 systemd-resolved 전역 이벤트를 발생시켜
                    # 8개 워커 동시 실행 시 Chrome이 ERR_NETWORK_CHANGED를 감지함
                    # UID 정책 라우팅으로 DNS 쿼리도 자동으로 VPN 경로를 타므로 불필요
                    # modified_lines.append('PostUp = resolvectl dns %i 8.8.8.8 8.8.4.4')
                    # modified_lines.append('PostUp = resolvectl domain %i \\~.')

                    # PostDown: 정리
                    modified_lines.append(f'PostDown = ip rule del uidrange {uid}-{uid} table {table_num} 2>/dev/null || true')
                    modified_lines.append(f'PostDown = ip route del default table {table_num} 2>/dev/null || true')
                    # modified_lines.append('PostDown = resolvectl revert %i || true')

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
            print(f"      ✓ 정책 라우팅: wg{user_id} (UID {uid}) → 테이블 {table_num}")

            # 3. WireGuard 연결
            print(f"   🔌 WireGuard 연결 중 ({self.interface_name})...")

            # 통합 로거에 연결 시작 이벤트 기록 (비활성화: sticky bit 권한 문제)
            # if UNIFIED_LOGGER_AVAILABLE:
            #     try:
            #         log_event(
            #             worker_id=f"Worker-{self.worker_id}",
            #             event_type=EventType.VPN_CONNECTING,
            #             interface=self.interface_name,
            #             details={
            #                 'server_ip': self.vpn_key_data.get('server_ip'),
            #                 'internal_ip': internal_ip
            #             }
            #         )
            #     except Exception as e:
            #         print(f"   ⚠️  통합 로거 기록 실패 (VPN_CONNECTING): {e}")

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

            # 통합 로거에 연결 완료 이벤트 기록 (비활성화: sticky bit 권한 문제)
            # if UNIFIED_LOGGER_AVAILABLE:
            #     try:
            #         log_event(
            #             worker_id=f"Worker-{self.worker_id}",
            #             event_type=EventType.VPN_CONNECTED,
            #             interface=self.interface_name,
            #             details={
            #                 'server_ip': self.vpn_key_data.get('server_ip'),
            #                 'internal_ip': self.vpn_key_data['internal_ip']
            #             }
            #         )
            #     except Exception as e:
            #         print(f"   ⚠️  통합 로거 기록 실패 (VPN_CONNECTED): {e}")

            # VPN 연결 추적 등록
            tracker = get_vpn_tracker()
            tracker.register_connection(
                worker_id=self.worker_id,
                interface=self.interface_name,
                internal_ip=self.vpn_key_data['internal_ip'],
                server_ip=self.vpn_key_data.get('server_ip'),
                config_path=str(self.config_path),
                public_key=self.vpn_key_data.get('public_key')
            )

            # 네트워크 안정화 대기 (ERR_NETWORK_CHANGED 방지)
            # 2025-11-07: RESULT.md 해결책 적용
            # wg up → ping 2~3회 → 0.5초 정적 구간 → Chrome 실행
            import time
            test_ip = "8.8.8.8"  # Google DNS
            max_attempts = 3

            for attempt in range(1, max_attempts + 1):
                # ping으로 외부 인터넷 연결 확인
                ping_result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', test_ip],
                    capture_output=True,
                    text=True,
                    timeout=3
                )

                if ping_result.returncode == 0:
                    if attempt < max_attempts:
                        # 성공해도 2~3회 ping 반복 (안정성 확인)
                        time.sleep(0.3)
                    continue
                else:
                    if attempt < max_attempts:
                        print(f"   ⏳ 네트워크 안정화 대기 중... ({attempt}/{max_attempts})")
                        time.sleep(1)
                    else:
                        print(f"   ⚠️  인터넷 연결 확인 실패 (계속 진행)")
                        break

            # 모든 ping 성공 후 정적 구간 대기
            # 라우팅 규칙 전파 완료 + netlink 이벤트 안정화
            print(f"   ✓ 네트워크 안정화 완료 (ping {max_attempts}회 성공)")
            time.sleep(0.5)  # 추가 안정화 대기

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

                # 통합 로거에 해제 시작 이벤트 기록 (비활성화: sticky bit 권한 문제)
                # if UNIFIED_LOGGER_AVAILABLE:
                #     try:
                #         log_event(
                #             worker_id=f"Worker-{self.worker_id}",
                #             event_type=EventType.VPN_DISCONNECTING,
                #             interface=self.interface_name,
                #             details={}
                #         )
                #     except Exception as e:
                #         print(f"   ⚠️  통합 로거 기록 실패 (VPN_DISCONNECTING): {e}")

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

                    # 통합 로거에 해제 완료 이벤트 기록 (비활성화: sticky bit 권한 문제)
                    # if UNIFIED_LOGGER_AVAILABLE:
                    #     try:
                    #         log_event(
                    #             worker_id=f"Worker-{self.worker_id}",
                    #             event_type=EventType.VPN_DISCONNECTED,
                    #             interface=self.interface_name,
                    #             details={}
                    #         )
                    #     except Exception as e:
                    #         print(f"   ⚠️  통합 로거 기록 실패 (VPN_DISCONNECTED): {e}")

                # 설정 파일 삭제
                try:
                    self.config_path.unlink()
                except Exception as e:
                    print(f"   ⚠️  설정 파일 삭제 실패: {e}")

        except Exception as e:
            print(f"   ❌ WireGuard 종료 중 오류: {e}")
            success = False

        # 메인 라우팅 보호: VPN 종료 후 메인 라우팅 확인
        try:
            main_gateway = "121.172.70.254"
            check_route = subprocess.run(
                ['ip', 'route', 'show'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if f"default via {main_gateway}" not in check_route.stdout:
                print(f"   ⚠️  메인 라우팅 없음 - 복구 시도")
                # 메인 라우팅 복구
                subprocess.run(
                    ['sudo', 'ip', 'route', 'add', 'default', 'via', main_gateway, 'dev', 'enp4s0'],
                    capture_output=True,
                    timeout=5
                )
                print(f"   ✓ 메인 라우팅 복구 완료")
        except Exception as e:
            print(f"   ⚠️  메인 라우팅 확인 실패: {e}")

        # 2. VPN 키 반납 (WireGuard 종료 실패해도 키는 반납)
        if self.vpn_key_data:
            if not self.vpn_client.release_key(self.vpn_key_data['public_key']):
                success = False

        # 3. VPN 연결 추적 해제
        tracker = get_vpn_tracker()
        tracker.unregister_connection(worker_id=self.worker_id)

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
