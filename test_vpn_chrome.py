#!/usr/bin/env python3
"""
VPN + Chrome 테스트 스크립트

기능:
1. VPN 키 자동 할당 (http://220.121.120.83/vpn_api/allocate)
2. 순수 오리지널 Chrome 실행 (fresh profile)
3. IP 체크 페이지로 자동 이동
4. 이후 사용자가 수동으로 조작
5. 창 닫으면 VPN 키 반납 및 연결 해제

사용법:
    python3 test_vpn_chrome.py
"""

import os
import sys
import time
import random
import subprocess
import requests
import shutil
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from uc_lib.core.browser_core_uc import BrowserCoreUC


class VPNTester:
    """VPN + Chrome 테스트 클래스"""

    def __init__(self):
        self.vpn_api_base = "http://220.121.120.83/vpn_api"
        self.vpn_interface = None
        self.vpn_config_path = None
        self.vpn_public_key = None  # 반납 시 필요
        self.test_profile_dir = project_root / "test_browser_profile"

    def cleanup_old_vpn(self):
        """이전 VPN 연결 정리"""
        print("\n" + "=" * 60)
        print("🧹 이전 VPN 연결 정리")
        print("=" * 60)

        # 모든 wg 인터페이스 확인 및 종료
        try:
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )

            interfaces = []
            for line in result.stdout.split('\n'):
                if 'wg-' in line or 'wg101' in line or 'wg102' in line:
                    # 인터페이스 이름 추출
                    parts = line.split(':')
                    if len(parts) >= 2:
                        iface = parts[1].strip().split('@')[0]
                        interfaces.append(iface)

            if interfaces:
                print(f"   발견된 인터페이스: {', '.join(interfaces)}")
                for iface in interfaces:
                    try:
                        subprocess.run(
                            ["sudo", "wg-quick", "down", iface],
                            capture_output=True,
                            timeout=5
                        )
                        print(f"   ✓ {iface} 종료됨")
                    except:
                        pass
            else:
                print("   ℹ️  활성 VPN 연결 없음")

        except Exception as e:
            print(f"   ⚠️  VPN 정리 중 오류 (계속 진행): {e}")

        # /tmp/vpn_configs 정리
        config_dir = Path("/tmp/vpn_configs")
        if config_dir.exists():
            try:
                shutil.rmtree(config_dir)
                print(f"   ✓ VPN 설정 파일 삭제됨: {config_dir}")
            except:
                pass

        config_dir.mkdir(parents=True, exist_ok=True)

    def allocate_vpn_key(self):
        """VPN 키 할당"""
        print("\n" + "=" * 60)
        print("🔑 VPN 키 할당")
        print("=" * 60)
        print(f"   API: {self.vpn_api_base}/allocate")

        try:
            response = requests.get(f"{self.vpn_api_base}/allocate", timeout=10)
            response.raise_for_status()

            data = response.json()

            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                print(f"   ✗ VPN 키 할당 실패: {error_msg}")
                return None

            print(f"   ✓ VPN 키 할당 성공")
            print(f"   서버: {data['server_ip']}:{data.get('server_port', 51820)}")
            print(f"   내부 IP: {data['internal_ip']}")

            return data

        except Exception as e:
            print(f"   ✗ VPN 키 할당 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def connect_vpn(self, vpn_data):
        """VPN 연결"""
        print("\n" + "=" * 60)
        print("🔐 VPN 연결 중")
        print("=" * 60)

        try:
            # 내부 IP에서 인터페이스 이름 생성 (wg-10-8-0-14 형식)
            internal_ip = vpn_data['internal_ip']
            interface_name = 'wg-' + internal_ip.replace('.', '-')

            print(f"   인터페이스: {interface_name}")
            print(f"   내부 IP: {internal_ip}")
            print(f"   서버: {vpn_data['server_ip']}:{vpn_data.get('server_port', 51820)}")

            # WireGuard 설정 파일 생성
            config_dir = Path("/tmp/vpn_configs")
            config_dir.mkdir(parents=True, exist_ok=True)

            config_path = config_dir / f"{interface_name}.conf"

            # Gateway 계산 (API에 없으면 internal_ip 기반으로 계산)
            gateway = vpn_data.get('gateway')
            if not gateway:
                # 10.8.0.14 → 10.8.0.1
                ip_parts = internal_ip.split('.')
                ip_parts[-1] = '1'
                gateway = '.'.join(ip_parts)
                print(f"   ℹ️  Gateway 미제공 - 계산된 값 사용: {gateway}")
            else:
                print(f"   게이트웨이: {gateway}")

            # 엔드포인트 생성
            server_ip = vpn_data['server_ip']
            server_port = vpn_data.get('server_port', 51820)
            endpoint = f"{server_ip}:{server_port}"

            # WireGuard 설정 작성
            config_content = f"""[Interface]
PrivateKey = {vpn_data['private_key']}
Address = {internal_ip}/24
DNS = 8.8.8.8, 8.8.4.4
Table = off

[Peer]
PublicKey = {vpn_data['server_pubkey']}
Endpoint = {endpoint}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

            config_path.write_text(config_content)
            os.chmod(config_path, 0o600)
            print(f"   ✓ 설정 파일 생성: {config_path}")

            # public_key 저장 (나중에 반납 시 사용)
            self.vpn_public_key = vpn_data['public_key']

            # WireGuard 인터페이스 시작
            print(f"   🔄 WireGuard 연결 중...")
            result = subprocess.run(
                ["sudo", "wg-quick", "up", str(config_path)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"   ✗ WireGuard 연결 실패:")
                print(result.stderr)
                return None

            print(f"   ✓ WireGuard 연결 성공!")

            # 라우팅 테이블 설정 (UID 1000 = tech 사용자)
            # tech 사용자의 모든 트래픽을 이 VPN으로 라우팅
            table_num = 200  # 테스트용 고정 테이블

            # 기존 룰 삭제 (있으면)
            subprocess.run(
                ["sudo", "ip", "rule", "del", "uidrange", "1000-1000", "table", str(table_num)],
                capture_output=True
            )

            # 새 룰 추가
            subprocess.run(
                ["sudo", "ip", "rule", "add", "uidrange", "1000-1000", "table", str(table_num)],
                check=True
            )

            # 라우팅 테이블에 기본 경로 추가
            subprocess.run(
                ["sudo", "ip", "route", "add", "default", "via", gateway, "dev", interface_name, "table", str(table_num)],
                check=True
            )

            print(f"   ✓ 라우팅 설정 완료 (Table {table_num}, UID 1000)")

            # 연결 확인 (ping 3회)
            print(f"   🔄 연결 확인 중...")
            ping_success = 0
            for i in range(3):
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    ping_success += 1
                time.sleep(0.3)

            if ping_success >= 2:
                print(f"   ✓ VPN 연결 확인 완료 ({ping_success}/3)")
            else:
                print(f"   ⚠️  VPN 연결 불안정 ({ping_success}/3)")

            self.vpn_interface = interface_name
            self.vpn_config_path = config_path

            return interface_name

        except Exception as e:
            print(f"   ✗ VPN 연결 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def disconnect_vpn(self):
        """VPN 연결 해제 및 키 반납"""
        if not self.vpn_interface:
            return

        print("\n" + "=" * 60)
        print("🔌 VPN 연결 해제")
        print("=" * 60)

        try:
            # WireGuard 인터페이스 종료
            subprocess.run(
                ["sudo", "wg-quick", "down", self.vpn_interface],
                capture_output=True,
                timeout=10
            )
            print(f"   ✓ {self.vpn_interface} 종료됨")

            # 라우팅 룰 제거
            subprocess.run(
                ["sudo", "ip", "rule", "del", "uidrange", "1000-1000", "table", "200"],
                capture_output=True
            )
            print(f"   ✓ 라우팅 룰 제거됨")

            # 설정 파일 삭제
            if self.vpn_config_path and self.vpn_config_path.exists():
                self.vpn_config_path.unlink()
                print(f"   ✓ 설정 파일 삭제됨")

            # VPN 키 반납
            if self.vpn_public_key:
                self.release_vpn_key(self.vpn_public_key)

        except Exception as e:
            print(f"   ⚠️  VPN 해제 중 오류: {e}")

    def release_vpn_key(self, public_key: str):
        """VPN 키 반납"""
        print("\n" + "=" * 60)
        print("🔓 VPN 키 반납")
        print("=" * 60)

        try:
            response = requests.post(
                f"{self.vpn_api_base}/release",
                json={'public_key': public_key},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            if data.get('success'):
                print(f"   ✓ VPN 키 반납 완료")
            else:
                error_msg = data.get('error', 'Unknown error')
                print(f"   ⚠️  VPN 키 반납 실패: {error_msg}")

        except Exception as e:
            print(f"   ⚠️  VPN 키 반납 중 오류: {e}")

    def cleanup_test_profile(self):
        """테스트 프로필 삭제"""
        if self.test_profile_dir.exists():
            try:
                shutil.rmtree(self.test_profile_dir)
                print(f"   ✓ 테스트 프로필 삭제됨: {self.test_profile_dir}")
            except Exception as e:
                print(f"   ⚠️  프로필 삭제 실패: {e}")

    def run(self):
        """메인 실행"""
        driver = None
        core = None

        try:
            # 1. 이전 VPN 연결 정리
            self.cleanup_old_vpn()

            # 2. 테스트 프로필 삭제 (항상 새로운 시작)
            print("\n" + "=" * 60)
            print("🧹 테스트 프로필 정리")
            print("=" * 60)
            self.cleanup_test_profile()

            # 3. VPN 키 할당
            vpn_data = self.allocate_vpn_key()
            if not vpn_data:
                print("\n❌ VPN 키 할당 실패")
                return

            # 4. VPN 연결
            interface = self.connect_vpn(vpn_data)
            if not interface:
                print("\n❌ VPN 연결 실패")
                return

            # 6. 안정화 대기
            print("\n   ⏳ 안정화 대기 중 (1초)...")
            time.sleep(1)

            # 7. Chrome 실행 (fresh profile)
            print("\n" + "=" * 60)
            print("🌐 Chrome 실행")
            print("=" * 60)

            core = BrowserCoreUC(
                version="144",  # 최신 안정 버전
                instance_id=1,
                user_data_dir=str(self.test_profile_dir)
            )

            driver = core.launch(use_profile=True, fresh_profile=True)

            if not driver:
                print("\n❌ Chrome 실행 실패")
                return

            print("   ✓ Chrome 실행 성공")

            # 8. IP 체크 페이지로 이동
            print("\n" + "=" * 60)
            print("🌐 IP 체크")
            print("=" * 60)

            driver.get("https://api.ipify.org?format=text")
            time.sleep(1)

            external_ip = driver.find_element("tag name", "body").text.strip()
            print(f"\n   ✅ 외부 IP: {external_ip}")
            print(f"   📍 내부 IP: {vpn_data['internal_ip']}")
            print(f"   🌐 VPN 서버: {vpn_data['server_ip']}")
            print(f"   🔌 인터페이스: {interface}")

            # 9. 사용자에게 제어권 넘김
            print("\n" + "=" * 60)
            print("✋ 사용자 제어 모드")
            print("=" * 60)
            print("   ℹ️  이제 직접 브라우저를 조작하세요.")
            print("   ℹ️  브라우저 창을 닫으면 VPN 연결이 해제되고 종료됩니다.")
            print("=" * 60)

            # 10. 브라우저가 닫힐 때까지 대기
            while True:
                try:
                    # 브라우저가 살아있는지 체크
                    driver.current_url
                    time.sleep(1)
                except:
                    # 브라우저가 닫힘
                    print("\n   ℹ️  브라우저가 닫혔습니다.")
                    break

        except KeyboardInterrupt:
            print("\n\n   ⚠️  사용자가 중단함 (Ctrl+C)")

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # 11. 정리
            print("\n" + "=" * 60)
            print("🧹 정리 작업")
            print("=" * 60)

            # 브라우저 종료
            if driver:
                try:
                    driver.quit()
                    print("   ✓ 브라우저 종료됨")
                except:
                    pass

            # VPN 연결 해제
            self.disconnect_vpn()

            # 테스트 프로필 삭제
            self.cleanup_test_profile()

            print("\n✅ 모든 작업 완료!")


def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════════════════════╗
║         VPN + Chrome 테스트 스크립트                      ║
╚══════════════════════════════════════════════════════════╝

기능:
  1. VPN 키 자동 할당 (http://220.121.120.83/vpn_api/allocate)
  2. Fresh Chrome 프로필 실행
  3. IP 체크 자동 실행
  4. 사용자가 직접 조작 가능
  5. 브라우저 닫으면 VPN 키 반납 및 연결 해제

주의:
  - 재실행 시 이전 VPN 연결 자동 정리
  - 프로필은 항상 새롭게 시작 (test_browser_profile)
  - sudo 권한 필요 (WireGuard 제어)
  - VPN 키는 사용 후 자동 반납됨

""")

    tester = VPNTester()
    tester.run()


if __name__ == "__main__":
    main()
