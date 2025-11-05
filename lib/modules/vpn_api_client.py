#!/usr/bin/env python3
"""
VPN API Client
VPN 서버 API 연동 클라이언트
"""

import requests
from typing import List


class VPNAPIClient:
    """
    VPN API 클라이언트

    API 엔드포인트: http://220.121.120.83/vpn_socks5/api/list.php
    응답 형식: ["IP1", "IP2", ...] (IP 리스트)
    """

    API_URL = "http://220.121.120.83/vpn_socks5/api/list.php"

    def __init__(self, timeout: int = 10):
        """
        Args:
            timeout: API 요청 타임아웃 (초)
        """
        self.timeout = timeout

    def fetch_vpn_ips(self) -> List[str]:
        """
        API에서 VPN IP 목록 가져오기

        Returns:
            VPN IP 문자열 리스트
            ["112.161.221.82", "211.198.89.191", ...]

        Raises:
            requests.RequestException: API 호출 실패 시
        """
        try:
            response = requests.get(self.API_URL, timeout=self.timeout)
            response.raise_for_status()

            vpn_ips = response.json()

            if not isinstance(vpn_ips, list):
                raise ValueError(f"Invalid API response format: {type(vpn_ips)}")

            return vpn_ips

        except requests.RequestException as e:
            print(f"❌ VPN API 호출 실패: {e}")
            raise
        except Exception as e:
            print(f"❌ VPN API 응답 파싱 실패: {e}")
            raise

    def get_vpn_list_with_local(self) -> List[str]:
        """
        VPN 목록을 가져오고 'L' (Local) 추가

        Returns:
            ['L', '0', '1', '2', ...] 형식의 리스트
            - 'L': Local (VPN 없이 직접 연결)
            - '0', '1', '2', ...: VPN 번호 (IP 배열 인덱스)
        """
        try:
            vpn_ips = self.fetch_vpn_ips()

            # ['L', '0', '1', '2', ...] 형식으로 변환
            vpn_list = ['L']  # Local 항상 포함
            vpn_list.extend([str(i) for i in range(len(vpn_ips))])

            return vpn_list

        except Exception as e:
            print(f"❌ VPN 목록 조회 실패: {e}")
            print("   ⚠️  Local 모드만 사용합니다")
            return ['L']


def get_vpn_list() -> List[str]:
    """
    VPN 목록 가져오기 (헬퍼 함수)

    Returns:
        ['L', '0', '1', '2', ...] 형식의 리스트
    """
    client = VPNAPIClient()
    return client.get_vpn_list_with_local()


if __name__ == "__main__":
    # 테스트
    print("🔍 VPN API 테스트\n")

    client = VPNAPIClient()

    print("VPN 목록 (Local 포함):")
    vpn_list = client.get_vpn_list_with_local()
    print(f"   총 {len(vpn_list)}개: {vpn_list[:10]}...")
