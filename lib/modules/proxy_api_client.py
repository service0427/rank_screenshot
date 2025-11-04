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

    API 엔드포인트: http://220.121.120.83/vpn_socks5/api/list.php?type=proxy
    SOCKS5 인증: techb:Tech1324
    응답 형식: ["IP1", "IP2", ...] (간소화된 IP 리스트)
    """

    API_URL = "http://220.121.120.83/vpn_socks5/api/list.php?type=proxy"
    SOCKS5_USERNAME = "techb"
    SOCKS5_PASSWORD = "Tech1324"

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

    def select_best_proxy(self, proxies: List[str]) -> str:
        """
        프록시 목록에서 랜덤 선택

        Args:
            proxies: fetch_proxies()로 가져온 프록시 IP 목록 (문자열 리스트)

        Returns:
            프록시 주소 (인증 정보 포함, 예: "techb:Tech1324@211.198.89.191:10000")

        Raises:
            ValueError: 프록시 목록이 비어있을 때
        """
        import random

        if not proxies:
            raise ValueError("사용 가능한 프록시가 없습니다")

        # 프록시 IP 중 랜덤 선택
        public_ip = random.choice(proxies)
        socks5_port = 10000  # 고정 포트

        # 인증 정보 포함한 프록시 주소 생성
        # 형식: "username:password@IP:port"
        proxy_address = f"{self.SOCKS5_USERNAME}:{self.SOCKS5_PASSWORD}@{public_ip}:{socks5_port}"

        print(f"   ✓ 프록시 랜덤 선택: {public_ip}:{socks5_port} [{len(proxies)}개 중 선택]")

        return proxy_address

    def validate_proxy_format(self, proxy_address: str) -> bool:
        """
        프록시 주소 형식 검증

        Args:
            proxy_address: 프록시 주소 (IP:port 또는 user:pass@IP:port 형식)

        Returns:
            유효 여부
        """
        if not proxy_address:
            return False

        # 인증 정보 포함 형식: user:pass@IP:port
        if '@' in proxy_address:
            auth_part, addr_part = proxy_address.split('@', 1)
            # auth_part 검증 생략 (user:pass 형식)
            proxy_address = addr_part

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


def get_proxy_address(proxy_arg: str = None) -> Optional[str]:
    """
    프록시 주소 가져오기 (자동 선택 또는 수동 지정)

    Args:
        proxy_arg: --proxy 옵션 값 ('auto' 또는 'IP:port')

    Returns:
        프록시 주소 (인증 정보 포함, 예: "techb:Tech1324@IP:10000") 또는 None
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

        # 인증 정보 없이 지정된 경우 자동 추가
        if '@' not in proxy_arg:
            proxy_arg = f"{client.SOCKS5_USERNAME}:{client.SOCKS5_PASSWORD}@{proxy_arg}"

        if not client.validate_proxy_format(proxy_arg):
            print(f"   ❌ 잘못된 프록시 형식: {proxy_arg} (올바른 형식: IP:port)")
            return None
        return proxy_arg
