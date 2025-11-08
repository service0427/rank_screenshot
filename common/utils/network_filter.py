"""
네트워크 필터 모듈

쿠팡 메인 페이지 최적화를 위한 광고/트래킹 차단
"""

import json
import re
from pathlib import Path
from typing import List, Dict


class NetworkFilter:
    """네트워크 필터 - 광고/트래킹 차단"""

    def __init__(self, config_path='config/filter_config.json'):
        self.config_path = Path(__file__).parent.parent.parent / config_path
        self.config = self.load_config()
        self.blocked_patterns = self._compile_patterns()

    def load_config(self) -> Dict:
        """필터 설정 로드"""
        if not self.config_path.exists():
            print(f"⚠️  필터 설정 파일 없음: {self.config_path}")
            return {
                'console_only_filters': {'patterns': []},
                'full_filters': {'domains': [], 'patterns': []},
                'domain_whitelist': {'domains': ['coupang.com']}
            }

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _compile_patterns(self) -> List:
        """차단 패턴을 정규표현식으로 컴파일"""
        patterns = []

        # full_filters 도메인을 패턴으로 변환
        for domain in self.config['full_filters']['domains']:
            # domain.com → .*domain\.com.*
            pattern = f".*{re.escape(domain)}.*"
            patterns.append(re.compile(pattern, re.IGNORECASE))

        # full_filters 패턴 추가
        for pattern_str in self.config['full_filters']['patterns']:
            patterns.append(re.compile(pattern_str, re.IGNORECASE))

        return patterns

    def is_whitelisted_domain(self, url: str) -> bool:
        """화이트리스트 도메인 체크"""
        whitelist = self.config['domain_whitelist']['domains']
        for domain in whitelist:
            # 정규표현식 패턴 지원 (예: image[0-9]*.coupangcdn.com)
            if re.search(domain, url, re.IGNORECASE):
                return True
        return False

    def should_block(self, url: str) -> bool:
        """
        URL을 차단해야 하는지 판단

        Args:
            url: 요청 URL

        Returns:
            True: 차단, False: 허용
        """
        # 화이트리스트 도메인이면 허용
        if self.is_whitelisted_domain(url):
            # 화이트리스트 도메인이더라도 특정 패턴은 차단
            # 예: coupang.com/ad/*, coupang.com/tracking/*
            for pattern in self.blocked_patterns:
                if pattern.search(url):
                    return True
            return False

        # 화이트리스트가 아니면 차단 패턴 확인
        for pattern in self.blocked_patterns:
            if pattern.search(url):
                return True

        # 기본: 외부 도메인은 차단
        # coupang.com 관련 도메인이 아니면 모두 차단
        if not ('coupang' in url.lower() or 'localhost' in url.lower()):
            return True

        return False

    def should_filter_console_only(self, url: str) -> bool:
        """콘솔 전용 필터 (로그에는 기록, 콘솔에는 출력 안 함)"""
        for pattern in self.config['console_only_filters']['patterns']:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def get_blocked_url_patterns(self) -> List[str]:
        """
        CDP Network.setBlockedURLs에 사용할 패턴 리스트 반환

        Returns:
            차단할 URL 패턴 리스트
        """
        patterns = []

        # full_filters 도메인 - 다양한 프로토콜과 경로 대응
        for domain in self.config['full_filters']['domains']:
            # http/https 모두 차단
            patterns.append(f"*://*{domain}/*")
            patterns.append(f"*://*.{domain}/*")  # 서브도메인 포함
            # 쿼리스트링 포함 케이스
            patterns.append(f"*://*{domain}*")

        # full_filters 패턴 (CDP glob 형식으로 변환)
        for pattern in self.config['full_filters']['patterns']:
            # 패턴별 변환
            if pattern.startswith('/') and pattern.endswith('/'):
                # /banner/ → */banner/*
                cleaned = pattern.strip('/')
                patterns.append(f"*/{cleaned}/*")
                patterns.append(f"*/{cleaned}?*")  # 쿼리스트링 포함
            elif '\\.' in pattern:
                # /gtm\.js → */gtm.js*
                cleaned = pattern.replace('\\', '')
                patterns.append(f"*{cleaned}*")
            else:
                # 기타 패턴
                patterns.append(f"*{pattern}*")

        return patterns

    def print_summary(self):
        """필터 설정 요약 출력"""
        print(f"\n🛡️  네트워크 필터 설정:")
        print(f"   - 차단 도메인: {len(self.config['full_filters']['domains'])}개")
        print(f"   - 차단 패턴: {len(self.config['full_filters']['patterns'])}개")
        print(f"   - 화이트리스트: {len(self.config['domain_whitelist']['domains'])}개")
        print(f"   - 콘솔 필터: {len(self.config['console_only_filters']['patterns'])}개\n")
