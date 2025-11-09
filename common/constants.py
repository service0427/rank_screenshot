#!/usr/bin/env python3
"""
Constants and Status Definitions
"""

from enum import Enum
from pathlib import Path


# ===================================================================
# Import Path Configuration
# ===================================================================
# 프로젝트 구조 변경 시 이 설정만 수정하면 전체 import 경로가 자동으로 변경됨

class ImportPaths:
    """프로젝트 import 경로 설정"""

    # 기본 모듈 경로
    COMMON = "common"          # 공통 모듈 (constants, vpn, utils 등)
    UC_LIB = "uc_lib"          # UC 전용 모듈
    NODRIVER_LIB = "nodriver_lib"  # nodriver 전용 모듈 (추후)

    # 서브 경로
    CORE = "core"              # 브라우저 코어
    MODULES = "modules"        # 기능 모듈
    WORKFLOWS = "workflows"    # 워크플로우
    UTILS = "utils"            # 유틸리티

    @classmethod
    def get_import_path(cls, base: str, *sub_paths: str) -> str:
        """
        Import 경로 생성

        Args:
            base: 기본 모듈 경로 (COMMON, UC_LIB, NODRIVER_LIB)
            *sub_paths: 서브 경로들

        Returns:
            완전한 import 경로 (예: "common.utils.network_filter")
        """
        parts = [base] + list(sub_paths)
        return ".".join(parts)


# ===================================================================
# Action Status Constants
# ===================================================================

class ActionStatus(str, Enum):
    """Individual action lifecycle states"""
    # Initialization
    INIT = "INIT"
    PENDING = "PENDING"
    STARTED = "STARTED"

    # Page Loading
    NAVIGATING = "NAVIGATING"
    DOM_INTERACTIVE = "DOM_INTERACTIVE"
    DOM_READY = "DOM_READY"
    LOADED = "LOADED"
    NETWORK_IDLE = "NETWORK_IDLE"

    # Element States
    ELEMENT_WAITING = "ELEMENT_WAITING"
    ELEMENT_FOUND = "ELEMENT_FOUND"
    ELEMENT_VISIBLE = "ELEMENT_VISIBLE"
    ELEMENT_CLICKABLE = "ELEMENT_CLICKABLE"

    # Interaction Phases
    CLICKING = "CLICKING"
    TYPING = "TYPING"
    SCROLLING = "SCROLLING"

    # Outcomes
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"

    # Errors
    ERROR_TIMEOUT = "ERROR_TIMEOUT"
    ERROR_ELEMENT_NOT_FOUND = "ERROR_ELEMENT_NOT_FOUND"
    ERROR_NAVIGATION = "ERROR_NAVIGATION"
    ERROR_NETWORK = "ERROR_NETWORK"
    ERROR_UNKNOWN = "ERROR_UNKNOWN"


# ===================================================================
# Execution Status Constants
# ===================================================================

class ExecutionStatus(str, Enum):
    """Higher-level workflow states"""
    # Browser Lifecycle
    BROWSER_LAUNCHING = "BROWSER_LAUNCHING"
    BROWSER_READY = "BROWSER_READY"

    # Search Flow
    SEARCHING = "SEARCHING"
    SEARCH_SUBMITTED = "SEARCH_SUBMITTED"
    RESULTS_LOADED = "RESULTS_LOADED"

    # Product Interactions
    PRODUCT_FOUND = "PRODUCT_FOUND"
    PRODUCT_CLICKING = "PRODUCT_CLICKING"
    PRODUCT_PAGE_LOADED = "PRODUCT_PAGE_LOADED"

    # Cart Operations
    CART_CLICKING = "CART_CLICKING"
    CART_CLICKED = "CART_CLICKED"

    # Final States
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SearchMode(str, Enum):
    """Search execution modes"""
    BROWSER = "BROWSER"
    API = "API"


class SearchModeReason(str, Enum):
    """Reasons for mode selection"""
    FORCED_BROWSER = "FORCED_BROWSER"
    FORCED_API = "FORCED_API"
    AUTO_SELECTED = "AUTO_SELECTED"


class SuccessLevel(str, Enum):
    """Success evaluation levels"""
    FULL_SUCCESS = "FULL_SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILURE = "FAILURE"


class FinalStatus(str, Enum):
    """Final execution outcomes"""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


# ===================================================================
# HTTP Status Code Mapping
# ===================================================================

STATUS_HTTP_MAP = {
    # 2xx Success
    ExecutionStatus.COMPLETED: 200,
    ActionStatus.SUCCESS: 200,

    # 4xx Client Errors
    ActionStatus.ERROR_ELEMENT_NOT_FOUND: 404,
    ActionStatus.ERROR_TIMEOUT: 408,

    # 5xx Server Errors
    ActionStatus.ERROR_NETWORK: 502,
    ActionStatus.ERROR_NAVIGATION: 503,
    ActionStatus.ERROR_UNKNOWN: 500,
    ExecutionStatus.FAILED: 500,
}


def get_http_status(status) -> int:
    """Convert execution/action status to HTTP code"""
    return STATUS_HTTP_MAP.get(status, 500)


def is_success_status(status) -> bool:
    """Check if status represents success"""
    return status in [
        ActionStatus.SUCCESS,
        ExecutionStatus.COMPLETED,
        SuccessLevel.FULL_SUCCESS
    ]


def is_error_status(status) -> bool:
    """Check if status represents error"""
    if isinstance(status, str):
        return status.startswith("ERROR_")
    return status in [
        ExecutionStatus.FAILED,
        SuccessLevel.FAILURE
    ]


# ===================================================================
# Configuration Constants
# ===================================================================

class Config:
    """Global configuration"""

    # Browser Settings
    DEFAULT_VIEWPORT = {"width": 1200, "height": 800}
    DEFAULT_TIMEOUT = 30000  # 30 seconds

    # Delays (milliseconds)
    TYPING_MIN_DELAY = 80
    TYPING_MAX_DELAY = 200
    CLICK_MIN_DELAY = 100
    CLICK_MAX_DELAY = 300
    PAGE_LOAD_MIN_DELAY = 1000
    PAGE_LOAD_MAX_DELAY = 3000

    # Scroll Settings
    SCROLL_STEP_MIN = 100
    SCROLL_STEP_MAX = 300
    SCROLL_PAUSE_MIN = 200
    SCROLL_PAUSE_MAX = 500

    # Mouse Movement
    MOUSE_MOVE_STEPS_MIN = 10
    MOUSE_MOVE_STEPS_MAX = 30

    # Hub Server
    HUB_SERVER_URL = "http://mkt.techb.kr:3001"

    # Work API (작업 할당 및 결과 제출)
    # WORK_ALLOCATE_URL = "http://61.84.75.37:3302/api/work/allocate-screenshot?site_code=topr"
    WORK_ALLOCATE_URL = "http://61.84.75.37:3302/api/work/allocate-screenshot?type=adjust&site_code=topr"
    WORK_RESULT_URL = "http://61.84.75.37:3302/api/work/screenshot-result"

    # Browser Profiles (사용자별 독립 디렉토리)
    # VPN 사용 시 각 사용자(vpn0, vpn1...)가 자신의 홈 디렉토리에 프로필 저장
    # 이를 통해 권한 충돌 및 리소스 공유 문제 방지
    @staticmethod
    def get_profile_dir_base():
        import os
        from pathlib import Path

        # 현재 사용자의 홈 디렉토리 확인
        user = os.getenv('USER', 'unknown')

        # WireGuard 워커 사용자(wg101-112)의 경우 프로젝트 디렉토리 사용
        if user.startswith('wg') and len(user) >= 4 and user[2:].isdigit():
            # 프로젝트 root 디렉토리의 uc_browser-profiles 사용
            # uc_browser-profiles/wg101/{130,144}
            # uc_browser-profiles/wg102/{130,144}
            project_root = Path(__file__).parent.parent
            profile_base = project_root / "uc_browser-profiles" / user
        else:
            # 일반 사용자는 홈 디렉토리 사용
            home_dir = Path.home()
            profile_base = home_dir / ".coupang_agent_profiles"

        # 디렉토리 생성
        profile_base.mkdir(parents=True, exist_ok=True)

        return str(profile_base)

    # 레거시 호환성 유지 (기본값)
    PROFILE_DIR_BASE = str(Path(__file__).parent.parent / "browser-profiles")

    # Debug Settings
    DEBUG_MODE = False  # 디버그 모드 (--debug 플래그로 설정됨, 상세 로그 및 파일 저장)
    ENABLE_DEBUG_OVERLAY = True  # 디버깅 오버레이 표시 여부 ([전체:N/일반:M] 형식)

    # Fingerprint Verification
    ENABLE_FINGERPRINT_CHECK = True  # Fingerprint.com playground 접속 및 visitorId 추출 여부

    # Network Monitoring (ERR_NETWORK_CHANGED 감지용)
    ENABLE_NETWORK_ERROR_MONITOR = True  # CDP 네트워크 에러 모니터링 활성화
    NETWORK_ERROR_LOG_FILE = "/tmp/chrome_network_errors.log"  # 네트워크 에러 로그 파일

    # Highlight Settings (상품 강조 표시 + 순위 배지 통합)
    ENABLE_HIGHLIGHT = True  # 하이라이트(P/I/V 포함) 표시 여부 (False: 표시 안 함)

    # 테두리 설정
    HIGHLIGHT_BORDER_WIDTH = 5
    HIGHLIGHT_BORDER_COLOR = "#FF0000"
    HIGHLIGHT_BORDER_STYLE = "solid"  # solid, dashed, dotted
    HIGHLIGHT_BORDER_OFFSET = -5

    # 배경 오버레이 설정
    HIGHLIGHT_BACKGROUND_OVERLAY = True
    HIGHLIGHT_BACKGROUND_COLOR = "rgba(255, 255, 0, 0.15)"  # 연한 노란색

    # P/I/V 라벨 표시 설정
    HIGHLIGHT_SHOW_PIV_LABELS = True
    HIGHLIGHT_LABEL_FONT_SIZE = 15
    HIGHLIGHT_LABEL_BACKGROUND = "rgba(0, 0, 0, 0.85)"
    HIGHLIGHT_LABEL_TEXT_COLOR = "#CCCCCC"  # 기본 텍스트 색상
    HIGHLIGHT_LABEL_PADDING = 10
    HIGHLIGHT_LABEL_BORDER_RADIUS = 4
    HIGHLIGHT_MATCH_COLOR = "#FFFF00"  # 매칭된 필드 강조 색상 (노란색)
    # 위치 설정 (CSS 값 직접 지정)
    HIGHLIGHT_LABEL_TOP = "10px"
    HIGHLIGHT_LABEL_RIGHT = "10px"
    HIGHLIGHT_LABEL_BOTTOM = None
    HIGHLIGHT_LABEL_LEFT = None

    # 순위 배지 설정
    HIGHLIGHT_SHOW_RANK_BADGE = True
    HIGHLIGHT_RANK_BADGE_MIN_RANK = 11  # 최소 순위 (11등 이상만 표시, 10등 이하는 표시 안 함)
    HIGHLIGHT_RANK_BADGE_SIZE = 45
    HIGHLIGHT_RANK_BADGE_COLOR = "#FF6B6B"
    HIGHLIGHT_RANK_BADGE_TEXT_COLOR = "#FFFFFF"
    # 위치 설정 (CSS 값 직접 지정)
    HIGHLIGHT_RANK_BADGE_TOP = "10px"
    HIGHLIGHT_RANK_BADGE_RIGHT = None
    HIGHLIGHT_RANK_BADGE_BOTTOM = None
    HIGHLIGHT_RANK_BADGE_LEFT = "10px"
