#!/usr/bin/env python3
"""
Multi-Browser Manager for nodriver, Selenium, and Playwright
Supports Chrome and Firefox with TLS fingerprinting variety
"""

import asyncio
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


class BrowserVersionManager:
    """통합 브라우저 버전 관리 클래스"""

    def __init__(
        self,
        chrome_dir="/home/tech/agent/chrome-version",
        firefox_dir="/home/tech/agent/firefox-version"
    ):
        self.chrome_dir = Path(chrome_dir)
        self.firefox_dir = Path(firefox_dir)

        self.chrome_versions = self._scan_chrome()
        self.firefox_versions = self._scan_firefox()

    def _scan_chrome(self) -> Dict[str, str]:
        """Chrome 버전 스캔 (Stable 127-144 + Beta/Dev/Canary 채널)"""
        versions = {}
        if not self.chrome_dir.exists():
            return versions

        for version_dir in sorted(self.chrome_dir.glob("*")):
            if version_dir.is_dir():
                chrome_bin = version_dir / "chrome-linux64" / "chrome"
                version_file = version_dir / "VERSION"

                if chrome_bin.exists() and version_file.exists():
                    # 디렉토리 이름을 버전 키로 사용 (127, 134, beta, dev, canary 등)
                    major = version_dir.name
                    versions[major] = str(chrome_bin)

        return versions

    def _scan_firefox(self) -> Dict[str, str]:
        """Firefox 버전 스캔"""
        versions = {}
        if not self.firefox_dir.exists():
            return versions

        for version_dir in sorted(self.firefox_dir.glob("*")):
            if version_dir.is_dir():
                firefox_bin = version_dir / "firefox" / "firefox"
                version_file = version_dir / "VERSION"

                if firefox_bin.exists() and version_file.exists():
                    major = version_dir.name
                    versions[major] = str(firefox_bin)

        return versions

    def list_all(self):
        """모든 설치된 브라우저 출력"""
        print("🌐 설치된 브라우저:")
        print("\n📦 Chrome:")
        for major, path in self.chrome_versions.items():
            print(f"  • Chrome {major}: {path}")
        print(f"  Total: {len(self.chrome_versions)} versions")

        print("\n🦊 Firefox:")
        for major, path in self.firefox_versions.items():
            print(f"  • Firefox {major}: {path}")
        print(f"  Total: {len(self.firefox_versions)} versions")

    def get_chrome(self, version: str) -> Optional[str]:
        """특정 Chrome 버전 경로"""
        return self.chrome_versions.get(version)

    def get_firefox(self, version: str) -> Optional[str]:
        """특정 Firefox 버전 경로"""
        return self.firefox_versions.get(version)

    def get_random_chrome(self) -> Tuple[str, str]:
        """랜덤 Chrome 버전"""
        if not self.chrome_versions:
            raise ValueError("Chrome이 설치되어 있지 않습니다")
        major = random.choice(list(self.chrome_versions.keys()))
        return major, self.chrome_versions[major]

    def get_random_firefox(self) -> Tuple[str, str]:
        """랜덤 Firefox 버전"""
        if not self.firefox_versions:
            raise ValueError("Firefox가 설치되어 있지 않습니다")
        major = random.choice(list(self.firefox_versions.keys()))
        return major, self.firefox_versions[major]

    def get_random_browser(self) -> Tuple[str, str, str]:
        """랜덤 브라우저 (Chrome 또는 Firefox)"""
        browsers = []
        if self.chrome_versions:
            browsers.append("chrome")
        if self.firefox_versions:
            browsers.append("firefox")

        if not browsers:
            raise ValueError("설치된 브라우저가 없습니다")

        browser_type = random.choice(browsers)

        if browser_type == "chrome":
            major, path = self.get_random_chrome()
            return "chrome", major, path
        else:
            major, path = self.get_random_firefox()
            return "firefox", major, path

    def get_chrome_group(self, group="old") -> Tuple[str, str]:
        """Chrome 그룹별 선택"""
        groups = {
            "old": ["127", "128", "129", "130"],
            "new": ["131", "132", "133", "134", "135", "136", "137", "138", "139", "140", "141"],
            "latest": ["142", "143", "144"],
            "channels": ["beta", "dev", "canary"]  # 채널 그룹 추가
        }

        available = [v for v in groups.get(group, []) if v in self.chrome_versions]
        if not available:
            raise ValueError(f"Chrome 그룹 '{group}'에 사용 가능한 버전이 없습니다")

        major = random.choice(available)
        return major, self.chrome_versions[major]


# ===================================================================
# nodriver 예제
# ===================================================================

async def example_nodriver_chrome(manager: BrowserVersionManager):
    """nodriver로 Chrome 제어"""
    try:
        import nodriver as uc
    except ImportError:
        print("⚠️  nodriver가 설치되어 있지 않습니다: pip install nodriver")
        return

    print("\n" + "="*60)
    print("nodriver - Chrome")
    print("="*60)

    major, chrome_path = manager.get_random_chrome()
    print(f"사용 중: Chrome {major}")
    print(f"경로: {chrome_path}")

    config = uc.Config(
        browser_executable_path=chrome_path,
        headless=False,  # GUI 모드
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    browser = await uc.start(config=config)

    page = await browser.get("https://httpbin.org/user-agent")
    await asyncio.sleep(1)

    ua = await page.evaluate("document.body.innerText")
    print(f"User-Agent: {ua[:100]}")

    try:
        browser.stop()
    except:
        pass
    print("✓ 완료")


# ===================================================================
# Selenium 예제
# ===================================================================

def example_selenium_chrome(manager: BrowserVersionManager):
    """Selenium으로 Chrome 제어"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        print("⚠️  Selenium이 설치되어 있지 않습니다: pip install selenium")
        return

    print("\n" + "="*60)
    print("Selenium - Chrome")
    print("="*60)

    major, chrome_path = manager.get_random_chrome()
    print(f"사용 중: Chrome {major}")
    print(f"경로: {chrome_path}")

    options = Options()
    options.binary_location = chrome_path
    # GUI 모드 - headless 옵션 제거
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    # ChromeDriver는 자동으로 다운로드됨 (Selenium 4.6+)
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://httpbin.org/user-agent")
        ua = driver.find_element("tag name", "pre").text
        print(f"User-Agent: {ua[:100]}")
    finally:
        driver.quit()

    print("✓ 완료")


def example_selenium_firefox(manager: BrowserVersionManager):
    """Selenium으로 Firefox 제어"""
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options
    except ImportError:
        print("⚠️  Selenium이 설치되어 있지 않습니다: pip install selenium")
        return

    print("\n" + "="*60)
    print("Selenium - Firefox")
    print("="*60)

    major, firefox_path = manager.get_random_firefox()
    print(f"사용 중: Firefox {major}")
    print(f"경로: {firefox_path}")

    options = Options()
    options.binary_location = firefox_path
    # GUI 모드 - headless 옵션 제거

    # GeckoDriver는 자동으로 다운로드됨 (Selenium 4.6+)
    driver = webdriver.Firefox(options=options)

    try:
        driver.get("https://httpbin.org/user-agent")
        ua = driver.find_element("tag name", "pre").text
        print(f"User-Agent: {ua[:100]}")
    finally:
        driver.quit()

    print("✓ 완료")


# ===================================================================
# Playwright 예제
# ===================================================================

async def example_playwright_chrome(manager: BrowserVersionManager):
    """Playwright로 Chrome 제어"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("⚠️  Playwright가 설치되어 있지 않습니다:")
        print("   pip install playwright")
        print("   playwright install")
        return

    print("\n" + "="*60)
    print("Playwright - Chrome")
    print("="*60)

    major, chrome_path = manager.get_random_chrome()
    print(f"사용 중: Chrome {major}")
    print(f"경로: {chrome_path}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=chrome_path,
            headless=False  # GUI 모드
        )

        page = await browser.new_page()
        await page.goto("https://httpbin.org/user-agent")

        content = await page.content()
        print(f"Content length: {len(content)}")

        await browser.close()

    print("✓ 완료")


async def example_playwright_firefox(manager: BrowserVersionManager):
    """Playwright로 Firefox 제어"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("⚠️  Playwright가 설치되어 있지 않습니다:")
        print("   pip install playwright")
        print("   playwright install")
        return

    print("\n" + "="*60)
    print("Playwright - Firefox")
    print("="*60)

    major, firefox_path = manager.get_random_firefox()
    print(f"사용 중: Firefox {major}")
    print(f"경로: {firefox_path}")

    async with async_playwright() as p:
        browser = await p.firefox.launch(
            executable_path=firefox_path,
            headless=False  # GUI 모드
        )

        page = await browser.new_page()
        await page.goto("https://httpbin.org/user-agent")

        content = await page.content()
        print(f"Content length: {len(content)}")

        await browser.close()

    print("✓ 완료")


# ===================================================================
# TLS 핑거프린팅 비교 예제
# ===================================================================

async def example_fingerprint_comparison(manager: BrowserVersionManager):
    """브라우저별 TLS 핑거프린팅 비교"""
    print("\n" + "="*60)
    print("TLS 핑거프린팅 비교")
    print("="*60)

    browsers_to_test = []

    # Chrome 그룹 1 (127-130)
    try:
        major, path = manager.get_chrome_group("old")
        browsers_to_test.append(("Chrome (old)", major, path))
    except ValueError:
        pass

    # Chrome 그룹 2 (131-141)
    try:
        major, path = manager.get_chrome_group("new")
        browsers_to_test.append(("Chrome (new)", major, path))
    except ValueError:
        pass

    # Firefox
    try:
        major, path = manager.get_random_firefox()
        browsers_to_test.append(("Firefox", major, path))
    except ValueError:
        pass

    if not browsers_to_test:
        print("⚠️  테스트할 브라우저가 없습니다")
        return

    # nodriver로 테스트
    try:
        import nodriver as uc

        for browser_type, major, path in browsers_to_test:
            if "Firefox" in browser_type:
                print(f"\n⏭️  {browser_type} {major} - nodriver는 Firefox를 지원하지 않습니다")
                continue

            print(f"\n🔍 {browser_type} {major}")

            config = uc.Config(
                browser_executable_path=path,
                headless=False,  # GUI 모드
                browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            browser = await uc.start(config=config)

            page = await browser.get("https://tls.browserleaks.com/json")
            await asyncio.sleep(2)

            try:
                content = await page.evaluate("document.body.innerText")
                data = json.loads(content)

                print(f"  TLS Version: {data.get('tls_version', 'N/A')}")
                print(f"  Cipher Suite: {data.get('cipher_suite', 'N/A')[:50]}...")
                print(f"  User Agent: {data.get('user_agent', 'N/A')[:80]}...")

            except Exception as e:
                print(f"  ⚠️  데이터 파싱 실패: {e}")

            try:
                browser.stop()
            except:
                pass

    except ImportError:
        print("⚠️  nodriver가 설치되어 있지 않습니다")

    print("\n" + "="*60)


# ===================================================================
# 메인 함수
# ===================================================================

async def main():
    """메인 실행 함수"""
    print("🌐 Multi-Browser Manager")
    print("Supports: nodriver, Selenium, Playwright")
    print("="*60)

    manager = BrowserVersionManager()
    manager.list_all()

    if not manager.chrome_versions and not manager.firefox_versions:
        print("\n❌ 설치된 브라우저가 없습니다!")
        print("먼저 브라우저를 설치하세요:")
        print("  ./install-chrome-versions.sh all")
        print("  ./install-firefox-versions.sh all")
        return

    print("\n실행할 예제를 선택하세요:")
    print("1. nodriver - Chrome")
    print("2. Selenium - Chrome")
    print("3. Selenium - Firefox")
    print("4. Playwright - Chrome")
    print("5. Playwright - Firefox")
    print("6. TLS 핑거프린팅 비교")
    print("0. 모든 예제 실행")

    choice = input("\n선택 (0-6): ").strip()

    examples = {
        "1": ("async", example_nodriver_chrome),
        "2": ("sync", example_selenium_chrome),
        "3": ("sync", example_selenium_firefox),
        "4": ("async", example_playwright_chrome),
        "5": ("async", example_playwright_firefox),
        "6": ("async", example_fingerprint_comparison),
    }

    if choice == "0":
        # 모든 예제 실행
        for mode, func in examples.values():
            try:
                if mode == "async":
                    await func(manager)
                else:
                    func(manager)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️  오류 발생: {e}")
    elif choice in examples:
        mode, func = examples[choice]
        try:
            if mode == "async":
                await func(manager)
            else:
                func(manager)
        except Exception as e:
            print(f"⚠️  오류 발생: {e}")
    else:
        print("잘못된 선택입니다")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
