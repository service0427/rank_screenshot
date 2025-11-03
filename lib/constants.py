#!/usr/bin/env python3
"""
Constants and Status Definitions
"""

from enum import Enum


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

    # Browser Profiles
    PROFILE_DIR_BASE = "/home/tech/agent/browser-profiles"

    # Watermark Settings (11+ rank display)
    WATERMARK_POSITION_TOP = "10px"
    WATERMARK_POSITION_RIGHT = "10px"  # 오른쪽 상단
    WATERMARK_BG_COLOR = "#FF6B00"  # 쿠팡 오렌지색
    WATERMARK_TEXT_COLOR = "white"
    WATERMARK_PADDING = "4px 8px"
    WATERMARK_FONT_SIZE = "12px"
    WATERMARK_FONT_WEIGHT = "bold"
    WATERMARK_BORDER_RADIUS = "4px"
    WATERMARK_Z_INDEX = "10"
    WATERMARK_FONT_FAMILY = "Arial, sans-serif"
    WATERMARK_LINE_HEIGHT = "1"
    WATERMARK_MIN_RANK = 11  # 11등부터 워터마크 표시
