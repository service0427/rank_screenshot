#!/usr/bin/env python3
"""
스크린샷 업로드 모듈
캡처된 스크린샷을 서버에 업로드하는 기능 제공
"""

import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import time


class ScreenshotUploader:
    """스크린샷을 서버에 업로드하는 클래스"""

    def __init__(
        self,
        upload_url: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30
    ):
        """
        Args:
            upload_url: 업로드 서버 URL
            max_retries: 최대 재시도 횟수 (기본: 3)
            retry_delay: 재시도 간 대기 시간(초) (기본: 1.0)
            timeout: 요청 타임아웃(초) (기본: 30)
        """
        self.upload_url = upload_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    def upload(
        self,
        filepath: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        스크린샷 파일을 서버에 업로드

        Args:
            filepath: 업로드할 파일 경로
            metadata: 추가 메타데이터 (선택)
                - keyword: 검색 키워드
                - product_id: 상품 ID
                - item_id: 아이템 ID
                - vendor_item_id: 판매자 아이템 ID
                - rank: 상품 순위

        Returns:
            {
                "success": bool,
                "uploaded_path": str,       # 업로드된 파일 경로
                "server_response": dict,    # 서버 응답
                "error": str                # 오류 메시지 (실패 시)
            }
        """
        filepath = Path(filepath)

        # 파일 존재 확인
        if not filepath.exists():
            return {
                "success": False,
                "uploaded_path": None,
                "server_response": None,
                "error": f"파일이 존재하지 않습니다: {filepath}"
            }

        # 파일 크기 확인
        file_size = filepath.stat().st_size
        if file_size == 0:
            return {
                "success": False,
                "uploaded_path": None,
                "server_response": None,
                "error": f"파일 크기가 0입니다: {filepath}"
            }

        print(f"\n📤 스크린샷 업로드 시작...")
        print(f"   파일: {filepath.name}")
        print(f"   크기: {file_size / 1024:.2f} KB")
        print(f"   서버: {self.upload_url}")

        # 메타데이터 준비
        metadata = metadata or {}

        # 재시도 로직
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"\n   시도 {attempt}/{self.max_retries}...")

                # multipart/form-data 형식으로 업로드
                with open(filepath, 'rb') as f:
                    # 실제 서버는 'image' 필드로 파일을 받음
                    files = {
                        'image': (filepath.name, f, 'image/png')
                    }

                    # 메타데이터를 form data로 추가 (필수 필드만)
                    data = {
                        'screenshot_id': metadata.get('screenshot_id', ''),
                        'keyword': metadata.get('keyword', ''),
                        'product_id': metadata.get('product_id', ''),
                        'item_id': metadata.get('item_id', ''),
                        'vendor_item_id': metadata.get('vendor_item_id', ''),
                        'rank': metadata.get('rank', '')
                    }

                    # POST 데이터 로그 출력
                    import json
                    print(f"   📋 전송 데이터 (multipart/form-data):")
                    print(f"      📎 파일 필드: image")
                    print(f"         - 파일명: {filepath.name}")
                    print(f"         - 타입: image/png")
                    print(f"         - 크기: {file_size / 1024:.2f} KB")
                    print(f"      📝 데이터 필드:")
                    print(f"{json.dumps(data, ensure_ascii=False, indent=8)}")

                    # POST 요청
                    response = requests.post(
                        self.upload_url,
                        files=files,
                        data=data,
                        timeout=self.timeout
                    )

                    # 응답 확인 (200 OK, 201 Created 모두 성공으로 처리)
                    if response.status_code in [200, 201]:
                        try:
                            server_response = response.json()
                        except:
                            server_response = {}

                        # 서버 응답 JSON 출력
                        import json
                        print(f"\n✅ 업로드 성공!")
                        print(f"   서버 응답: {json.dumps(server_response, ensure_ascii=False, indent=2)}")

                        return {
                            "success": True,
                            "uploaded_path": str(filepath),
                            "server_response": server_response,
                            "error": None
                        }
                    else:
                        last_error = f"서버 오류: HTTP {response.status_code}"
                        print(f"   ⚠️  {last_error}")
                        print(f"   응답: {response.text[:200]}")

            except requests.exceptions.Timeout:
                last_error = f"타임아웃 ({self.timeout}초)"
                print(f"   ⚠️  {last_error}")

            except requests.exceptions.ConnectionError as e:
                last_error = f"연결 오류: {str(e)}"
                print(f"   ⚠️  {last_error}")

            except Exception as e:
                last_error = f"업로드 실패: {str(e)}"
                print(f"   ⚠️  {last_error}")
                import traceback
                traceback.print_exc()

            # 재시도 대기
            if attempt < self.max_retries:
                print(f"   ⏱️  {self.retry_delay}초 후 재시도...")
                time.sleep(self.retry_delay)

        # 모든 재시도 실패
        print(f"\n❌ 업로드 실패 (최대 재시도 횟수 초과)")
        print(f"   오류: {last_error}")
        print(f"   파일은 로컬에 보존됨: {filepath}")

        return {
            "success": False,
            "uploaded_path": str(filepath),
            "server_response": None,
            "error": last_error
        }

    def upload_multiple(
        self,
        filepaths: list,
        metadata_list: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        여러 스크린샷을 순차적으로 업로드

        Args:
            filepaths: 업로드할 파일 경로 리스트
            metadata_list: 각 파일의 메타데이터 리스트 (선택)

        Returns:
            {
                "total": int,           # 전체 파일 수
                "success": int,         # 성공 개수
                "failed": int,          # 실패 개수
                "results": list         # 각 파일의 업로드 결과
            }
        """
        if not filepaths:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "results": []
            }

        # 메타데이터 리스트 준비
        if metadata_list is None:
            metadata_list = [None] * len(filepaths)
        elif len(metadata_list) < len(filepaths):
            metadata_list.extend([None] * (len(filepaths) - len(metadata_list)))

        print(f"\n📤 다중 스크린샷 업로드 시작 (총 {len(filepaths)}개)")
        print("=" * 60)

        results = []
        success_count = 0
        failed_count = 0

        for idx, (filepath, metadata) in enumerate(zip(filepaths, metadata_list), start=1):
            print(f"\n[{idx}/{len(filepaths)}] 업로드 중...")

            result = self.upload(filepath, metadata)
            results.append(result)

            if result["success"]:
                success_count += 1
            else:
                failed_count += 1

        print("\n" + "=" * 60)
        print(f"📊 업로드 완료")
        print(f"   전체: {len(filepaths)}개")
        print(f"   성공: {success_count}개")
        print(f"   실패: {failed_count}개")
        print("=" * 60)

        return {
            "total": len(filepaths),
            "success": success_count,
            "failed": failed_count,
            "results": results
        }
