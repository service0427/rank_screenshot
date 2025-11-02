#!/usr/bin/env python3
"""
이미지 오버레이 모듈
스크린샷에 텍스트, 배지, 워터마크 등을 추가하는 기능 제공
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Optional, Tuple


class ImageOverlay:
    """스크린샷에 텍스트 오버레이를 추가하는 클래스"""

    # 한글 지원 폰트 경로 (우선순위 순)
    FONT_PATHS = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]

    def __init__(self, font_size: int = 40):
        """
        Args:
            font_size: 텍스트 폰트 크기 (기본: 40)
        """
        self.font_size = font_size
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """
        한글 지원 폰트 로드 (fallback 포함)

        Returns:
            로드된 폰트 객체
        """
        for font_path in self.FONT_PATHS:
            try:
                return ImageFont.truetype(font_path, self.font_size)
            except Exception:
                continue

        # Fallback: 기본 폰트
        return ImageFont.load_default()

    def add_text_overlay(
        self,
        image_path: str,
        text: str,
        position: str = "top-center",
        text_color: Tuple[int, int, int] = (255, 255, 0),
        bg_color: Tuple[int, int, int, int] = (0, 0, 0, 180),
        padding: int = 10,
        y_offset: int = 20
    ) -> bool:
        """
        이미지에 텍스트 오버레이 추가

        Args:
            image_path: 이미지 파일 경로
            text: 추가할 텍스트
            position: 텍스트 위치 ("top-center", "top-left", "top-right", "bottom-center")
            text_color: 텍스트 색상 RGB (기본: 노란색)
            bg_color: 배경 색상 RGBA (기본: 반투명 검정)
            padding: 배경 박스 패딩 (기본: 10px)
            y_offset: 상단/하단으로부터의 오프셋 (기본: 20px)

        Returns:
            성공 여부
        """
        try:
            # 이미지 열기
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)

            # 텍스트 크기 계산
            bbox = draw.textbbox((0, 0), text, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 이미지 크기
            img_width, img_height = img.size

            # 위치 계산
            if position == "top-center":
                x = (img_width - text_width) // 2
                y = y_offset
            elif position == "top-left":
                x = padding
                y = y_offset
            elif position == "top-right":
                x = img_width - text_width - padding
                y = y_offset
            elif position == "bottom-center":
                x = (img_width - text_width) // 2
                y = img_height - text_height - y_offset
            elif position == "bottom-left":
                x = padding
                y = img_height - text_height - y_offset
            elif position == "bottom-right":
                x = img_width - text_width - padding
                y = img_height - text_height - y_offset
            else:
                raise ValueError(f"Unknown position: {position}")

            # 배경 박스 그리기
            box_coords = [
                (x - padding, y - padding),
                (x + text_width + padding, y + text_height + padding)
            ]
            draw.rectangle(box_coords, fill=bg_color)

            # 텍스트 그리기
            draw.text((x, y), text, fill=text_color, font=self.font)

            # 이미지 저장 (덮어쓰기)
            img.save(image_path)

            return True

        except Exception as e:
            print(f"⚠️  이미지 오버레이 실패: {e}")
            return False

    def add_multiple_overlays(
        self,
        image_path: str,
        overlays: list
    ) -> bool:
        """
        여러 텍스트 오버레이를 한번에 추가

        Args:
            image_path: 이미지 파일 경로
            overlays: 오버레이 정보 리스트
                [
                    {
                        "text": "텍스트",
                        "position": "top-center",
                        "text_color": (255, 255, 0),
                        "bg_color": (0, 0, 0, 180)
                    },
                    ...
                ]

        Returns:
            성공 여부
        """
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)

            for overlay in overlays:
                text = overlay.get("text", "")
                position = overlay.get("position", "top-center")
                text_color = overlay.get("text_color", (255, 255, 0))
                bg_color = overlay.get("bg_color", (0, 0, 0, 180))
                padding = overlay.get("padding", 10)
                y_offset = overlay.get("y_offset", 20)

                # 텍스트 크기 계산
                bbox = draw.textbbox((0, 0), text, font=self.font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # 이미지 크기
                img_width, img_height = img.size

                # 위치 계산
                if position == "top-center":
                    x = (img_width - text_width) // 2
                    y = y_offset
                elif position == "bottom-center":
                    x = (img_width - text_width) // 2
                    y = img_height - text_height - y_offset
                else:
                    continue  # 지원하지 않는 위치는 스킵

                # 배경 박스
                box_coords = [
                    (x - padding, y - padding),
                    (x + text_width + padding, y + text_height + padding)
                ]
                draw.rectangle(box_coords, fill=bg_color)

                # 텍스트
                draw.text((x, y), text, fill=text_color, font=self.font)

            # 저장
            img.save(image_path)
            return True

        except Exception as e:
            print(f"⚠️  다중 오버레이 실패: {e}")
            return False
