# 배포 서버 권한 문제 해결 가이드

## 문제: Permission Denied (배포 서버)

배포 서버에서 `python3: can't open file 'uc_agent.py' : [Errno 13] Permission denied` 오류가 발생하는 경우 해결 방법입니다.

---

## 🔍 1단계: 진단

배포 서버에서 다음 스크립트를 실행하여 문제를 진단합니다:

```bash
cd /path/to/rank_screenshot
./debug_permissions.sh
```

이 스크립트는 다음을 확인합니다:
- ✅ 파일 권한
- ✅ 디렉토리 권한
- ✅ wg 사용자 존재 여부
- ✅ Python 경로
- ✅ 실제 파일 읽기 테스트
- ✅ 보안 모듈 (SELinux/AppArmor)

---

## 🛠️ 2단계: 자동 수정

### 방법 1: setup.sh 재실행 (권장)

```bash
cd /path/to/rank_screenshot
./setup.sh
```

**setup.sh가 자동으로 설정하는 권한:**
- ✅ Python 파일: `755` (world-readable & executable)
- ✅ Python 모듈 (.py): `644` (world-readable)
- ✅ 디렉토리: `755` (world-executable)
- ✅ 상위 디렉토리: 읽기/실행 권한 부여

### 방법 2: 수동 권한 설정

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/rank_screenshot

# 1. 메인 Python 파일 권한
chmod 755 uc_agent.py
chmod 755 uc_run_workers.py

# 2. 프로젝트 루트 디렉토리
chmod 755 .

# 3. 상위 디렉토리 (예: /home/tech)
chmod o+rx "$(dirname "$(pwd)")"

# 4. Python 모듈 디렉토리
find common -type d -exec chmod 755 {} \;
find common -type f -name "*.py" -exec chmod 644 {} \;

find uc_lib -type d -exec chmod 755 {} \;
find uc_lib -type f -name "*.py" -exec chmod 644 {} \;

# 5. Chrome 바이너리 디렉토리
find chrome-version -type d -exec chmod 755 {} \;
```

---

## 🐛 3단계: 일반적인 원인과 해결

### 원인 1: 상위 디렉토리 권한 부족

**증상:**
```
Permission denied: '/home/tech/rank_screenshot/uc_agent.py'
```

**해결:**
```bash
# 홈 디렉토리에 실행 권한 부여
chmod o+rx /home/tech

# 프로젝트 디렉토리에 실행 권한 부여
chmod o+rx /home/tech/rank_screenshot
```

**원리:**
- `/home/tech/rank_screenshot/uc_agent.py`에 접근하려면
- `/home` → `/home/tech` → `/home/tech/rank_screenshot` 모두 실행(x) 권한 필요

---

### 원인 2: Python 파일 자체의 읽기 권한 부족

**증상:**
```
wg101이 uc_agent.py를 읽을 수 없음
```

**해결:**
```bash
chmod 755 /home/tech/rank_screenshot/uc_agent.py
```

**권장 권한:**
- `755` (rwxr-xr-x): 소유자는 전체, 기타는 읽기/실행
- `644` (rw-r--r--): Python 모듈 파일

---

### 원인 3: wg 사용자가 없음

**증상:**
```
✗ wg101 (없음)
```

**해결:**
```bash
# wg101-112 사용자 생성
for i in {101..112}; do
    user="wg$i"
    uid=$((1000 + i))

    # 사용자가 없으면 생성
    if ! id "$user" &>/dev/null; then
        sudo useradd -m -s /bin/bash -u "$uid" "$user"
        echo "✓ $user (UID: $uid) 생성 완료"
    fi
done
```

---

### 원인 4: Python 인터프리터 경로 차이

**증상:**
```
python3: command not found
```

**해결:**
```bash
# Python3 설치 확인
which python3

# 없으면 설치
sudo apt-get update
sudo apt-get install -y python3 python3-pip
```

---

### 원인 5: SELinux 또는 AppArmor

**증상:**
```
SELinux: Enforcing
```

**해결:**

#### SELinux (RHEL/CentOS)
```bash
# 임시 비활성화 (재부팅 시 복원)
sudo setenforce 0

# 영구 비활성화
sudo vi /etc/selinux/config
# SELINUX=disabled 로 변경

# 또는 컨텍스트 수정
sudo chcon -R -t bin_t /home/tech/rank_screenshot/uc_agent.py
```

#### AppArmor (Ubuntu/Debian)
```bash
# Python3 프로필 비활성화
sudo ln -s /etc/apparmor.d/usr.bin.python3 /etc/apparmor.d/disable/
sudo apparmor_parser -R /etc/apparmor.d/usr.bin.python3
```

---

## 📋 4단계: 검증

### 테스트 1: wg101로 파일 읽기
```bash
sudo -u wg101 cat /home/tech/rank_screenshot/uc_agent.py > /dev/null
echo $?  # 0이어야 성공
```

### 테스트 2: wg101로 Python 실행
```bash
sudo -u wg101 python3 -c "print('Hello')"
# Hello 출력되어야 함
```

### 테스트 3: wg101로 uc_agent.py 실행
```bash
sudo -u wg101 python3 /home/tech/rank_screenshot/uc_agent.py --help
# 도움말이 출력되어야 함
```

### 테스트 4: 실제 워커 실행
```bash
cd /home/tech/rank_screenshot
python3 uc_run_workers.py -t 1 -i 1 --local
# VPN 없이 1회 실행 (로컬 모드)
```

---

## 🎯 5단계: 최종 체크리스트

배포 서버에서 다음을 모두 확인:

- [ ] `./debug_permissions.sh` 실행 결과 모두 ✓
- [ ] wg101-112 사용자 존재 (`id wg101`)
- [ ] uc_agent.py 권한: `755` (`ls -la uc_agent.py`)
- [ ] 프로젝트 디렉토리 권한: `755` (`ls -ld .`)
- [ ] 상위 디렉토리 권한: `o+rx` (`ls -ld ..`)
- [ ] Python 모듈 권한: `644` (`find common -name "*.py" -exec ls -l {} \;`)
- [ ] SELinux/AppArmor 비활성화 또는 설정 완료
- [ ] wg101로 uc_agent.py --help 실행 성공
- [ ] `python3 uc_run_workers.py -t 1 -i 1 --local` 실행 성공

---

## 💡 추가 팁

### 전체 권한 777 사용하지 말 것

**❌ 나쁜 방법:**
```bash
chmod -R 777 /home/tech/rank_screenshot
```

**이유:**
- 보안 위험 (누구나 파일 수정 가능)
- 일부 시스템에서 실행 거부 (security policy)

**✅ 올바른 방법:**
```bash
# 디렉토리: 755 (rwxr-xr-x)
find /home/tech/rank_screenshot -type d -exec chmod 755 {} \;

# Python 실행 파일: 755
chmod 755 /home/tech/rank_screenshot/uc_agent.py

# Python 모듈: 644 (rw-r--r--)
find /home/tech/rank_screenshot -type f -name "*.py" -exec chmod 644 {} \;
```

### wg 사용자 홈 디렉토리 권한

wg101-112 사용자의 홈 디렉토리도 권한 확인:
```bash
# 홈 디렉토리 생성 및 권한 설정
for i in {101..112}; do
    user="wg$i"
    home="/home/$user"

    if [ -d "$home" ]; then
        sudo chown -R "$user:$user" "$home"
        chmod 755 "$home"

        # .cache, .local 디렉토리
        sudo -u "$user" mkdir -p "$home/.cache" "$home/.local/share"
        sudo chown -R "$user:$user" "$home/.cache" "$home/.local"
    fi
done
```

---

## 🚨 긴급 복구

모든 방법이 실패하면:

```bash
# 1. 전체 재설치
cd /home/tech
rm -rf rank_screenshot
git clone https://github.com/service0427/rank_screenshot.git
cd rank_screenshot
./setup.sh

# 2. 권한 강제 설정
sudo chmod -R o+rX /home/tech/rank_screenshot
sudo chmod 755 /home/tech/rank_screenshot/uc_agent.py
sudo chmod 755 /home/tech/rank_screenshot/uc_run_workers.py

# 3. wg 사용자 재생성
for i in {101..112}; do
    user="wg$i"
    sudo userdel -r "$user" 2>/dev/null
    sudo useradd -m -s /bin/bash -u $((1000 + i)) "$user"
done

# 4. 테스트
./debug_permissions.sh
```

---

## 📞 문제 지속 시

위 모든 방법을 시도했는데도 문제가 지속되면:

1. `./debug_permissions.sh` 출력 결과 전체 복사
2. GitHub Issue에 보고
3. 다음 정보 포함:
   - OS 버전 (`cat /etc/os-release`)
   - Python 버전 (`python3 --version`)
   - 에러 로그 전체
   - debug_permissions.sh 출력 전체
