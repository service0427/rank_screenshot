#!/usr/bin/env python3
"""
Proxy API Client
프록시 서버 API 연동 클라이언트
"""

import requests
from typing import List, Dict, Optional


class ProxyAPIClient:
    """
    프록시 API 클라이언트

    API 엔드포인트: https://mkt.techb.kr/api/proxy/status
    """

    API_URL = "https://mkt.techb.kr/api/proxy/status"

    def __init__(self, timeout: int = 10):
        """
        Args:
            timeout: API 요청 타임아웃 (초)
        """
        self.timeout = timeout

    def fetch_proxies(self) -> List[Dict]:
        """
        API에서 프록시 목록 가져오기

        Returns:
            프록시 정보 리스트
            [
                {
                    "proxy": "112.161.54.7:10022",
                    "external_ip": "112.161.54.7",
                    "use_count": 0,
                    "remaining_work_seconds": "168"
                },
                ...
            ]

        Raises:
            requests.RequestException: API 호출 실패 시
        """
        try:
            response = requests.get(self.API_URL, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            if not data.get('success'):
                raise ValueError(f"API returned success=false: {data}")

            proxies = data.get('proxies', [])
            print(f"   ✓ API에서 {len(proxies)}개 프록시 조회 완료")

            return proxies

        except requests.Timeout:
            raise Exception(f"API 타임아웃 ({self.timeout}초): {self.API_URL}")
        except requests.RequestException as e:
            raise Exception(f"API 호출 실패: {e}")
        except ValueError as e:
            raise Exception(f"API 응답 파싱 실패: {e}")

    def select_best_proxy(self, proxies: List[Dict]) -> str:
        """
        remaining_work_seconds > 120인 프록시 중 랜덤 선택

        Args:
            proxies: fetch_proxies()로 가져온 프록시 목록

        Returns:
            프록시 주소 (IP:port 형식, 예: "112.161.54.7:10022")

        Raises:
            ValueError: 프록시 목록이 비어있거나 조건 만족하는 프록시가 없을 때
        """
        import random

        if not proxies:
            raise ValueError("사용 가능한 프록시가 없습니다")

        # remaining_work_seconds > 120인 프록시만 필터링
        valid_proxies = [
            p for p in proxies
            if int(p.get('remaining_work_seconds', 0)) > 120
        ]

        if not valid_proxies:
            raise ValueError("remaining_work_seconds > 120인 프록시가 없습니다")

        # 필터링된 프록시 중 랜덤 선택
        selected_proxy = random.choice(valid_proxies)
        proxy_address = selected_proxy.get('proxy')
        remaining_seconds = int(selected_proxy.get('remaining_work_seconds', 0))

        if not proxy_address:
            raise ValueError("프록시 주소가 없습니다")

        # 초를 분으로 변환
        remaining_minutes = remaining_seconds / 60

        print(f"   ✓ 프록시 랜덤 선택: {proxy_address} (남은 시간: {remaining_minutes:.1f}분) [{len(valid_proxies)}개 중 선택]")

        return proxy_address

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


def get_proxy_address(proxy_arg: str = None) -> Optional[str]:
    """
    프록시 주소 가져오기 (자동 선택 또는 수동 지정)

    Args:
        proxy_arg: --proxy 옵션 값 ('auto' 또는 'IP:port')

    Returns:
        프록시 주소 (IP:port 형식) 또는 None
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
