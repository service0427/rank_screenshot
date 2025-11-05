# VPN 키 풀 시스템 가이드

새로운 동적 키 할당/반납 방식의 VPN 시스템 사용 가이드입니다.

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [기존 시스템과의 차이](#기존-시스템과의-차이)
3. [테스트 방법](#테스트-방법)
4. [통합 방법](#통합-방법)
5. [트러블슈팅](#트러블슈팅)

---

## 시스템 개요

### 아키텍처

```
┌──────────────┐
│ VPN 키 풀    │
│ API 서버     │  ← http://112.161.221.82:3000
│              │
│ - 키 할당    │
│ - 키 반납    │
│ - 상태 조회  │
└──────────────┘
      ↕️
┌──────────────┐
│ Worker 1~N   │
│              │
│ 1. 키 할당   │
│ 2. VPN 연결  │
│ 3. 작업 실행 │
│ 4. VPN 해제  │
│ 5. 키 반납   │
└──────────────┘
```

### 주요 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/vpn/allocate` | GET | VPN 키 할당받기 |
| `/api/vpn/release` | POST | VPN 키 반납하기 |
| `/api/vpn/status` | GET | 키 풀 상태 조회 |

---

## 기존 시스템과의 차이

### 기존 방식 (고정 VPN 사용자)

```bash
# 장점:
✅ 단순한 구조 (vpn0, vpn1, vpn2...)
✅ 영구적인 설정 (재부팅 후에도 유지)

# 단점:
❌ 사용자 수 제한 (시스템 사용자 최대 개수)
❌ 동적 확장 불가
❌ IP 관리 복잡
❌ 사용자별 권한 설정 필요 (sudoers)
```

### 새로운 방식 (키 풀 방식)

```bash
# 장점:
✅ 동적 확장 가능 (100개 이상 가능)
✅ 중앙 집중식 관리
✅ 키 재사용 (할당 → 반납 → 재할당)
✅ 권한 문제 해결 (tech 사용자만 사용)
✅ 상태 모니터링 가능

# 단점:
❌ API 서버 의존성 추가
❌ 네트워크 오류 가능성
❌ 초기 구축 복잡도 증가
```

---

## 테스트 방법

### 1. Bash 스크립트 테스트 (권장)

```bash
cd /home/tech/rank_screenshot

# 단일 키 할당/반납 테스트
./test_vpn_pool.sh
```

**예상 출력:**
```
============================================================
🧪 VPN 키 풀 시스템 테스트 (Bash)
============================================================

📊 1. 서버 상태 확인
------------------------------------------------------------
{
  "total": 100,
  "available": 100,
  "allocated": 0
}

🔑 2. VPN 키 할당
------------------------------------------------------------
   ✅ VPN 키 할당 성공!
   📍 Internal IP: 10.8.0.34
   🖥️  Server: 112.161.221.82:55555
   🔐 Public Key: gsHkV1313+nIJU5h3K...

💾 3. 설정 파일 저장
------------------------------------------------------------
   ✅ 설정 파일 저장: /tmp/vpn_test_client.conf

   --- 설정 파일 앞부분 ---
   [Interface]
   PrivateKey = wBhuTSoUcawSU/cZmbnhCfzzUDNlh7PM9AfnHFxR73U=
   Address = 10.8.0.34/24
   DNS = 8.8.8.8
   ...

⏸️  4. 키 반납 준비
------------------------------------------------------------
   Enter를 누르면 키를 반납합니다...
```

### 2. Python 스크립트 테스트

```bash
# 단일 키 테스트
python3 test_vpn_pool.py

# 다중 키 테스트 (3개 워커)
python3 test_vpn_pool.py --multi
```

### 3. curl 직접 테스트

```bash
# 1. 상태 확인
curl -s http://112.161.221.82:3000/api/vpn/status | jq '.statistics'

# 2. 키 할당
RESPONSE=$(curl -s http://112.161.221.82:3000/api/vpn/allocate)
echo "$RESPONSE" | jq

# 3. Public Key 추출
PUBLIC_KEY=$(echo "$RESPONSE" | jq -r '.public_key')
echo "Public Key: $PUBLIC_KEY"

# 4. 키 반납
curl -X POST http://112.161.221.82:3000/api/vpn/release \
  -H "Content-Type: application/json" \
  -d "{\"public_key\": \"$PUBLIC_KEY\"}"
```

---

## 통합 방법

### run_workers.py 통합 예시

```python
from lib.modules.vpn_pool_client import VPNPoolClient

# VPN 키 풀 클라이언트 생성
vpn_pool = VPNPoolClient()

def run_worker(worker_id, ...):
    """개별 워커 실행"""

    # 1. VPN 키 할당받기
    key_info = vpn_pool.allocate_key(instance_id=worker_id)

    if not key_info:
        print(f"❌ Worker-{worker_id}: VPN 키 할당 실패")
        return

    try:
        # 2. WireGuard 설정 파일 저장
        config_path = f"/tmp/vpn_worker_{worker_id}.conf"
        vpn_pool.save_config_file(worker_id, config_path)

        # 3. WireGuard 연결
        subprocess.run(["sudo", "wg-quick", "up", config_path])

        # 4. 작업 실행
        run_agent_selenium_uc(...)

    finally:
        # 5. WireGuard 연결 해제
        subprocess.run(["sudo", "wg-quick", "down", config_path])

        # 6. VPN 키 반납
        vpn_pool.release_key(instance_id=worker_id)

# 모든 워커 종료 시
vpn_pool.cleanup_all()
```

### 장점

1. **자동 키 관리**: 할당 → 사용 → 반납 자동화
2. **리소스 효율**: 100개 키 풀로 수백 개 워커 지원 (순차적 사용)
3. **권한 문제 해결**: tech 사용자만으로 운영 가능
4. **확장성**: 서버만 확장하면 키 개수 무제한

---

## 트러블슈팅

### 1. 서버 연결 실패

```bash
❌ 연결 실패: VPN 키 풀 서버에 연결할 수 없음
```

**원인:**
- VPN 키 풀 서버가 시작되지 않음
- 네트워크 문제
- 방화벽 차단

**해결:**
```bash
# 서버 상태 확인
curl -v http://112.161.221.82:3000/api/vpn/status

# 핑 테스트
ping -c 3 112.161.221.82

# 포트 테스트
nc -zv 112.161.221.82 3000
```

### 2. 키 할당 실패

```bash
❌ 할당 실패: No available keys
```

**원인:**
- 모든 키가 이미 할당됨
- 반납되지 않은 키 존재

**해결:**
```bash
# 상태 확인
curl -s http://112.161.221.82:3000/api/vpn/status | jq

# 강제 재시작 (서버 측)
# 모든 키가 available 상태로 리셋됨
```

### 3. 키 반납 실패

```bash
❌ 반납 실패: Key not found
```

**원인:**
- 이미 반납된 키
- Public Key 불일치

**해결:**
```bash
# 할당된 키 정보 확인
curl -s http://112.161.221.82:3000/api/vpn/status | jq '.keys[] | select(.allocated == true)'

# 올바른 Public Key 사용
```

### 4. WireGuard 연결 실패

```bash
❌ wg-quick: interface already exists
```

**원인:**
- 이전 연결이 정리되지 않음

**해결:**
```bash
# 모든 WireGuard 인터페이스 확인
sudo wg show

# 특정 인터페이스 제거
sudo wg-quick down /tmp/vpn_worker_1.conf

# 모든 인터페이스 제거
sudo wg-quick down-all
```

---

## 다음 단계

1. **VPN 키 풀 서버 시작**
   ```bash
   # 서버 측에서 실행
   cd ~/vpn-key-pool
   npm start
   ```

2. **테스트 실행**
   ```bash
   # 클라이언트에서 실행
   cd /home/tech/rank_screenshot
   ./test_vpn_pool.sh
   ```

3. **run_workers.py 통합**
   - VPNPoolClient 통합
   - 키 할당/반납 로직 추가
   - WireGuard 연결/해제 자동화

4. **프로덕션 배포**
   - 다중 워커 테스트
   - 에러 처리 강화
   - 모니터링 추가

---

## 참고 자료

- VPN Pool Client: `lib/modules/vpn_pool_client.py`
- Test Script (Bash): `test_vpn_pool.sh`
- Test Script (Python): `test_vpn_pool.py`
- API Documentation: (서버 측 README 참고)
