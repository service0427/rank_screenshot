#!/usr/bin/env python3
"""
키워드별 사이클 로거

각 키워드마다 별도의 로그 파일을 생성하고 최신 50개만 유지합니다.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class KeywordLogger:
    """키워드별 사이클 로그 관리"""

    def __init__(self, base_dir: str = "/home/tech/rank_screenshot/logs/keyword_cycles"):
        """
        Args:
            base_dir: 로그 파일 저장 디렉토리
        """
        self.base_dir = Path(base_dir)

        # umask를 일시적으로 0으로 설정하여 777 권한으로 디렉토리 생성
        import os
        old_umask = os.umask(0)
        try:
            self.base_dir.mkdir(parents=True, mode=0o777, exist_ok=True)
        finally:
            os.umask(old_umask)

        # 디렉토리 권한 명시적 설정
        try:
            os.chmod(self.base_dir, 0o777)
        except (PermissionError, OSError):
            pass  # 권한 변경 불가 시 무시

    def _get_log_file(self, keyword: str) -> Path:
        """
        키워드에 해당하는 로그 파일 경로 생성

        Args:
            keyword: 검색 키워드

        Returns:
            로그 파일 경로
        """
        # 파일명에 사용할 수 없는 문자 제거
        safe_keyword = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in keyword)
        return self.base_dir / f"{safe_keyword}.jsonl"

    def log_cycle(
        self,
        keyword: str,
        worker_id: str,
        cycle_data: Dict[str, Any]
    ):
        """
        키워드 사이클 로그 추가

        Args:
            keyword: 검색 키워드
            worker_id: 워커 ID (예: "Worker-1")
            cycle_data: 사이클 데이터
                - success: bool
                - matched_product: Dict
                - match_condition: str
                - rank: int
                - original_rank: int (Adjust 모드)
                - is_adjusted: bool (Adjust 모드)
                - screenshot_path: str
                - error_message: str
                - pages_searched: int
                - total_products_checked: int
                - execution_time: float
        """
        log_file = self._get_log_file(keyword)

        # 로그 엔트리 생성
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "worker_id": worker_id,
            "keyword": keyword,
            **cycle_data
        }

        # 기존 로그 읽기
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = [json.loads(line) for line in f if line.strip()]
            except Exception as e:
                print(f"⚠️  기존 로그 읽기 실패: {e}")
                existing_logs = []

        # 새 로그 추가
        existing_logs.append(log_entry)

        # 최신 50개만 유지
        if len(existing_logs) > 50:
            existing_logs = existing_logs[-50:]

        # 로그 파일 쓰기
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                for log in existing_logs:
                    f.write(json.dumps(log, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  로그 저장 실패: {e}")

    def get_recent_logs(self, keyword: str, limit: int = 10) -> list:
        """
        최근 로그 조회

        Args:
            keyword: 검색 키워드
            limit: 조회할 로그 개수 (기본: 10)

        Returns:
            로그 리스트 (최신순)
        """
        log_file = self._get_log_file(keyword)

        if not log_file.exists():
            return []

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = [json.loads(line) for line in f if line.strip()]
            return logs[-limit:]
        except Exception as e:
            print(f"⚠️  로그 조회 실패: {e}")
            return []

    def get_statistics(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        키워드별 통계 조회

        Args:
            keyword: 검색 키워드

        Returns:
            통계 정보 (성공률, 평균 실행시간 등)
        """
        logs = self.get_recent_logs(keyword, limit=50)

        if not logs:
            return None

        total = len(logs)
        success_count = sum(1 for log in logs if log.get('success', False))

        execution_times = [log.get('execution_time', 0) for log in logs if log.get('execution_time')]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        # Adjust 모드 통계
        adjusted_count = sum(1 for log in logs if log.get('is_adjusted', False))

        return {
            "keyword": keyword,
            "total_cycles": total,
            "success_count": success_count,
            "success_rate": success_count / total * 100 if total > 0 else 0,
            "avg_execution_time": avg_execution_time,
            "adjusted_count": adjusted_count,
            "adjusted_rate": adjusted_count / total * 100 if total > 0 else 0
        }

    def cleanup_old_logs(self, days: int = 7):
        """
        오래된 로그 파일 정리

        Args:
            days: 보관 기간 (일)
        """
        import time
        cutoff_time = time.time() - (days * 86400)

        for log_file in self.base_dir.glob("*.jsonl"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    print(f"🧹 오래된 로그 삭제: {log_file.name}")
            except Exception as e:
                print(f"⚠️  로그 삭제 실패 ({log_file.name}): {e}")


# 사용 예시
if __name__ == "__main__":
    logger = KeywordLogger()

    # 로그 추가
    logger.log_cycle(
        keyword="노트북파우치",
        worker_id="Worker-1",
        cycle_data={
            "success": True,
            "rank": 7,
            "original_rank": 1,
            "is_adjusted": True,
            "screenshot_path": "/path/to/screenshot.png",
            "execution_time": 68.5,
            "pages_searched": 1,
            "total_products_checked": 27
        }
    )

    # 최근 로그 조회
    recent = logger.get_recent_logs("노트북파우치", limit=5)
    print(f"\n📊 최근 5개 로그:")
    for log in recent:
        print(f"   {log['timestamp']}: {'✅' if log['success'] else '❌'} 순위 {log.get('rank', 'N/A')}")

    # 통계 조회
    stats = logger.get_statistics("노트북파우치")
    if stats:
        print(f"\n📈 통계:")
        print(f"   총 사이클: {stats['total_cycles']}회")
        print(f"   성공률: {stats['success_rate']:.1f}%")
        print(f"   평균 실행시간: {stats['avg_execution_time']:.1f}초")
        print(f"   DOM 조작: {stats['adjusted_count']}회 ({stats['adjusted_rate']:.1f}%)")
