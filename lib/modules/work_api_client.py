#!/usr/bin/env python3
"""
작업 API 클라이언트
스크린샷 작업 할당 및 결과 제출
"""

import requests
import time
import os
import subprocess
import json
from typing import Optional, Dict, Any


class WorkAPIClient:
    """작업 API 통신 클라이언트"""

    def __init__(
        self,
        allocate_url: str = "http://61.84.75.37:3302/api/work/allocate-screenshot",
        result_url: str = "http://61.84.75.37:3302/api/work/screenshot-result",
        timeout: int = 60
    ):
        """
        Args:
            allocate_url: 작업 할당 API URL
            result_url: 작업 결과 제출 API URL
            timeout: 요청 타임아웃 (초)
        """
        self.allocate_url = allocate_url
        self.result_url = result_url
        self.timeout = timeout

        # VPN 환경에서 실행 중인지 확인
        self.is_vpn_env = os.environ.get('VPN_EXECUTED') is not None
        if self.is_vpn_env:
            print(f"🌐 VPN 환경 감지 - API 요청은 로컬 네트워크 사용")

    def _request_via_local(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        VPN 환경에서 로컬 네트워크를 통해 API 요청 실행

        Args:
            method: HTTP 메서드 (GET, POST)
            url: 요청 URL
            **kwargs: requests 라이브러리 파라미터 (params, json, headers, timeout)

        Returns:
            Response 객체 또는 None
        """
        try:
            # Python 스크립트 생성 (로컬에서 실행할 코드)
            script = f"""
import requests
import sys
import json

try:
    response = requests.{method.lower()}(
        "{url}",
"""
            # params 추가
            if 'params' in kwargs and kwargs['params']:
                script += f"        params={kwargs['params']},\n"

            # json 추가
            if 'json' in kwargs:
                script += f"        json={json.dumps(kwargs['json'])},\n"

            # headers 추가
            if 'headers' in kwargs:
                script += f"        headers={kwargs['headers']},\n"

            # timeout 추가
            timeout = kwargs.get('timeout', self.timeout)
            script += f"        timeout={timeout}\n"
            script += """    )

    # 응답 정보를 JSON으로 출력
    result = {
        "status_code": response.status_code,
        "text": response.text,
        "headers": dict(response.headers)
    }
    print(json.dumps(result))
    sys.exit(0)

except Exception as e:
    error = {"error": str(e)}
    print(json.dumps(error))
    sys.exit(1)
"""

            # 원본 사용자 확인 (VPN 환경에서는 HOME 환경 변수에서 원본 사용자 추출)
            original_user = os.environ.get('HOME', '/home/tech').split('/')[-1]

            # subprocess로 원본 사용자로 Python 실행 (VPN 라우팅 완전 우회)
            cmd = ['sudo', '-u', original_user, 'python3', '-c', script]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5  # 여유 시간 추가
            )

            if result.returncode == 0:
                # 성공: 응답 파싱
                response_data = json.loads(result.stdout)

                # requests.Response 객체 재구성
                mock_response = requests.Response()
                mock_response.status_code = response_data['status_code']
                mock_response._content = response_data['text'].encode('utf-8')
                mock_response.headers.update(response_data['headers'])

                return mock_response
            else:
                # 실패
                print(f"❌ 로컬 네트워크 요청 실패: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print(f"⚠️  로컬 네트워크 요청 타임아웃")
            return None
        except Exception as e:
            print(f"❌ 로컬 네트워크 요청 중 오류: {e}")
            return None

    def allocate_work(self, screenshot_id: int = None) -> Optional[Dict[str, Any]]:
        """
        스크린샷 작업 할당 요청

        Args:
            screenshot_id: 지정된 작업 ID (None이면 자동 할당)

        Returns:
            성공 시 작업 정보 딕셔너리:
            {
                "success": True,
                "id": 4948534,
                "work_type": "screenshot",
                "site_code": "topr",
                "keyword": "사운드바",
                "product_id": "7227655664",
                "item_id": "18331882647",
                "vendor_item_id": "85810785808",
                "min_rank": 7
            }
            실패 시 None
        """
        try:
            # URL 구성 (screenshot_id가 있으면 쿼리 파라미터로 추가)
            url = self.allocate_url
            params = {}
            if screenshot_id is not None:
                params['id'] = screenshot_id

            print(f"\n📥 작업 할당 요청: {url}")
            if screenshot_id:
                print(f"   📌 지정 작업 ID: {screenshot_id}")

            # 요청 시작 시간 측정
            start_time = time.time()

            # VPN 환경이면 로컬 네트워크로 요청
            if self.is_vpn_env:
                print(f"   🔄 로컬 네트워크로 요청 우회 중...")
                response = self._request_via_local('GET', url, params=params, timeout=self.timeout)
                if response is None:
                    return None
            else:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

            # 응답 시간 측정
            elapsed = time.time() - start_time
            print(f"   ⏱️  응답 시간: {elapsed:.2f}초")

            if response.status_code == 200:
                data = response.json()

                if data.get("success"):
                    print(f"✅ 작업 할당 성공:")
                    print(f"   - ID: {data.get('id')}")
                    print(f"   - 작업 유형: {data.get('work_type')}")
                    print(f"   - 사이트: {data.get('site_code')}")
                    print(f"   - 키워드: {data.get('keyword')}")
                    print(f"   - 상품 ID: {data.get('product_id')}")
                    print(f"   - 아이템 ID: {data.get('item_id')}")
                    print(f"   - 판매자 아이템 ID: {data.get('vendor_item_id')}")
                    print(f"   - 최소 순위: {data.get('min_rank')}")
                    return data
                else:
                    print(f"⚠️  작업 할당 실패: {data.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"❌ 작업 할당 요청 실패: HTTP {response.status_code}")
                print(f"   응답: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            print(f"⚠️  작업 할당 요청 타임아웃 ({self.timeout}초)")
            return None
        except requests.exceptions.ConnectionError:
            print(f"❌ 작업 할당 서버 연결 실패: {self.allocate_url}")
            return None
        except Exception as e:
            print(f"❌ 작업 할당 중 오류: {e}")
            return None

    def submit_result(
        self,
        screenshot_id: int,
        screenshot_url: str,
        keyword: str = None,
        rank: int = None,
        product_id: str = None,
        item_id: str = None,
        vendor_item_id: str = None,
        filename: str = None
    ) -> bool:
        """
        작업 결과 제출

        Args:
            screenshot_id: 작업 ID
            screenshot_url: 업로드된 스크린샷 URL
            keyword: 검색 키워드
            rank: 발견된 순위 (전체 누적 순위)
            product_id: 상품 ID (매칭된 경우만, 아니면 None)
            item_id: 아이템 ID (매칭된 경우만, 아니면 None)
            vendor_item_id: 판매자 아이템 ID (매칭된 경우만, 아니면 None)
            filename: 스크린샷 파일명

        Returns:
            성공 여부
        """
        try:
            print(f"\n📤 작업 결과 제출:")
            print(f"   - 작업 ID: {screenshot_id}")
            print(f"   - 스크린샷 URL: {screenshot_url}")
            if rank:
                print(f"   - 순위: {rank}위")
            if product_id or item_id or vendor_item_id:
                print(f"   - 매칭 필드: product_id={product_id}, item_id={item_id}, vendor_item_id={vendor_item_id}")

            payload = {
                "id": screenshot_id,
                "screenshot_url": screenshot_url,
                "keyword": keyword,
                "rank": rank,
                "product_id": product_id,
                "item_id": item_id,
                "vendor_item_id": vendor_item_id,
                "filename": filename
            }

            # 요청 시작 시간 측정
            start_time = time.time()

            # VPN 환경이면 로컬 네트워크로 요청
            if self.is_vpn_env:
                print(f"   🔄 로컬 네트워크로 요청 우회 중...")
                response = self._request_via_local(
                    'POST',
                    self.result_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )
                if response is None:
                    return False
            else:
                response = requests.post(
                    self.result_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )

            # 응답 시간 측정
            elapsed = time.time() - start_time
            print(f"   ⏱️  응답 시간: {elapsed:.2f}초")

            if response.status_code == 200:
                data = response.json()

                if data.get("success"):
                    print(f"✅ 작업 결과 제출 성공")
                    return True
                else:
                    print(f"⚠️  작업 결과 제출 실패: {data.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"❌ 작업 결과 제출 실패: HTTP {response.status_code}")
                print(f"   응답: {response.text[:200]}")
                return False

        except requests.exceptions.Timeout:
            print(f"⚠️  작업 결과 제출 타임아웃 ({self.timeout}초)")
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ 작업 결과 서버 연결 실패: {self.result_url}")
            return False
        except Exception as e:
            print(f"❌ 작업 결과 제출 중 오류: {e}")
            return False
