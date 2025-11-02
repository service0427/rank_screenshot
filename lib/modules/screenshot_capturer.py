#!/usr/bin/env python3
"""
스크린샷 캡처 모듈
브라우저 페이지 스크린샷을 캡처하고 저장하는 기능 제공
"""

import os
import time
from pathlib import Path
from typing import Optional
from datetime import datetime


class ScreenshotCapturer:
    """스크린샷 캡처 및 저장을 담당하는 클래스"""

    def __init__(self, driver, base_dir: str = "screenshots"):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
            base_dir: 스크린샷 저장 기본 디렉토리 (기본: "screenshots")
        """
        self.driver = driver
        self.base_dir = Path(base_dir)

    def capture(
        self,
        keyword: str = "",
        version: str = "",
        full_page: bool = False,
        product_id: str = "",
        item_id: str = "",
        vendor_item_id: str = ""
    ) -> Optional[str]:
        """
        현재 페이지 스크린샷 캡처

        Args:
            keyword: 검색 키워드 (파일명에 포함)
            version: Chrome 버전 (사용 안 함 - 하위 호환성 유지)
            full_page: 전체 페이지 캡처 여부 (기본: False, viewport만)
            product_id: 상품 ID (파일명에 포함)
            item_id: 아이템 ID (파일명에 포함)
            vendor_item_id: 판매자 아이템 ID (파일명에 포함)

        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        if not self.driver:
            print("   ⚠️  No active driver for screenshot")
            return None

        try:
            # 저장 경로 생성
            filepath = self._generate_filepath(keyword, product_id, item_id, vendor_item_id)

            # 스크린샷 캡처
            if full_page:
                self._capture_full_page(filepath)
            else:
                self._capture_viewport(filepath)

            # 파일 크기 확인
            file_size = filepath.stat().st_size / 1024  # KB

            print(f"📸 Screenshot saved:")
            print(f"   Path: {filepath}")
            print(f"   Size: {file_size:.2f} KB")

            return str(filepath)

        except Exception as e:
            print(f"   ⚠️  Screenshot failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_filepath(
        self,
        keyword: str,
        product_id: str,
        item_id: str,
        vendor_item_id: str
    ) -> Path:
        """
        스크린샷 파일 경로 생성

        경로 구조: screenshots/YYYY/MM/DD/HH-MM-SS_{keyword}_{product_id}_{item_id}_{vendor_item_id}.png

        Args:
            keyword: 검색 키워드
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID

        Returns:
            저장할 파일 경로
        """
        # 현재 날짜/시간
        now = datetime.now()

        # 월별 폴더 밑에 일별 폴더 생성
        # screenshots/YYYY/MM/DD/
        year_month_day_dir = self.base_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")

        # 디렉토리 생성
        year_month_day_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성: His_{keyword}_{product_id}_{item_id}_{vendor_item_id}.png
        time_str = now.strftime("%H%M%S")

        # 키워드 정리 (파일명에 사용 불가능한 문자 제거)
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_keyword:
            safe_keyword = "unknown"

        # 상품 정보가 없으면 "none"으로 표시
        safe_product_id = product_id if product_id else "none"
        safe_item_id = item_id if item_id else "none"
        safe_vendor_item_id = vendor_item_id if vendor_item_id else "none"

        filename = f"{time_str}_{safe_keyword}_{safe_product_id}_{safe_item_id}_{safe_vendor_item_id}.png"
        return year_month_day_dir / filename

    def _capture_viewport(self, filepath: Path):
        """
        현재 Viewport만 캡처

        Args:
            filepath: 저장할 파일 경로
        """
        self.driver.save_screenshot(str(filepath))

    def _capture_full_page(self, filepath: Path):
        """
        전체 페이지 캡처 (스크롤 포함)

        Args:
            filepath: 저장할 파일 경로
        """
        # 페이지 전체 높이 가져오기
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")

        # 원본 창 크기 저장
        original_size = self.driver.get_window_size()

        try:
            # 전체 페이지를 담을 수 있도록 창 크기 조절
            self.driver.set_window_size(original_size['width'], total_height)
            time.sleep(0.5)  # 렌더링 대기

            # 캡처
            self.driver.save_screenshot(str(filepath))

        finally:
            # 원래 크기로 복원
            self.driver.set_window_size(original_size['width'], original_size['height'])
