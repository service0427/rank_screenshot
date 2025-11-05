# VPN 키 풀 시스템 통합 가이드

agent.py와 run_workers.py에 VPN 키 풀 시스템을 통합하는 방법

## 📋 통합 전 준비사항

### 1. WireGuard 설치 확인

```bash
# WireGuard 설치 여부 확인
which wg-quick

# 없으면 설치
sudo apt update && sudo apt install wireguard
```

### 2. sudoers 설정 (필수!)

```bash
# sudoers 설정 스크립트 실행
./setup-vpn-pool-sudoers.sh

# 테스트
sudo wg-quick  # 비밀번호 없이 Usage 메시지 출력되어야 함
```

**중요:** 이 설정이 없으면 VPN 키 풀 시스템을 사용할 수 없습니다!

---

## 🔧 agent.py 통합

### 기존 방식 vs 새로운 방식

**기존 방식 (고정 VPN 사용자):**
```bash
# VPN 0 사용 (os.execvpe로 vpn 명령어 실행)
python3 agent.py --vpn 0 --keyword "노트북"
```

**새로운 방식 (VPN 키 풀):**
```bash
# VPN 키 풀에서 자동 할당
python3 agent.py --vpn-pool --keyword "노트북"
```

### 통합 코드 예시

#### 1. Import 추가

```python
from lib.modules.vpn_pool_manager import VPNPoolManager
```

#### 2. argparse 옵션 추가

```python
parser.add_argument(
    "--vpn-pool",
    action="store_true",
    help="VPN 키 풀 사용 (자동 할당/반납)"
)
```

#### 3. run_agent_selenium_uc 함수 수정

```python
def run_agent_selenium_uc(
    instance_id: int = 1,
    # ... 기존 파라미터 ...
    vpn_pool: bool = False,  # 추가
    proxy_address: str = None
):
    """Selenium + undetected-chromedriver 에이전트 실행"""

    vpn_manager = None
    vpn_conn_info = None

    try:
        # === VPN 키 풀 연결 (브라우저 시작 전) ===
        if vpn_pool:
            print("\n" + "=" * 60)
            print("🔐 VPN 키 풀 연결")
            print("=" * 60)

            vpn_manager = VPNPoolManager()
            vpn_conn_info = vpn_manager.connect(instance_id=instance_id)

            if not vpn_conn_info:
                print("❌ VPN 연결 실패 - Agent 종료")
                return

            print(f"✅ VPN 연결 완료: {vpn_conn_info['internal_ip']}")
            print("=" * 60 + "\n")

        # === 브라우저 초기화 ===
        core = BrowserCoreUC(instance_id=instance_id)
        driver = core.launch(...)

        # ... 기존 워크플로우 ...

    finally:
        # === VPN 연결 해제 ===
        if vpn_manager and vpn_conn_info:
            vpn_manager.disconnect(instance_id=instance_id)

        # ... 기존 정리 코드 ...
```

#### 4. 메인 함수 수정

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(...)

    # VPN 키 풀 옵션 추가
    parser.add_argument("--vpn-pool", action="store_true", ...)

    args = parser.parse_args()

    # run_agent_selenium_uc 호출 시 vpn_pool 전달
    run_agent_selenium_uc(
        instance_id=args.instance,
        # ... 기존 파라미터 ...
        vpn_pool=args.vpn_pool,  # 추가
    )
```

---

## 🔧 run_workers.py 통합

### 기존 방식 vs 새로운 방식

**기존 방식 (고정 VPN 리스트):**
```bash
# VPN 0~36 중 랜덤 선택
python3 run_workers.py -t 6
```

**새로운 방식 (VPN 키 풀):**
```bash
# VPN 키 풀에서 자동 할당 (51개+)
python3 run_workers.py --use-vpn-pool -t 6
```

### 통합 코드 예시

#### 1. Import 추가

```python
from lib.modules.vpn_pool_manager import get_vpn_pool_manager
```

#### 2. argparse 옵션 추가

```python
parser.add_argument(
    "--use-vpn-pool",
    action="store_true",
    help="VPN 키 풀 사용 (기존 VPN 대신)"
)
```

#### 3. run_worker 함수 수정

```python
def run_worker(worker_id: int, iterations: int, use_vpn_pool: bool = False, ...):
    """개별 워커 실행"""

    vpn_manager = None
    vpn_conn_info = None

    # VPN 키 풀 매니저 가져오기 (공유 인스턴스)
    if use_vpn_pool:
        vpn_manager = get_vpn_pool_manager()

    while True:
        i += 1
        if not is_infinite and i > iterations:
            break

        try:
            # === VPN 연결 (키 풀 사용 시) ===
            if use_vpn_pool:
                print(f"\n[Worker-{worker_id}] 🔐 VPN 키 할당 중...")
                vpn_conn_info = vpn_manager.connect(instance_id=worker_id)

                if not vpn_conn_info:
                    print(f"[Worker-{worker_id}] ❌ VPN 연결 실패 - 1분 후 재시도")
                    time.sleep(60)
                    continue

                print(f"[Worker-{worker_id}] ✅ VPN: {vpn_conn_info['internal_ip']}")

            # === Chrome 프로세스 정리 ===
            cleanup_chrome_processes(vpn=None, instance_id=worker_id)

            # === agent.py 실행 ===
            cmd = ["python3", "agent.py", "--work-api", ...]

            # VPN 키 풀 옵션 추가
            if use_vpn_pool:
                cmd.append("--vpn-pool")

            result = subprocess.run(cmd, ...)

            # ... 기존 로직 ...

        finally:
            # === VPN 연결 해제 (키 풀 사용 시) ===
            if use_vpn_pool and vpn_conn_info:
                vpn_manager.disconnect(instance_id=worker_id)
```

#### 4. 메인 함수 수정

```python
def main():
    parser = argparse.ArgumentParser(...)

    # VPN 키 풀 옵션 추가
    parser.add_argument("--use-vpn-pool", ...)

    args = parser.parse_args()

    # 스레드 생성
    for worker_id in range(1, args.threads + 1):
        thread = threading.Thread(
            target=run_worker,
            args=(worker_id, args.iterations, ..., args.use_vpn_pool),  # 추가
        )
        threads.append(thread)
        thread.start()

    # 프로그램 종료 시 모든 VPN 연결 해제
    if args.use_vpn_pool:
        vpn_manager = get_vpn_pool_manager()
        vpn_manager.disconnect_all()
```

---

## 🧪 테스트 방법

### 1. 단일 Agent 테스트

```bash
# VPN 키 풀로 단일 실행
python3 agent.py --vpn-pool --keyword "노트북" --close
```

**예상 출력:**
```
🔐 VPN 키 풀 연결
============================================================
🔐 VPN 연결 중... (Worker-1)
🔑 VPN 키 할당 요청 중... (Worker-1)
   ✅ VPN 키 할당 성공!
   📍 Internal IP: 10.8.0.34
   💾 설정 파일 저장: /tmp/vpn_configs/worker_1.conf
   ✅ VPN 연결 성공!
   📍 Internal IP: 10.8.0.34
   🌐 Interface: wg-worker-1
✅ VPN 연결 완료: 10.8.0.34
============================================================

... (쿠팡 워크플로우 진행) ...

🔌 VPN 연결 해제 중... (Worker-1)
   ✅ WireGuard 연결 해제 성공
🔓 VPN 키 반납 중... (Worker-1)
   ✅ VPN 키 반납 성공!
```

### 2. 다중 Worker 테스트

```bash
# 3개 워커로 VPN 키 풀 사용
python3 run_workers.py --use-vpn-pool -t 3 -i 1
```

**예상 동작:**
1. Worker-1: VPN 키 할당 (10.8.0.34) → 작업 실행 → VPN 해제
2. Worker-2: VPN 키 할당 (10.8.0.35) → 작업 실행 → VPN 해제
3. Worker-3: VPN 키 할당 (10.8.0.36) → 작업 실행 → VPN 해제

### 3. 서버 상태 모니터링

```bash
# 실시간 키 풀 상태 확인
watch -n 2 'curl -s http://112.161.221.82:3000/api/vpn/status | jq .statistics'
```

---

## 🎯 장점 및 개선사항

### 기존 방식의 문제점 (해결됨)

| 문제 | 기존 방식 | 새로운 방식 |
|------|-----------|-------------|
| **사용자 수 제한** | 36개 (vpn0~vpn35) | 51개+ (무제한) |
| **싱크 과정** | ✅ 필요 (sync.sh) | ❌ 불필요 |
| **퍼미션 설정** | ✅ 복잡 (setup-permissions.sh) | ❌ 간단 (sudoers만) |
| **사용자 전환** | ✅ sudo -u vpnN | ❌ 불필요 (tech만) |
| **동적 확장** | ❌ 불가 | ✅ 가능 |
| **중앙 관리** | ❌ 없음 | ✅ API 서버 |
| **모니터링** | ❌ 어려움 | ✅ 실시간 통계 |

### 새로운 방식의 장점

1. **동적 확장**: 51개 키로 수백 개 워커 지원 (순차 사용)
2. **간편한 관리**: tech 사용자만으로 모든 작업 가능
3. **자동화**: 키 할당/반납 자동 처리
4. **모니터링**: API로 실시간 상태 확인
5. **안정성**: 중앙 집중식 키 관리

---

## 🚨 주의사항

### 1. sudoers 설정 필수

VPN 키 풀 시스템을 사용하려면 **반드시** sudoers 설정이 필요합니다:

```bash
./setup-vpn-pool-sudoers.sh
```

### 2. WireGuard 인터페이스 충돌 방지

각 워커는 고유한 인터페이스 이름을 사용합니다:
- Worker-1: `wg-worker-1`
- Worker-2: `wg-worker-2`
- ...

동일한 instance_id로 중복 연결 시 충돌 발생 가능!

### 3. 키 반납 중요성

**반드시** VPN 연결 해제 시 키를 반납해야 합니다!
- 반납하지 않으면 키가 고갈됨
- finally 블록에서 반납 처리 필수

### 4. API 서버 의존성

VPN 키 풀 API 서버가 다운되면 모든 워커가 중단됩니다:
- API 서버 모니터링 필요
- 폴백 로직 고려 (로컬 모드로 전환)

---

## 📊 성능 비교

### 기존 방식 (고정 36개)

```
동시 실행 가능: 36개 워커
확장성: ❌
관리: 복잡
```

### 새로운 방식 (키 풀 51개)

```
동시 실행 가능: 51개 워커
순차 사용: 수백 개 워커 가능
확장성: ✅
관리: 간단
```

**예시:**
- 100개 워커 실행
- 각 작업 평균 2분 소요
- 51개 키로 순차 처리
- 모든 작업 완료: 약 4분

---

## 📝 다음 단계

1. **sudoers 설정**:
   ```bash
   ./setup-vpn-pool-sudoers.sh
   ```

2. **agent.py 수정**: 이 가이드 참고하여 통합

3. **run_workers.py 수정**: 이 가이드 참고하여 통합

4. **테스트**: 단일 → 다중 워커 순서로 테스트

5. **프로덕션 배포**: 안정화 후 배포

---

## 🆘 트러블슈팅

### "sudo: a password is required"

**원인:** sudoers 설정이 안 되었거나 잘못됨

**해결:**
```bash
./setup-vpn-pool-sudoers.sh
```

### "wg-quick: command not found"

**원인:** WireGuard 미설치

**해결:**
```bash
sudo apt update && sudo apt install wireguard
```

### "No available keys"

**원인:** 모든 키가 이미 할당됨

**해결:**
```bash
# 서버 상태 확인
curl -s http://112.161.221.82:3000/api/vpn/status | jq

# 대기 후 재시도 또는 서버 측 키 강제 반납
```

### IP가 변경되지 않음

**원인:** WireGuard 라우팅 문제

**해결:**
```bash
# 인터페이스 확인
sudo wg show

# 라우팅 확인
ip route

# 재연결
sudo wg-quick down /tmp/vpn_configs/worker_1.conf
sudo wg-quick up /tmp/vpn_configs/worker_1.conf
```

---

**완료 후 기존 VPN 시스템 제거 가능:**
- `~/vpn-ip-rotation/client/sync.sh` 불필요
- `setup-vpn-sudoers.sh` (기존) 불필요
- vpn0~vpn36 사용자 유지 또는 제거 가능
