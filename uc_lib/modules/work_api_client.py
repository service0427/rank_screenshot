#!/usr/bin/env python3
"""
작업 API 클라이언트
스크린샷 작업 할당 및 결과 제출
"""

import requests
import time
import os
from typing import Optional, Dict, Any
from common.constants import Config


class WorkAPIClient:
    """작업 API 통신 클라이언트"""

    def __init__(
        self,
        allocate_url: str = None,
        result_url: str = None,
        timeout: int = 60
    ):
        """
        Args:
            allocate_url: 작업 할당 API URL (None이면 Config.WORK_ALLOCATE_URL 사용)
            result_url: 작업 결과 제출 API URL (None이면 Config.WORK_RESULT_URL 사용)
            timeout: 요청 타임아웃 (초)
        """
        self.allocate_url = allocate_url or Config.WORK_ALLOCATE_URL
        self.result_url = result_url or Config.WORK_RESULT_URL
        self.timeout = timeout

        # VPN 환경 확인 (정보성 메시지)
        # API 서버 IP는 VPN 라우팅에서 제외되어 자동으로 로컬 네트워크 사용
        self.is_vpn_env = os.environ.get('VPN_EXECUTED') is not None
        if self.is_vpn_env:
            print(f"🌐 VPN 환경 감지 - API 요청은 로컬 네트워크로 자동 라우팅")

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

            # API 요청 (VPN 환경에서도 IP 라우팅 규칙으로 자동 로컬 네트워크 사용)
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
        filename: str = None,
        match_product_id: bool = False,
        match_item_id: bool = False,
        match_vendor_item_id: bool = False
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
            match_product_id: product_id 일치 여부 (boolean)
            match_item_id: item_id 일치 여부 (boolean)
            match_vendor_item_id: vendor_item_id 일치 여부 (boolean)

        Returns:
            성공 여부
        """
        try:
            print(f"\n📤 작업 결과 제출:")
            print(f"   - 작업 ID: {screenshot_id}")
            print(f"   - 스크린샷 URL: {screenshot_url}")
            if rank:
                print(f"   - 순위: {rank}위")

            # 매칭 필드 표시 (✓/✗ 형태)
            if match_product_id or match_item_id or match_vendor_item_id:
                match_symbols = []
                if match_product_id:
                    match_symbols.append("product_id=✓")
                if match_item_id:
                    match_symbols.append("item_id=✓")
                if match_vendor_item_id:
                    match_symbols.append("vendor_item_id=✓")
                print(f"   - 매칭 필드: {', '.join(match_symbols)}")

            payload = {
                "id": screenshot_id,
                "screenshot_url": screenshot_url,
                "keyword": keyword,
                "rank": rank,
                "product_id": product_id,
                "item_id": item_id,
                "vendor_item_id": vendor_item_id,
                "filename": filename,
                "match_product_id": match_product_id,
                "match_item_id": match_item_id,
                "match_vendor_item_id": match_vendor_item_id
            }

            # 요청 시작 시간 측정
            start_time = time.time()

            # API 요청 (VPN 환경에서도 IP 라우팅 규칙으로 자동 로컬 네트워크 사용)
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
