#!/usr/bin/env python3
"""
워커별 개별 이벤트 로거 (Per-Worker Event Logger)

각 워커가 자신의 로그 파일에 이벤트를 기록합니다.
ERR_NETWORK_CHANGED 발생 시 모든 워커의 로그를 타임스탬프 기준으로
병합하여 상관분석을 수행합니다.

로그 파일 경로:
    /tmp/vpn_events_wg101.log  (Worker-1)
    /tmp/vpn_events_wg102.log  (Worker-2)
    ...

사용법:
    from common.unified_event_logger import log_event, EventType

    log_event(
        worker_id="Worker-1",
        event_type=EventType.VPN_CONNECTING,
        interface="wg101",
        details={"server_ip": "1.2.3.4"}
    )
"""

import os
import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path


class EventType(Enum):
    """이벤트 타입 정의"""
    # VPN 이벤트
    VPN_CONNECTING = "VPN_CONNECTING"
    VPN_CONNECTED = "VPN_CONNECTED"
    VPN_DISCONNECTING = "VPN_DISCONNECTING"
    VPN_DISCONNECTED = "VPN_DISCONNECTED"
    VPN_ERROR = "VPN_ERROR"

    # 브라우저 이벤트
    BROWSER_LAUNCHING = "BROWSER_LAUNCHING"
    BROWSER_READY = "BROWSER_READY"
    BROWSER_CLOSING = "BROWSER_CLOSING"
    BROWSER_CLOSED = "BROWSER_CLOSED"

    # 네트워크 이벤트
    NETWORK_ERROR = "NETWORK_ERROR"
    ERR_NETWORK_CHANGED = "ERR_NETWORK_CHANGED"
    PAGE_LOADING = "PAGE_LOADING"
    PAGE_LOADED = "PAGE_LOADED"

    # 검색 워크플로우 이벤트
    SEARCH_STARTED = "SEARCH_STARTED"
    SEARCH_SUBMITTED = "SEARCH_SUBMITTED"
    RESULTS_LOADING = "RESULTS_LOADING"
    RESULTS_LOADED = "RESULTS_LOADED"

    # 시스템 네트워크 이벤트
    INTERFACE_ADDED = "INTERFACE_ADDED"
    INTERFACE_REMOVED = "INTERFACE_REMOVED"
    ROUTING_RULE_ADDED = "ROUTING_RULE_ADDED"
    ROUTING_RULE_REMOVED = "ROUTING_RULE_REMOVED"
    ROUTE_ADDED = "ROUTE_ADDED"
    ROUTE_REMOVED = "ROUTE_REMOVED"

    # 일반 이벤트
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# 워커 ID를 wg 사용자명으로 변환하는 캐시
_worker_to_wg_user: Dict[str, str] = {}


def _get_wg_user_from_worker_id(worker_id) -> str:
    """
    Worker-1 -> wg101
    Worker-2 -> wg102
    ...
    Worker-12 -> wg112
    """
    # worker_id를 문자열로 변환
    worker_id_str = str(worker_id)

    if worker_id_str in _worker_to_wg_user:
        return _worker_to_wg_user[worker_id_str]

    # Worker-N 형식에서 숫자 추출
    if worker_id_str.startswith("Worker-"):
        try:
            num = int(worker_id_str.split("-")[1])
            wg_user = f"wg{100 + num}"
            _worker_to_wg_user[worker_id_str] = wg_user
            return wg_user
        except (IndexError, ValueError):
            pass

    # 현재 사용자 이름 사용 (fallback)
    current_user = os.environ.get('USER', 'unknown')
    _worker_to_wg_user[worker_id_str] = current_user
    return current_user


def log_event(
    worker_id: str,
    event_type: EventType,
    interface: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    워커별 개별 로그 파일에 이벤트 기록

    Args:
        worker_id: 워커 식별자 (예: "Worker-1")
        event_type: 이벤트 타입
        interface: VPN 인터페이스 (예: "wg101")
        details: 추가 상세 정보
    """
    # 워커 ID에서 wg 사용자 이름 추출
    wg_user = _get_wg_user_from_worker_id(worker_id)

    # 로그 파일 경로: /tmp/vpn_events_wg101.log
    log_file = f"/tmp/vpn_events_{wg_user}.log"

    # 타임스탬프 (마이크로초 정밀도)
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%H:%M:%S.%f")[:-3]  # 밀리초까지
    timestamp_full = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")

    # JSON 이벤트 레코드
    event_record = {
        "timestamp": timestamp_full,
        "timestamp_display": timestamp_str,
        "worker_id": worker_id,
        "wg_user": wg_user,
        "event_type": event_type.value,
        "interface": interface or "N/A",
        "details": details or {}
    }

    try:
        file_exists = os.path.exists(log_file)

        # 파일이 없으면 생성 (append 모드)
        with open(log_file, 'a') as f:
            f.write(json.dumps(event_record, ensure_ascii=False) + "\n")

        # 파일이 새로 생성되었으면 666 권한 설정 (모든 사용자가 쓸 수 있음)
        if not file_exists:
            os.chmod(log_file, 0o666)
    except Exception as e:
        # 로깅 실패 오류를 stderr로 출력 (디버깅용)
        import sys
        print(f"⚠️ log_event() 실패: {log_file} - {type(e).__name__}: {e}", file=sys.stderr)
        pass


# 편의 함수: get_instance() 호환성 유지 (사용되지 않음)
class UnifiedEventLogger:
    """더미 클래스 (하위 호환성)"""

    @staticmethod
    def get_instance():
        """get_instance()는 더 이상 사용되지 않음"""
        return None
