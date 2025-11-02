#!/usr/bin/env python3
"""
영상 녹화 모듈
브라우저 자동화 과정을 영상으로 녹화하는 기능 제공
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional
from datetime import datetime
import time
from PIL import Image
import io


class VideoRecorder:
    """브라우저 자동화 과정을 영상으로 녹화하는 클래스"""

    def __init__(
        self,
        driver,
        base_dir: str = "videos",
        fps: int = 15,
        codec: str = "mp4v"
    ):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
            base_dir: 영상 저장 기본 디렉토리 (기본: "videos")
            fps: 초당 프레임 수 (기본: 15)
            codec: 비디오 코덱 (기본: "mp4v")
        """
        self.driver = driver
        self.base_dir = Path(base_dir)
        self.fps = fps
        self.codec = codec

        # 녹화 상태
        self.is_recording = False
        self.video_writer = None
        self.frames = []
        self.start_time = None
        self.output_path = None

    def start_recording(
        self,
        keyword: str = "",
        version: str = ""
    ) -> bool:
        """
        녹화 시작 (브라우저 화면 크기를 자동 감지)

        Args:
            keyword: 검색 키워드 (파일명에 포함)
            version: Chrome 버전 (디렉토리 구분용)

        Returns:
            녹화 시작 성공 여부
        """
        if self.is_recording:
            print("   ⚠️  이미 녹화 중입니다")
            return False

        try:
            # 첫 번째 스크린샷으로 실제 브라우저 크기 감지
            screenshot_png = self.driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot_png))
            width, height = image.size

            # 저장 경로 생성
            self.output_path = self._generate_filepath(keyword, version)

            # VideoWriter 초기화
            fourcc = cv2.VideoWriter_fourcc(*self.codec)
            self.video_writer = cv2.VideoWriter(
                str(self.output_path),
                fourcc,
                self.fps,
                (width, height)
            )

            if not self.video_writer.isOpened():
                print("   ❌ VideoWriter 초기화 실패")
                return False

            self.is_recording = True
            self.start_time = time.time()
            self.frames = []

            print(f"🎥 녹화 시작!")
            print(f"   파일: {self.output_path.name}")
            print(f"   해상도: {width}x{height}")
            print(f"   FPS: {self.fps}")

            return True

        except Exception as e:
            print(f"   ❌ 녹화 시작 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def capture_frame(self):
        """현재 브라우저 화면을 프레임으로 캡처"""
        if not self.is_recording:
            return

        try:
            # 브라우저 스크린샷 캡처 (PNG bytes)
            screenshot_png = self.driver.get_screenshot_as_png()

            # PIL Image로 변환
            image = Image.open(io.BytesIO(screenshot_png))

            # NumPy array로 변환 (OpenCV 형식)
            frame = np.array(image)

            # RGB -> BGR 변환 (OpenCV는 BGR 사용)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # 프레임 쓰기 (크기는 start_recording에서 설정한 크기와 동일해야 함)
            if self.video_writer:
                self.video_writer.write(frame)
                self.frames.append(frame)

        except Exception as e:
            print(f"   ⚠️  프레임 캡처 실패: {e}")

    def stop_recording(self) -> Optional[str]:
        """
        녹화 종료

        Returns:
            저장된 영상 파일 경로 (실패 시 None)
        """
        if not self.is_recording:
            print("   ⚠️  녹화 중이 아닙니다")
            return None

        try:
            # VideoWriter 해제
            if self.video_writer:
                self.video_writer.release()

            # 통계 계산
            duration = time.time() - self.start_time
            frame_count = len(self.frames)
            file_size = self.output_path.stat().st_size / (1024 * 1024)  # MB

            print(f"\n🎬 녹화 완료!")
            print(f"   파일: {self.output_path}")
            print(f"   길이: {duration:.1f}초")
            print(f"   프레임: {frame_count}개")
            print(f"   크기: {file_size:.2f} MB")

            # 상태 초기화
            self.is_recording = False
            self.video_writer = None
            self.frames = []
            self.start_time = None

            return str(self.output_path)

        except Exception as e:
            print(f"   ❌ 녹화 종료 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def record_with_interval(self, interval: float = 0.1):
        """
        일정 간격으로 프레임 캡처 (녹화 중일 때만)

        Args:
            interval: 프레임 캡처 간격(초) (기본: 0.1초 = 100ms)
        """
        if self.is_recording:
            self.capture_frame()
            time.sleep(interval)

    def _generate_filepath(self, keyword: str, version: str) -> Path:
        """
        영상 파일 경로 생성

        Args:
            keyword: 검색 키워드
            version: Chrome 버전

        Returns:
            저장할 파일 경로
        """
        # 버전별 디렉토리
        version_dir = self.base_dir / f"chrome-{version}" if version else self.base_dir / "chrome-unknown"

        # VPN/Local 디렉토리
        vpn_num = os.getenv('VPN_EXECUTED')
        if vpn_num and vpn_num != '0':
            target_dir = version_dir / f"vpn{vpn_num}"
        else:
            target_dir = version_dir / "local"

        # 디렉토리 생성
        target_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성 (키워드_날짜_시간.mp4)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 키워드 정리 (파일명에 사용 불가능한 문자 제거)
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_keyword:
            safe_keyword = "recording"

        filename = f"{safe_keyword}_{timestamp}.mp4"
        return target_dir / filename

    def __del__(self):
        """소멸자: VideoWriter 자원 해제"""
        if self.video_writer:
            self.video_writer.release()
