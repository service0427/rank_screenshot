#!/usr/bin/env python3
"""
스크린샷 처리 모듈
스크린샷 캡처, 오버레이, 업로드를 통합 관리
"""

from pathlib import Path
from typing import Optional, Dict, Any
from .screenshot_capturer import ScreenshotCapturer
from .screenshot_uploader import ScreenshotUploader
from .image_overlay import ImageOverlay


class ScreenshotProcessor:
    """스크린샷 캡처, 오버레이, 업로드를 통합 처리하는 클래스"""

    def __init__(
        self,
        driver,
        base_dir: str = "screenshots",
        upload_url: Optional[str] = None,
        enable_upload: bool = True
    ):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
            base_dir: 스크린샷 저장 디렉토리
            upload_url: 업로드 서버 URL (None이면 업로드 비활성화)
            enable_upload: 업로드 기능 활성화 여부
        """
        self.driver = driver
        self.capturer = ScreenshotCapturer(driver, base_dir=base_dir)
        self.overlay = ImageOverlay(font_size=40)

        # 업로드 설정
        self.enable_upload = enable_upload and upload_url is not None
        if self.enable_upload:
            self.uploader = ScreenshotUploader(
                upload_url=upload_url,
                max_retries=3,
                retry_delay=1.0,
                timeout=30
            )
        else:
            self.uploader = None

    def capture_with_overlay(
        self,
        keyword: str,
        version: str,
        overlay_text: str,
        full_page: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """
        스크린샷 캡처 + 오버레이 + 업로드를 한번에 처리

        Args:
            keyword: 파일명에 사용할 키워드
            version: Chrome 버전 (디렉토리 구분용)
            overlay_text: 이미지에 추가할 텍스트 (예: "매칭 조건: product_id 일치")
            full_page: 전체 페이지 캡처 여부
            metadata: 업로드 시 함께 전송할 메타데이터

        Returns:
            (local_path, uploaded_url) 튜플
            - local_path: 로컬에 저장된 스크린샷 경로
            - uploaded_url: 업로드된 URL (업로드 실패 시 None)
        """
        # 1. 스크린샷 캡처
        # metadata에서 상품 정보 추출
        product_id = metadata.get('product_id', '') if metadata else ''
        item_id = metadata.get('item_id', '') if metadata else ''
        vendor_item_id = metadata.get('vendor_item_id', '') if metadata else ''

        screenshot_path = self.capturer.capture(
            keyword=keyword,
            version=version,
            full_page=full_page,
            product_id=product_id,
            item_id=item_id,
            vendor_item_id=vendor_item_id
        )

        if not screenshot_path:
            print(f"⚠️  스크린샷 캡처 실패")
            return (None, None)

        print(f"✅ 스크린샷 캡처 완료")

        # 2. 오버레이 추가
        if overlay_text:
            success = self.overlay.add_text_overlay(
                image_path=screenshot_path,
                text=f"🎯 {overlay_text}",
                position="top-center",
                text_color=(255, 255, 0),
                bg_color=(0, 0, 0, 180)
            )

            if success:
                print(f"✅ 매칭 조건을 이미지에 추가: {overlay_text}")
            else:
                print(f"⚠️  오버레이 추가 실패")

        # 3. 업로드 (활성화된 경우)
        uploaded_url = None
        if self.enable_upload and self.uploader:
            print("\n" + "=" * 60)
            print("📤 스크린샷 업로드")
            print("=" * 60 + "\n")

            upload_result = self.uploader.upload(screenshot_path, metadata)

            if upload_result["success"]:
                # 서버 응답에서 path 추출
                server_response = upload_result.get("server_response", {})
                path = server_response.get("path")

                if path:
                    uploaded_url = path  # 서버에서 받은 path를 그대로 사용

                    print(f"\n✅ 스크린샷 업로드 완료")
                    print(f"   파일 경로: {uploaded_url}\n")
                else:
                    print(f"\n⚠️  스크린샷 업로드 성공했으나 path를 받지 못함")
            else:
                print(f"\n⚠️  스크린샷 업로드 실패: {upload_result['error']}")
                print(f"   파일은 로컬에 저장되어 있습니다: {screenshot_path}\n")

        return (screenshot_path, uploaded_url)

    def capture_before_after(
        self,
        keyword: str,
        version: str,
        overlay_text: str,
        product_info: Dict[str, Any],
        product_finder
    ) -> tuple:
        """
        변경 전/후 스크린샷을 캡처하고 업로드

        Args:
            keyword: 검색 키워드
            version: Chrome 버전
            overlay_text: 매칭 조건 텍스트
            product_info: 상품 정보 딕셔너리
            product_finder: ProductFinder 인스턴스 (스크롤용)

        Returns:
            (before_path, after_path) 튜플
        """
        # URL 파라미터 추출 (메타데이터용)
        url_params = product_finder.extract_url_params(product_info.get('link', ''))

        # 메타데이터 준비
        metadata = {
            'keyword': keyword,
            'product_id': url_params['product_id'],
            'item_id': url_params['item_id'],
            'vendor_item_id': url_params['vendor_item_id'],
            'rank': str(product_info.get('rank', 'unknown'))
        }

        # === 변경 전 스크린샷 ===
        print("\n" + "=" * 60)
        print(f"📸 [변경 전] 상품 캡처 ({product_info['rank']}등)")
        print("=" * 60 + "\n")

        # 상품을 화면 중앙에 배치
        product_finder.scroll_to_center(product_info)

        # 캡처 + 오버레이 + 업로드
        before_path = self.capture_with_overlay(
            keyword=f"{keyword}_before_viewport",
            version=version,
            overlay_text=overlay_text,
            full_page=False,
            metadata=metadata
        )

        # === 변경 후 스크린샷 (순위 변조가 있을 경우) ===
        # (이 부분은 caller에서 처리)

        return before_path, None

    def capture_after(
        self,
        keyword: str,
        version: str,
        overlay_text: str,
        product_info: Dict[str, Any],
        product_finder
    ) -> Optional[str]:
        """
        변경 후 스크린샷 캡처

        Args:
            keyword: 검색 키워드
            version: Chrome 버전
            overlay_text: 매칭 조건 텍스트
            product_info: 상품 정보
            product_finder: ProductFinder 인스턴스

        Returns:
            저장된 스크린샷 경로
        """
        print("\n" + "=" * 60)
        print(f"📸 [변경 후] 상품 캡처")
        print("=" * 60 + "\n")

        # URL 파라미터 추출
        url_params = product_finder.extract_url_params(product_info.get('link', ''))

        # 메타데이터 준비
        metadata = {
            'keyword': keyword,
            'product_id': url_params['product_id'],
            'item_id': url_params['item_id'],
            'vendor_item_id': url_params['vendor_item_id'],
            'rank': str(product_info.get('rank', 'unknown'))
        }

        # 캡처 + 오버레이 + 업로드
        after_path = self.capture_with_overlay(
            keyword=f"{keyword}_after_viewport",
            version=version,
            overlay_text=overlay_text,
            full_page=False,
            metadata=metadata
        )

        return after_path
