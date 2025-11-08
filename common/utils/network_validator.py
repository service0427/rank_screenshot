#!/usr/bin/env python3
"""
네트워크 연결 검증 유틸리티
VPN/Proxy 사용 시 실제 IP가 올바르게 적용되었는지 확인
"""

import requests
import time
from typing import Optional, Dict


def verify_public_ip(expected_ip: Optional[str] = None, proxy_address: Optional[str] = None, timeout: int = 10) -> Dict[str, any]:
    """
    현재 공인 IP 확인 및 검증

    Args:
        expected_ip: 예상되는 IP 주소 (VPN/Proxy IP)
        proxy_address: SOCKS5 프록시 주소 (예: "1.2.3.4:10000")
        timeout: 타임아웃 (초)

    Returns:
        {
            'success': bool,           # 검증 성공 여부
            'actual_ip': str,          # 실제 공인 IP
            'expected_ip': str,        # 예상 IP (있는 경우)
            'matched': bool,           # IP 일치 여부
            'error': str               # 에러 메시지 (실패 시)
        }
    """
    result = {
        'success': False,
        'actual_ip': None,
        'expected_ip': expected_ip,
        'matched': False,
        'error': None
    }

    try:
        # SOCKS5 프록시 설정
        proxies = None
        if proxy_address:
            proxies = {
                'http': f'socks5://{proxy_address}',
                'https': f'socks5://{proxy_address}'
            }

        # IP 확인 API 호출 (ipify.org 사용)
        response = requests.get(
            'https://api.ipify.org?format=json',
            proxies=proxies,
            timeout=timeout
        )

        if response.status_code == 200:
            data = response.json()
            actual_ip = data.get('ip')
            result['actual_ip'] = actual_ip
            result['success'] = True

            # 예상 IP와 비교 (제공된 경우)
            if expected_ip:
                result['matched'] = (actual_ip == expected_ip)
            else:
                # 예상 IP가 없으면 무조건 성공
                result['matched'] = True
        else:
            result['error'] = f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        result['error'] = f"IP 확인 타임아웃 ({timeout}초)"
    except requests.exceptions.ProxyError as e:
        result['error'] = f"프록시 연결 실패: {e}"
    except requests.exceptions.RequestException as e:
        result['error'] = f"네트워크 요청 실패: {e}"
    except Exception as e:
        result['error'] = f"알 수 없는 오류: {e}"

    return result


def verify_vpn_connection(vpn_number: int, vpn_client=None, timeout: int = 10) -> Dict[str, any]:
    """
    VPN 연결 상태 검증

    Args:
        vpn_number: VPN 번호 (0, 1, 2, ...)
        vpn_client: VPN API 클라이언트 (있으면 예상 IP 조회)
        timeout: 타임아웃 (초)

    Returns:
        verify_public_ip()와 동일한 형식
    """
    expected_ip = None

    # VPN API에서 예상 IP 조회
    if vpn_client:
        try:
            expected_ip = vpn_client.get_ip_by_vpn_number(vpn_number)
        except Exception as e:
            print(f"   ⚠️  VPN API 조회 실패: {e}")

    # 공인 IP 확인 (VPN은 프록시 없이 확인)
    return verify_public_ip(expected_ip=expected_ip, proxy_address=None, timeout=timeout)


def verify_proxy_connection(proxy_address: str, expected_ip: Optional[str] = None, timeout: int = 10) -> Dict[str, any]:
    """
    SOCKS5 프록시 연결 상태 검증

    Args:
        proxy_address: SOCKS5 프록시 주소 (예: "1.2.3.4:10000")
        expected_ip: 예상 IP (프록시 서버 IP)
        timeout: 타임아웃 (초)

    Returns:
        verify_public_ip()와 동일한 형식
    """
    return verify_public_ip(expected_ip=expected_ip, proxy_address=proxy_address, timeout=timeout)


def print_verification_result(result: Dict[str, any], mode: str = "Network"):
    """
    검증 결과를 콘솔에 출력

    Args:
        result: verify_*() 함수의 반환값
        mode: 출력 모드 ("VPN", "Proxy", "Network")
    """
    print(f"\n🔍 {mode} 연결 검증:")

    if result['success']:
        print(f"   ✓ 공인 IP: {result['actual_ip']}")

        if result['expected_ip']:
            if result['matched']:
                print(f"   ✅ IP 일치: {result['expected_ip']} (정상)")
            else:
                print(f"   ❌ IP 불일치!")
                print(f"      예상: {result['expected_ip']}")
                print(f"      실제: {result['actual_ip']}")
                print(f"   🚨 {mode} 연결이 제대로 적용되지 않았습니다!")
    else:
        print(f"   ❌ 연결 확인 실패: {result['error']}")
        print(f"   🚨 {mode} 연결이 작동하지 않습니다!")

    print()

    return result['success'] and result['matched']
