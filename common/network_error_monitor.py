#!/usr/bin/env python3
"""
CDP 네트워크 에러 모니터 (ERR_NETWORK_CHANGED 실시간 감지)

Chrome DevTools Protocol을 사용하여 브라우저 네트워크 에러를 실시간으로 감지하고 로깅합니다.
특히 ERR_NETWORK_CHANGED 오류 발생 시 타임스탬프를 기록하여 시스템 네트워크 이벤트와 상관분석이 가능합니다.
"""

import threading
import time
from datetime import datetime
from typing import Optional
import json

# 통합 이벤트 로거 import
try:
    from common.unified_event_logger import log_event, EventType
    UNIFIED_LOGGER_AVAILABLE = True
except ImportError:
    UNIFIED_LOGGER_AVAILABLE = False

class NetworkErrorMonitor:
    """CDP 네트워크 에러 모니터"""

    def __init__(self, driver, worker_id: str, interface: str = None, log_file="/tmp/chrome_network_errors.log"):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
            worker_id: 워커 식별자 (예: "Worker-1")
            interface: VPN 인터페이스 (예: "wg101")
            log_file: 로그 파일 경로
        """
        self.driver = driver
        self.worker_id = worker_id
        self.interface = interface or "N/A"
        self.log_file = log_file
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # 에러 카운터
        self.error_count = 0
        self.network_changed_count = 0

    def log(self, message, level="INFO"):
        """타임스탬프와 함께 로그 기록"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{self.worker_id}] [{level}] {message}"

        # 콘솔 출력
        if level in ["ERROR", "CRITICAL"]:
            print(f"\n🔴 {log_line}")
        elif level == "WARNING":
            print(f"\n⚠️  {log_line}")
        else:
            print(log_line)

        # 파일 기록
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_line + "\n")
        except:
            pass

    def enable_network_monitoring(self):
        """CDP Network 도메인 활성화"""
        try:
            # Network 도메인 활성화
            self.driver.execute_cdp_cmd('Network.enable', {})

            # Page 도메인 활성화 (프레임 네비게이션 감지용)
            self.driver.execute_cdp_cmd('Page.enable', {})

            # Log 도메인 활성화 (콘솔 에러 감지용)
            self.driver.execute_cdp_cmd('Log.enable', {})

            self.log("CDP 네트워크 모니터링 활성화 완료", "INFO")
            return True

        except Exception as e:
            self.log(f"CDP 활성화 실패: {e}", "ERROR")
            return False

    def check_network_errors(self):
        """CDP 로그에서 네트워크 에러 확인"""
        try:
            # Chrome 로그 가져오기
            logs = self.driver.get_log('performance')

            for entry in logs:
                try:
                    message = json.loads(entry['message'])
                    method = message.get('message', {}).get('method', '')
                    params = message.get('message', {}).get('params', {})

                    # Network.loadingFailed 이벤트 감지
                    if method == 'Network.loadingFailed':
                        error_text = params.get('errorText', '')
                        request_id = params.get('requestId', 'unknown')
                        canceled = params.get('canceled', False)

                        # ERR_NETWORK_CHANGED 감지
                        if 'ERR_NETWORK_CHANGED' in error_text:
                            self.network_changed_count += 1
                            self.error_count += 1

                            self.log(
                                f"🚨 ERR_NETWORK_CHANGED 감지! "
                                f"(발생 횟수: {self.network_changed_count})",
                                "CRITICAL"
                            )
                            self.log(
                                f"   요청 ID: {request_id}",
                                "CRITICAL"
                            )
                            self.log(
                                f"   취소 여부: {canceled}",
                                "CRITICAL"
                            )

                            # 추가 디버그 정보
                            if 'type' in params:
                                self.log(
                                    f"   리소스 타입: {params['type']}",
                                    "CRITICAL"
                                )

                            # 통합 로거에 이벤트 기록
                            if UNIFIED_LOGGER_AVAILABLE:
                                log_event(
                                    worker_id=self.worker_id,
                                    event_type=EventType.ERR_NETWORK_CHANGED,
                                    interface=self.interface,
                                    details={
                                        'request_id': request_id,
                                        'canceled': canceled,
                                        'resource_type': params.get('type', 'unknown'),
                                        'error_text': error_text
                                    }
                                )

                        # 기타 네트워크 에러
                        elif error_text and 'ERR_' in error_text:
                            self.error_count += 1
                            self.log(
                                f"⚠️  네트워크 에러: {error_text} (RequestID: {request_id})",
                                "WARNING"
                            )

                    # Page.frameNavigated 이벤트 감지 (페이지 로드)
                    elif method == 'Page.frameNavigated':
                        frame = params.get('frame', {})
                        url = frame.get('url', '')

                        # ERR_NETWORK_CHANGED 에러 페이지 감지
                        if 'chrome-error://' in url and 'ERR_NETWORK_CHANGED' in url:
                            self.network_changed_count += 1
                            self.error_count += 1
                            self.log(
                                f"🚨 ERR_NETWORK_CHANGED 에러 페이지 감지! "
                                f"(발생 횟수: {self.network_changed_count})",
                                "CRITICAL"
                            )
                            self.log(f"   URL: {url}", "CRITICAL")

                            # 통합 로거에 이벤트 기록
                            if UNIFIED_LOGGER_AVAILABLE:
                                log_event(
                                    worker_id=self.worker_id,
                                    event_type=EventType.ERR_NETWORK_CHANGED,
                                    interface=self.interface,
                                    details={
                                        'source': 'chrome-error-page',
                                        'url': url
                                    }
                                )
                        elif url and 'about:blank' not in url and 'chrome-error://' not in url:
                            self.log(f"📄 페이지 로드: {url[:100]}", "INFO")

                        # 에러 페이지 일반 감지 (ERR_ 포함)
                        elif 'chrome-error://' in url:
                            error_match = url.split('/')[-1] if '/' in url else 'UNKNOWN'
                            if error_match.startswith('ERR_'):
                                self.error_count += 1
                                self.log(f"⚠️  Chrome 에러 페이지: {error_match}", "WARNING")

                    # Log.entryAdded 이벤트 감지 (콘솔 에러)
                    elif method == 'Log.entryAdded':
                        entry_obj = params.get('entry', {})
                        level = entry_obj.get('level', '')
                        text = entry_obj.get('text', '')

                        if level == 'error' and text:
                            # ERR_NETWORK_CHANGED가 콘솔에 출력될 수도 있음
                            if 'ERR_NETWORK_CHANGED' in text:
                                self.network_changed_count += 1
                                self.log(
                                    f"🚨 ERR_NETWORK_CHANGED (콘솔): {text}",
                                    "CRITICAL"
                                )
                            else:
                                self.log(f"❌ 콘솔 에러: {text[:200]}", "WARNING")

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    # 개별 로그 파싱 실패는 무시
                    continue

        except Exception as e:
            # get_log 실패는 무시 (브라우저가 닫혔을 수 있음)
            pass

    def monitor_loop(self, interval=0.5):
        """네트워크 에러 모니터링 루프"""
        self.log(f"네트워크 에러 모니터링 시작 (간격: {interval}초)", "INFO")

        self.monitoring = True
        iteration = 0

        while self.monitoring:
            try:
                time.sleep(interval)
                iteration += 1

                # 네트워크 에러 확인
                self.check_network_errors()

                # 매 20회마다 상태 출력 (10초마다, interval=0.5인 경우)
                if iteration % 20 == 0:
                    elapsed = iteration * interval
                    if self.error_count > 0:
                        self.log(
                            f"📊 모니터링 중... "
                            f"(에러: {self.error_count}회, "
                            f"ERR_NETWORK_CHANGED: {self.network_changed_count}회, "
                            f"경과: {elapsed:.0f}초)",
                            "STATUS"
                        )

            except Exception as e:
                # 모니터링 루프 에러는 로그만 남기고 계속 진행
                self.log(f"모니터링 루프 에러: {e}", "ERROR")
                time.sleep(1)  # 에러 발생 시 1초 대기

        self.log("네트워크 에러 모니터링 종료", "INFO")

    def start(self, interval=0.5):
        """백그라운드 모니터링 시작"""
        if self.monitoring:
            self.log("이미 모니터링 중입니다", "WARNING")
            return

        # CDP 활성화
        if not self.enable_network_monitoring():
            return

        # 백그라운드 스레드 시작
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()

        self.log("백그라운드 모니터링 스레드 시작", "INFO")

    def stop(self):
        """모니터링 중지"""
        if not self.monitoring:
            return

        self.monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

        self.log(
            f"모니터링 종료 - "
            f"총 에러: {self.error_count}회, "
            f"ERR_NETWORK_CHANGED: {self.network_changed_count}회",
            "INFO"
        )

    def get_stats(self):
        """에러 통계 반환"""
        return {
            'total_errors': self.error_count,
            'network_changed_errors': self.network_changed_count,
            'monitoring': self.monitoring
        }

# 사용 예시
if __name__ == "__main__":
    print("이 모듈은 직접 실행할 수 없습니다.")
    print("browser_core_uc.py에서 import하여 사용하세요:")
    print("")
    print("from common.network_error_monitor import NetworkErrorMonitor")
    print("")
    print("# BrowserCoreUC.launch() 이후")
    print("monitor = NetworkErrorMonitor(driver, worker_id='Worker-1')")
    print("monitor.start()")
