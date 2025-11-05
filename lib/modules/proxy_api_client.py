#!/usr/bin/env python3
"""
Proxy API Client
프록시 서버 API 연동 클라이언트 (SOCKS5 인증 지원)
"""

import requests
from typing import List, Dict, Optional


class ProxyAPIClient:
    """
    프록시 API 클라이언트

    API 엔드포인트: http://techb.kr/vpn_socks5/api/list.php?type=proxy
    응답 형식: ["IP1", "IP2", ...] (IP 리스트, 인증 불필요)
    """

    API_URL = "http://techb.kr/vpn_socks5/api/list.php?type=proxy"
    SOCKS5_PORT = 10000  # 고정 포트

    def __init__(self, timeout: int = 10):
        """
        Args:
            timeout: API 요청 타임아웃 (초)
        """
        self.timeout = timeout

    def fetch_proxies(self) -> List[str]:
        """
        API에서 프록시 IP 목록 가져오기

        Returns:
            프록시 IP 문자열 리스트
            [
                "211.198.89.191",
                "175.210.218.228",
                ...
            ]

        Raises:
            requests.RequestException: API 호출 실패 시
        """
        try:
            response = requests.get(self.API_URL, timeout=self.timeout)
            response.raise_for_status()

            # API 응답: IP 문자열 리스트
            # 예: ["211.198.89.191", "175.210.218.228", ...]
            proxies = response.json()

            if not isinstance(proxies, list):
                raise ValueError(f"API 응답이 리스트가 아닙니다: {type(proxies)}")

            print(f"   ✓ API에서 {len(proxies)}개 프록시 조회 완료")

            return proxies

        except requests.Timeout:
            raise Exception(f"API 타임아웃 ({self.timeout}초): {self.API_URL}")
        except requests.RequestException as e:
            raise Exception(f"API 호출 실패: {e}")
        except ValueError as e:
            raise Exception(f"API 응답 파싱 실패: {e}")

    def test_proxy(self, proxy_address: str, timeout: int = 5) -> bool:
        """
        프록시 연결 테스트 (curl 명령 사용)

        Args:
            proxy_address: IP:port 형식
            timeout: 타임아웃 (초)

        Returns:
            연결 가능 여부
        """
        import subprocess

        try:
            # curl로 프록시 테스트 (빠르게 HEAD 요청)
            result = subprocess.run(
                ['curl', '--socks5', proxy_address, '--head', '--max-time', str(timeout), 'https://www.coupang.com'],
                capture_output=True,
                timeout=timeout + 1
            )
            # 200, 403 등 응답이 오면 프록시는 작동함 (0 = 성공, 22 = 4xx/5xx HTTP 에러)
            return result.returncode in [0, 22]
        except:
            return False

    def select_best_proxy(self, proxies: List[str], test_connection: bool = True, max_retries: int = 3) -> str:
        """
        프록시 목록에서 랜덤 선택 (연결 테스트 포함)

        Args:
            proxies: fetch_proxies()로 가져온 프록시 IP 목록 (문자열 리스트)
            test_connection: 연결 테스트 수행 여부 (기본 True)
            max_retries: 연결 실패 시 재시도 횟수

        Returns:
            프록시 주소 (IP:port 형식, 예: "211.198.89.191:10000")

        Raises:
            ValueError: 프록시 목록이 비어있거나 모든 프록시 연결 실패
        """
        import random

        if not proxies:
            raise ValueError("사용 가능한 프록시가 없습니다")

        tested_proxies = []
        for attempt in range(max_retries):
            # 이미 테스트한 프록시 제외
            available = [p for p in proxies if p not in tested_proxies]
            if not available:
                break

            public_ip = random.choice(available)
            proxy_address = f"{public_ip}:{self.SOCKS5_PORT}"
            tested_proxies.append(public_ip)

            print(f"   🔍 프록시 선택 시도 {attempt + 1}/{max_retries}: {proxy_address}")

            # 연결 테스트
            if test_connection:
                if self.test_proxy(proxy_address, timeout=3):
                    print(f"   ✅ 프록시 연결 성공: {proxy_address}")
                    return proxy_address
                else:
                    print(f"   ❌ 프록시 연결 실패: {proxy_address}")
            else:
                # 테스트 없이 선택
                print(f"   ✓ 프록시 선택 (테스트 생략): {proxy_address}")
                return proxy_address

        # 모든 시도 실패
        raise ValueError(f"{max_retries}번 시도했으나 작동하는 프록시를 찾지 못했습니다")

    def validate_proxy_format(self, proxy_address: str) -> bool:
        """
        프록시 주소 형식 검증

        Args:
            proxy_address: 프록시 주소 (IP:port 형식)

        Returns:
            유효 여부
        """
        if not proxy_address:
            return False

        parts = proxy_address.split(':')
        if len(parts) != 2:
            return False

        ip, port = parts

        # IP 형식 간단 검증
        ip_parts = ip.split('.')
        if len(ip_parts) != 4:
            return False

        try:
            for part in ip_parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
        except ValueError:
            return False

        # 포트 검증
        try:
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                return False
        except ValueError:
            return False

        return True

    def get_socks5_list_with_local(self) -> List[str]:
        """
        SOCKS5 목록을 가져오고 'L' (Local) 추가

        Returns:
            ['L', '0', '1', '2', ...] 형식의 리스트
            - 'L': Local (프록시 없이 직접 연결)
            - '0', '1', '2', ...: SOCKS5 번호 (IP 배열 인덱스)
        """
        try:
            proxies = self.fetch_proxies()

            # ['L', '0', '1', '2', ...] 형식으로 변환
            socks5_list = ['L']  # Local 항상 포함
            socks5_list.extend([str(i) for i in range(len(proxies))])

            return socks5_list

        except Exception as e:
            print(f"❌ SOCKS5 목록 조회 실패: {e}")
            print("   ⚠️  Local 모드만 사용합니다")
            return ['L']

    def get_ip_by_socks5_number(self, socks5_number: int) -> Optional[str]:
        """
        SOCKS5 번호로 IP 주소 조회

        Args:
            socks5_number: SOCKS5 번호 (0부터 시작하는 인덱스)

        Returns:
            IP 주소 또는 None (범위 초과 시)
        """
        try:
            proxies = self.fetch_proxies()

            if 0 <= socks5_number < len(proxies):
                return proxies[socks5_number]
            else:
                print(f"❌ SOCKS5 번호 {socks5_number}가 범위를 벗어났습니다 (최대: {len(proxies) - 1})")
                return None

        except Exception as e:
            print(f"❌ SOCKS5 IP 조회 실패: {e}")
            return None


def get_proxy_address(proxy_arg: str = None) -> Optional[str]:
    """
    프록시 주소 가져오기 (자동 선택 또는 수동 지정)

    Args:
        proxy_arg: --proxy 옵션 값 ('auto' 또는 'IP:port')

    Returns:
        프록시 주소 (IP:port 형식, 예: "211.198.89.191:10000") 또는 None
    """
    if not proxy_arg:
        return None

    if proxy_arg == 'auto':
        # API에서 자동 선택
        print("🌐 프록시 API에서 자동 선택 중...")
        try:
            client = ProxyAPIClient()
            proxies = client.fetch_proxies()
            proxy_address = client.select_best_proxy(proxies)
            return proxy_address
        except Exception as e:
            print(f"   ❌ 프록시 자동 선택 실패: {e}")
            return None
    else:
        # 수동 지정
        print(f"🌐 프록시 수동 지정: {proxy_arg}")
        client = ProxyAPIClient()

        if not client.validate_proxy_format(proxy_arg):
            print(f"   ❌ 잘못된 프록시 형식: {proxy_arg} (올바른 형식: IP:port)")
            return None
        return proxy_arg
