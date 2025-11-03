#!/usr/bin/env python3
"""
작업 API 클라이언트
스크린샷 작업 할당 및 결과 제출
"""

import requests
from typing import Optional, Dict, Any


class WorkAPIClient:
    """작업 API 통신 클라이언트"""

    def __init__(
        self,
        allocate_url: str = "http://61.84.75.37:3302/api/work/allocate-screenshot",
        result_url: str = "http://61.84.75.37:3302/api/work/screenshot-result",
        timeout: int = 30
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

    def allocate_work(self, work_id: int = None) -> Optional[Dict[str, Any]]:
        """
        스크린샷 작업 할당 요청

        Args:
            work_id: 지정된 작업 ID (None이면 자동 할당)

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
            # URL 구성 (work_id가 있으면 쿼리 파라미터로 추가)
            url = self.allocate_url
            params = {}
            if work_id is not None:
                params['id'] = work_id

            print(f"\n📥 작업 할당 요청: {url}")
            if work_id:
                print(f"   📌 지정 작업 ID: {work_id}")

            response = requests.get(
                url,
                params=params,
                timeout=self.timeout
            )

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

    def submit_result(self, work_id: int, screenshot_url: str) -> bool:
        """
        작업 결과 제출

        Args:
            work_id: 작업 ID
            screenshot_url: 업로드된 스크린샷 URL

        Returns:
            성공 여부
        """
        try:
            print(f"\n📤 작업 결과 제출:")
            print(f"   - 작업 ID: {work_id}")
            print(f"   - 스크린샷 URL: {screenshot_url}")

            payload = {
                "id": work_id,
                "screenshot_url": screenshot_url
            }

            response = requests.post(
                self.result_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )

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
