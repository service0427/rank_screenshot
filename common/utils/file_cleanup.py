#!/usr/bin/env python3
"""
파일 자동 정리 유틸리티
최신 N개 파일만 유지하고 오래된 파일 자동 삭제
"""

import os
from pathlib import Path
from typing import Optional, List
import logging


logger = logging.getLogger(__name__)


def cleanup_old_files(
    directory: Path,
    keep_count: int = 50,
    file_pattern: str = "*",
    recursive: bool = True,
    dry_run: bool = False
) -> int:
    """
    디렉토리에서 오래된 파일을 자동으로 삭제하여 최신 N개만 유지

    Args:
        directory: 정리할 디렉토리 경로
        keep_count: 유지할 파일 개수 (기본: 50)
        file_pattern: 파일 패턴 (기본: "*" - 모든 파일)
        recursive: 하위 디렉토리 포함 여부 (기본: True)
        dry_run: 테스트 모드 (실제 삭제 안 함, 기본: False)

    Returns:
        삭제된 파일 개수
    """
    if not directory.exists():
        return 0

    # 모든 파일 찾기
    if recursive:
        files = list(directory.rglob(file_pattern))
    else:
        files = list(directory.glob(file_pattern))

    # 디렉토리 제외, 파일만
    files = [f for f in files if f.is_file()]

    # 파일 개수가 keep_count 이하면 삭제할 필요 없음
    if len(files) <= keep_count:
        return 0

    # 수정 시간 기준으로 정렬 (최신순)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # 오래된 파일 목록 (keep_count 이후)
    files_to_delete = files[keep_count:]

    deleted_count = 0
    for file_path in files_to_delete:
        try:
            if dry_run:
                logger.info(f"[DRY RUN] 삭제 대상: {file_path}")
            else:
                file_path.unlink()
                deleted_count += 1
        except Exception as e:
            logger.warning(f"파일 삭제 실패 ({file_path}): {e}")

    if deleted_count > 0:
        logger.info(f"✅ {directory.name}/ 에서 {deleted_count}개 파일 삭제 (최신 {keep_count}개 유지)")

    return deleted_count


def cleanup_screenshots(
    base_dir: Path = Path(__file__).parent.parent.parent / "screenshots",
    keep_count: int = 50
) -> int:
    """
    스크린샷 디렉토리 정리

    Args:
        base_dir: 스크린샷 기본 디렉토리
        keep_count: 유지할 파일 개수

    Returns:
        삭제된 파일 개수
    """
    return cleanup_old_files(
        directory=base_dir,
        keep_count=keep_count,
        file_pattern="*.png",
        recursive=True,
        dry_run=False
    )


def cleanup_debug_logs(
    base_dir: Path = Path(__file__).parent.parent.parent / "debug_logs",
    keep_count: int = 50
) -> int:
    """
    디버그 로그 디렉토리 정리

    Args:
        base_dir: 디버그 로그 기본 디렉토리
        keep_count: 유지할 파일 개수

    Returns:
        삭제된 파일 개수
    """
    return cleanup_old_files(
        directory=base_dir,
        keep_count=keep_count,
        file_pattern="*.json",
        recursive=True,
        dry_run=False
    )


def cleanup_all(keep_count: int = 50) -> dict:
    """
    모든 임시 파일 정리 (스크린샷 + 디버그 로그)

    Args:
        keep_count: 각 디렉토리에서 유지할 파일 개수

    Returns:
        삭제 결과 딕셔너리 {'screenshots': N, 'debug_logs': M}
    """
    result = {
        'screenshots': cleanup_screenshots(keep_count=keep_count),
        'debug_logs': cleanup_debug_logs(keep_count=keep_count)
    }

    total = sum(result.values())
    if total > 0:
        logger.info(f"🗑️  전체 {total}개 파일 정리 완료 (스크린샷: {result['screenshots']}, 로그: {result['debug_logs']})")

    return result


if __name__ == "__main__":
    # 테스트용
    logging.basicConfig(level=logging.INFO)

    print("🧹 파일 정리 테스트 (DRY RUN)")
    print("=" * 60)

    # 스크린샷
    screenshot_dir = Path(__file__).parent.parent.parent / "screenshots"
    if screenshot_dir.exists():
        files = list(screenshot_dir.rglob("*.png"))
        print(f"\n📸 스크린샷: {len(files)}개 파일")
        cleanup_old_files(screenshot_dir, keep_count=50, file_pattern="*.png", dry_run=True)

    # 디버그 로그
    debug_dir = Path(__file__).parent.parent.parent / "debug_logs"
    if debug_dir.exists():
        files = list(debug_dir.rglob("*.json"))
        print(f"\n📋 디버그 로그: {len(files)}개 파일")
        cleanup_old_files(debug_dir, keep_count=50, file_pattern="*.json", dry_run=True)

    print("\n" + "=" * 60)
    print("✅ 테스트 완료 (실제 삭제는 하지 않음)")
