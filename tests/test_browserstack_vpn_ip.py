#!/usr/bin/env python3
"""
BrowserStack Local + VPN IP 변경 테스트
- VPN 연결 시 BrowserStack 모바일 디바이스가 동일한 IP 사용하는지 확인
- 랜덤 모바일 디바이스로 테스트
"""

import os
import sys
import time
import json
import argparse
import subprocess
import random
import requests
from pathlib import Path
from datetime import datetime

# BrowserStack credentials
BROWSERSTACK_USERNAME = os.getenv("BROWSERSTACK_USERNAME", "bsuser_wHW2oU")
BROWSERSTACK_ACCESS_KEY = os.getenv("BROWSERSTACK_ACCESS_KEY", "fuymXXoQNhshiN5BsZhp")
BROWSERSTACK_HUB = f"https://{BROWSERSTACK_USERNAME}:{BROWSERSTACK_ACCESS_KEY}@hub-cloud.browserstack.com/wd/hub"

# BrowserStack Local binary path (Linux용)
BSLOCAL_PATH = Path(__file__).parent / 'tools' / 'BrowserStackLocal'


class BrowserStackLocalManager:
    """BrowserStack Local tunnel manager (Linux)"""

    def __init__(self, access_key, binary_path=None):
        self.access_key = access_key
        self.binary_path = binary_path or BSLOCAL_PATH
        self.process = None

    def download_binary(self):
        """Download BrowserStack Local binary for Linux"""
        print("\n[BrowserStack Local] Downloading binary for Linux...")

        # Create tools directory
        tools_dir = self.binary_path.parent
        tools_dir.mkdir(parents=True, exist_ok=True)

        # Download URL for Linux
        download_url = "https://www.browserstack.com/browserstack-local/BrowserStackLocal-linux-x64.zip"

        try:
            import urllib.request
            import zipfile

            zip_path = tools_dir / 'BrowserStackLocal.zip'

            print(f"  Downloading from: {download_url}")
            urllib.request.urlretrieve(download_url, zip_path)

            print(f"  Extracting to: {tools_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tools_dir)

            # Make binary executable
            self.binary_path.chmod(0o755)

            # Remove zip file
            zip_path.unlink()

            print(f"  ✅ Binary downloaded: {self.binary_path}")
            return True

        except Exception as e:
            print(f"  ❌ Download failed: {e}")
            return False

    def start(self, force_local=True, verbose=False):
        """Start BrowserStack Local tunnel"""

        # Check if binary exists
        if not self.binary_path.exists():
            print(f"[ERROR] BrowserStack Local binary not found: {self.binary_path}")
            print("\nDownloading binary automatically...")
            if not self.download_binary():
                print("\n[ERROR] Failed to download binary. Please download manually from:")
                print("        https://www.browserstack.com/local-testing/automate")
                return False

        print(f"\n[BrowserStack Local] Starting tunnel...")
        print(f"  Binary: {self.binary_path}")

        # Build command
        cmd = [
            str(self.binary_path),
            '--key', self.access_key,
        ]

        if force_local:
            cmd.append('--force-local')

        if verbose:
            cmd.append('--verbose')

        try:
            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for tunnel to be ready
            print("  Waiting for tunnel connection...")
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)

                # Check if process is still running
                if self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    print(f"\n[ERROR] Tunnel process exited unexpectedly:")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False

                # Simple check: if process alive for 10s, assume connected
                if i >= 10:
                    print(f"  ✅ Tunnel connected ({i+1}s)")
                    return True

            print(f"  ❌ Tunnel connection timeout ({max_wait}s)")
            self.stop()
            return False

        except Exception as e:
            print(f"  ❌ Failed to start tunnel: {e}")
            return False

    def stop(self):
        """Stop BrowserStack Local tunnel"""
        if self.process:
            print("\n[BrowserStack Local] Stopping tunnel...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                print("  ✅ Tunnel stopped")
            except subprocess.TimeoutExpired:
                print("  ⚠️  Force killing tunnel...")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                print(f"  ⚠️  Error stopping tunnel: {e}")
            finally:
                self.process = None


def get_local_ip():
    """Get local IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        data = response.json()
        return data.get('ip', 'Unknown')
    except Exception as e:
        print(f"  ⚠️  Failed to get local IP: {e}")
        return 'Unknown'


def get_random_device():
    """Get random mobile device configuration"""

    # Android devices only (iOS Safari는 Coupang에서 차단)
    devices = [
        {
            "device": "Samsung Galaxy S23",
            "os": "android",
            "browser": "Chrome",
            "os_version": "13.0"
        },
        {
            "device": "Samsung Galaxy S24",
            "os": "android",
            "browser": "Chrome",
            "os_version": "14.0"
        },
        {
            "device": "Google Pixel 7",
            "os": "android",
            "browser": "Chrome",
            "os_version": "13.0"
        },
        {
            "device": "OnePlus 11",
            "os": "android",
            "browser": "Chrome",
            "os_version": "13.0"
        }
    ]

    return random.choice(devices)


def test_mobile_ip(device_config):
    """Test mobile device IP through BrowserStack"""
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    device_name = device_config['device']
    os_version = device_config['os_version']
    browser = device_config['browser']

    print(f"\n[Appium] Creating session for {device_name} (Android {os_version}, {browser})...")

    # Android options
    options = UiAutomator2Options()
    options.platform_name = 'Android'
    options.browser_name = browser

    # BrowserStack specific capabilities
    bstack_options = {
        'deviceName': device_name,
        'osVersion': os_version,
        'realMobile': 'true',
        'local': 'true',  # BrowserStack Local 사용
        'debug': 'true',
        'networkLogs': 'true',
        'userName': BROWSERSTACK_USERNAME,
        'accessKey': BROWSERSTACK_ACCESS_KEY,
        'projectName': 'VPN IP Test',
        'buildName': f'IP Test - {datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'sessionName': f'{device_name} - IP Check'
    }

    options.set_capability('bstack:options', bstack_options)

    driver = None
    try:
        # Create session
        driver = webdriver.Remote(
            command_executor=BROWSERSTACK_HUB,
            options=options
        )
        print(f"  ✅ Session created: {driver.session_id}")

        # Get IP from mobile device
        print(f"\n[Mobile Device] Checking IP address...")
        driver.get('https://api.ipify.org?format=json')
        time.sleep(3)

        # Extract IP from page
        page_source = driver.page_source

        # Try to find JSON data
        import re
        json_match = re.search(r'\{[^}]*"ip"[^}]*\}', page_source)

        mobile_ip = 'Unknown'
        if json_match:
            try:
                ip_data = json.loads(json_match.group(0))
                mobile_ip = ip_data.get('ip', 'Unknown')
            except:
                pass

        if mobile_ip == 'Unknown':
            # Fallback: try to find IP pattern
            ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', page_source)
            if ip_match:
                mobile_ip = ip_match.group(0)

        print(f"  📱 Mobile Device IP: {mobile_ip}")

        return mobile_ip

    except Exception as e:
        print(f"  ❌ Failed to test mobile IP: {e}")
        import traceback
        traceback.print_exc()
        return 'Unknown'

    finally:
        if driver:
            try:
                driver.quit()
                print(f"  ✅ Session closed")
            except:
                pass


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="BrowserStack Local + VPN IP 변경 테스트"
    )

    parser.add_argument(
        "--vpn",
        type=int,
        default=0,
        help="VPN 서버 번호 (0=로컬/VPN 없음, 1+=VPN 서버 번호, 기본: 0)"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🌐 BrowserStack Local + VPN IP 변경 테스트")
    print("=" * 60)

    # VPN 정보 표시
    if args.vpn > 0:
        print(f"VPN: ✅ Server {args.vpn}")
    else:
        print(f"VPN: ❌ 로컬 IP (VPN 사용 안 함)")

    print("=" * 60 + "\n")

    # 1. 로컬 IP 확인
    print("=" * 60)
    print("📍 로컬 IP 주소 확인")
    print("=" * 60)

    local_ip = get_local_ip()

    if args.vpn > 0:
        print(f"  VPN Server {args.vpn} IP: {local_ip}")
    else:
        print(f"  로컬 IP: {local_ip}")

    print("=" * 60)

    # 2. BrowserStack Local 터널 시작
    tunnel = BrowserStackLocalManager(BROWSERSTACK_ACCESS_KEY)

    if not tunnel.start():
        print("\n❌ BrowserStack Local 터널 시작 실패")
        return 1

    try:
        # 3. 랜덤 디바이스 선택
        device_config = get_random_device()

        print("\n" + "=" * 60)
        print("📱 랜덤 모바일 디바이스 선택")
        print("=" * 60)
        print(f"  디바이스: {device_config['device']}")
        print(f"  OS: Android {device_config['os_version']}")
        print(f"  브라우저: {device_config['browser']}")
        print("=" * 60)

        # 4. 모바일 디바이스 IP 확인
        mobile_ip = test_mobile_ip(device_config)

        # 5. 결과 비교
        print("\n" + "=" * 60)
        print("📊 IP 변경 테스트 결과")
        print("=" * 60)
        print(f"  로컬 IP:      {local_ip}")
        print(f"  모바일 IP:    {mobile_ip}")
        print("=" * 60)

        if local_ip == mobile_ip and local_ip != 'Unknown':
            print("\n✅ 성공: BrowserStack Local이 VPN IP를 정상적으로 사용합니다!")
            print(f"   → 로컬 IP와 모바일 IP가 동일합니다: {local_ip}")

            if args.vpn > 0:
                print(f"   → VPN Server {args.vpn}의 IP가 모바일 디바이스에 적용되었습니다")

            return 0
        else:
            print("\n❌ 실패: IP가 일치하지 않거나 확인할 수 없습니다")

            if local_ip == 'Unknown' or mobile_ip == 'Unknown':
                print("   → IP 확인 실패")
            else:
                print("   → BrowserStack Local 터널이 제대로 작동하지 않을 수 있습니다")

            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 테스트를 중단했습니다")
        return 1

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # BrowserStack Local 터널 종료
        tunnel.stop()


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n프로그램이 종료되었습니다\n")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
