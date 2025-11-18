# 배포 가이드 (Deployment Guide)

Agent를 새로운 서버에 배포하는 방법입니다.

## 📋 사전 요구사항

- Linux 서버 (Ubuntu/Rocky Linux)
- Python 3.12+
- sudo 권한 (초기 설정용)
- VPN 클라이언트 (옵션)

## 🚀 배포 단계

### 1. 저장소 클론

```bash
# 원하는 디렉토리에 클론
cd ~
git clone <repository-url> agent
cd agent
```

### 2. Chrome 버전 설치

```bash
# 모든 Chrome 버전 설치 (127~144)
./install-chrome-versions.sh all

# 또는 특정 버전만
./install-chrome-versions.sh 134
```

### 3. Python 패키지 설치

```bash
# 사용자 로컬에 설치
pip install --user undetected-chromedriver selenium

# 또는 가상환경 사용
python3 -m venv venv
source venv/bin/activate
pip install undetected-chromedriver selenium
```

### 4. 기본 테스트 (VPN 없이)

```bash
# 기본 실행 테스트
python3 agent.py --version 134 --close
```

성공하면 다음 단계로 진행합니다.

## 🔐 VPN 통합 (옵션)

VPN을 사용하는 경우:

### 1. VPN 클라이언트 설치

```bash
# VPN 저장소 클론
cd ~
git clone https://github.com/service0427/vpn vpn-ip-rotation
cd vpn-ip-rotation/client

# VPN 클라이언트 설치 (sudo 필요)
sudo ./setup.sh

# VPN 서버 목록 동기화 (sudo 필요)
sudo ./sync.sh
```

### 2. VPN 명령어 설치

```bash
# vpn 명령어를 시스템에 설치
sudo cp vpn /usr/local/bin/vpn
sudo chmod +x /usr/local/bin/vpn

# 확인
which vpn
vpn 0 curl ifconfig.me  # IP 확인
```

### 3. Agent 권한 설정

```bash
cd ~/agent

# 권한 설정 스크립트 실행
./setup-permissions.sh
```

### 4. sudoers 설정

VPN 사용자 전환을 위해 sudoers 설정이 필요합니다:

```bash
# sudoers 파일 생성
sudo tee /etc/sudoers.d/vpn-access << EOF
# Allow user to switch to VPN users without password
$USER ALL=(vpn0,vpn1,vpn2,vpn3) NOPASSWD: ALL
EOF

# 권한 설정
sudo chmod 440 /etc/sudoers.d/vpn-access

# 검증
sudo visudo -c
```

### 5. VPN 테스트

```bash
cd ~/agent

# VPN 0으로 테스트
python3 agent.py --version 134 --vpn 0 --close

# VPN 1로 테스트
python3 agent.py --version 134 --vpn 1 --close

# IP가 다르게 나오는지 확인
```

## 🔧 환경별 조정

### 홈 디렉토리 경로가 다른 경우

`setup-permissions.sh` 스크립트는 자동으로 현재 사용자의 홈 디렉토리를 감지합니다.

### Python 버전이 다른 경우

VPN 스크립트에서 Python 경로 수정:

```bash
# ~/vpn-ip-rotation/client/vpn 파일 수정
# 176번째 줄의 python3.12를 실제 버전으로 변경
sudo -u "$USERNAME" env HOME="$HOME" PYTHONPATH="$HOME/.local/lib/python3.X/site-packages:$PYTHONPATH" ...
```

### 다른 사용자 이름 사용

sudoers 파일에서 사용자 이름 변경:

```bash
# $USER를 실제 사용자 이름으로 교체
your-username ALL=(vpn0,vpn1,vpn2,vpn3) NOPASSWD: ALL
```

## 📝 배포 체크리스트

- [ ] Chrome 버전 설치 확인
- [ ] Python 패키지 설치 확인
- [ ] 기본 실행 테스트 성공
- [ ] VPN 클라이언트 설치 (옵션)
- [ ] VPN 명령어 설치 (옵션)
- [ ] Agent 권한 설정 완료
- [ ] sudoers 설정 완료 (VPN 사용 시)
- [ ] VPN 실행 테스트 성공 (VPN 사용 시)

## ⚠️ 문제 해결

### Permission denied 오류

```bash
# setup-permissions.sh 재실행
./setup-permissions.sh

# 특정 디렉토리 권한 수동 설정
chmod o+rx ~
chmod -R o+rX ~/agent
chmod -R o+rwX ~/agent/browser-profiles
chmod -R o+rwX ~/.local/share/undetected_chromedriver
```

### ChromeDriver 버전 문제

```bash
# ChromeDriver 캐시 삭제
rm -rf ~/.local/share/undetected_chromedriver/*

# 다시 실행 (자동 다운로드)
python3 agent.py --version 130 --vpn 1
```

### VPN 사용자를 찾을 수 없음

```bash
# VPN 서버 재동기화
cd ~/vpn-ip-rotation/client
sudo ./sync.sh

# VPN 사용자 확인
wg show interfaces
getent passwd | grep vpn
```

## 📊 배포 검증

모든 설정이 완료되면 다음 명령어로 검증:

```bash
# Chrome 127-144 모두 테스트 (VPN 포함)
for version in 127 128 129 130 131 132 133 134; do
    echo "Testing Chrome $version with VPN 0..."
    python3 agent.py --version $version --vpn 0 --close
    if [ $? -eq 0 ]; then
        echo "✅ Chrome $version: SUCCESS"
    else
        echo "❌ Chrome $version: FAILED"
    fi
done
```

## 🔄 업데이트

기존 설치를 업데이트하는 경우:

```bash
cd ~/agent
git pull

# 권한 재설정
./setup-permissions.sh

# 새 Chrome 버전이 추가된 경우
./install-chrome-versions.sh all
```
