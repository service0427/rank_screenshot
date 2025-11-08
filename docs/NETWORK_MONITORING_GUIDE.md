# 네트워크 모니터링 시스템 사용 가이드

ERR_NETWORK_CHANGED 문제 디버깅을 위한 통합 모니터링 시스템

**최신 업데이트 (2025-11-07)**: 통합 이벤트 로거 추가로 **모든 워커의 동시 활동**을 단일 로그에서 확인 가능!

---

## 시스템 구성

### 1. 통합 이벤트 로거 (`common/unified_event_logger.py`) ★ NEW!
**역할**: **ERR_NETWORK_CHANGED 발생 시 다른 모든 워커의 상태를 자동 기록**

**핵심 기능**:
- ✅ 모든 워커 이벤트를 단일 로그 파일에 기록 (`/tmp/unified_events.log`)
- ✅ ERR_NETWORK_CHANGED 발생 시 **전체 워커 상태 스냅샷** 자동 생성
- ✅ 밀리초 단위 타임스탬프로 정확한 시간 차이 계산
- ✅ 워커별 마지막 이벤트 추적

**감지 이벤트**:
- 🔌 VPN 연결/해제 (CONNECTING, CONNECTED, DISCONNECTING, DISCONNECTED)
- 🚀 브라우저 시작/종료
- 🔴 ERR_NETWORK_CHANGED (자동 상관분석!)
- 📄 페이지 로드
- 🔍 검색 워크플로우

**출력 예시**:
```
[20:48:23.456] [#0001] [Worker-1    ] [wg101   ] 🔌 VPN 연결 중 | {"server_ip": "1.2.3.4", "internal_ip": "10.8.0.10"}
[20:48:24.123] [#0002] [Worker-1    ] [wg101   ] ✅ VPN 연결 완료 | {"server_ip": "1.2.3.4", "internal_ip": "10.8.0.10"}
[20:48:24.456] [#0003] [Worker-2    ] [wg102   ] 🔌 VPN 연결 중 | {"server_ip": "1.2.3.5", "internal_ip": "10.8.0.11"}
[20:48:25.789] [#0004] [Worker-3    ] [wg103   ] 🔴 ERR_NETWORK_CHANGED | {"request_id": "abc", "canceled": true}

    ==========================================================================================
    ⚠️  ERR_NETWORK_CHANGED 발생 시점의 전체 워커 상태 (영향받은 워커: Worker-3)
    ==========================================================================================
        Worker-1     | wg101    | ✅ VPN 연결 완료              | 20:48:24.123 ( -1666ms)
               └─ {"server_ip": "1.2.3.4", "internal_ip": "10.8.0.10"}
        Worker-2     | wg102    | 🔌 VPN 연결 중                | 20:48:24.456 ( -1333ms)
               └─ {"server_ip": "1.2.3.5", "internal_ip": "10.8.0.11"}
    >>> Worker-3     | wg103    | 🔴 ERR_NETWORK_CHANGED        | 20:48:25.789 (    +0ms)
               └─ {"request_id": "abc", "canceled": true}
    ==========================================================================================
```

**★ Insight ─────────────────────────────────────**
- ERR_NETWORK_CHANGED 발생 시 **자동으로** 모든 워커의 상태를 기록합니다
- Worker-2가 VPN 연결 중일 때 Worker-3에서 에러 발생 → **Worker-2의 VPN 연결이 원인**일 가능성 높음
- 시간 차이 (예: -1333ms)로 어떤 워커의 활동이 에러와 관련있는지 즉시 파악 가능
─────────────────────────────────────────────────

### 2. 시스템 네트워크 이벤트 모니터 (`monitor_network_events.py`)
**역할**: WireGuard 인터페이스 및 라우팅 변경사항 실시간 추적

**감지 항목**:
- 🟢 WireGuard 인터페이스 추가/제거 (wg101-112)
- 📋 라우팅 규칙 변경 (UID 정책 라우팅)
- 🛤️  라우팅 테이블 변경 (Table 101-112)

**출력 예시**:
```
[20:48:23.456] [EVENT] 🟢 [#1] 인터페이스 추가: wg101
[20:48:23.458] [EVENT] 📋 [#2] 라우팅 규칙 추가 (Worker-1): 10101:  from all uidrange 1101-1101 lookup 101
[20:48:23.460] [EVENT] 🛤️  [#3] 경로 추가 (Worker-1, Table 101): default dev wg101
```

### 3. CDP 네트워크 에러 모니터 (`common/network_error_monitor.py`)
**역할**: Chrome 브라우저 네트워크 에러 실시간 감지 + 통합 로거 연동

**감지 항목**:
- 🚨 ERR_NETWORK_CHANGED 오류 → **통합 로거에 자동 기록**
- ⚠️  기타 네트워크 에러 (ERR_CONNECTION_REFUSED, ERR_NAME_NOT_RESOLVED 등)
- 📄 페이지 로드 이벤트
- ❌ 콘솔 에러

**출력 예시**:
```
[20:48:25.123] [Worker-1] [CRITICAL] 🚨 ERR_NETWORK_CHANGED 감지! (발생 횟수: 1)
[20:48:25.124] [Worker-1] [CRITICAL]    요청 ID: 12345
[20:48:25.125] [Worker-1] [CRITICAL]    취소 여부: True
```

---

## 실행 방법

### 단계 1: 시스템 네트워크 모니터 시작

```bash
# 터미널 1: 시스템 네트워크 이벤트 모니터링
cd /home/tech/rank_screenshot
python3 monitor_network_events.py &

# 로그 실시간 확인
tail -f /tmp/network_events.log
```

**주요 옵션**:
- 백그라운드 실행: `&` 사용
- 로그 파일: `/tmp/network_events.log` (기본값)
- 모니터링 간격: 0.1초 (기본값)

### 단계 2: 워커 실행 (통합 로거 + CDP 모니터 자동 시작)

```bash
# 터미널 2: 8개 워커 테스트 실행
python3 uc_run_workers.py -t 8 -i 1
```

**자동 활성화**:
- ✅ **통합 이벤트 로거**: 모든 워커 이벤트 자동 기록
- ✅ **CDP 모니터**: 각 워커가 Chrome 네트워크 에러 자동 감지
- 로그 파일:
  - `/tmp/unified_events.log` - **통합 로그 (ERR_NETWORK_CHANGED 시 상관분석 자동!)**
  - `/tmp/chrome_network_errors.log` - CDP 상세 로그
  - `/tmp/network_events.log` - 시스템 네트워크 이벤트

### 단계 3: 로그 실시간 확인

```bash
# ★ 통합 로그 확인 (권장!)
tail -f /tmp/unified_events.log

# ERR_NETWORK_CHANGED 발생 시 자동으로 모든 워커 상태가 표시됩니다!

# 개별 로그도 확인 가능
tail -f /tmp/chrome_network_errors.log | grep ERR_NETWORK_CHANGED
```

---

## 상관분석 방법

### ★ 새로운 방식: 통합 로그 자동 분석 (권장!)

통합 이벤트 로거가 **ERR_NETWORK_CHANGED 발생 시 자동으로** 모든 워커 상태를 기록합니다!

**확인 방법**:
```bash
# 통합 로그에서 ERR_NETWORK_CHANGED 검색
grep -A 15 "ERR_NETWORK_CHANGED" /tmp/unified_events.log
```

**출력 예시**:
```
[20:48:25.789] [#0004] [Worker-3    ] [wg103   ] 🔴 ERR_NETWORK_CHANGED

    ==========================================================================================
    ⚠️  ERR_NETWORK_CHANGED 발생 시점의 전체 워커 상태 (영향받은 워커: Worker-3)
    ==========================================================================================
        Worker-1     | wg101    | ✅ VPN 연결 완료              | 20:48:24.123 ( -1666ms)
        Worker-2     | wg102    | 🔌 VPN 연결 중                | 20:48:24.456 ( -1333ms)  ← 의심!
    >>> Worker-3     | wg103    | 🔴 ERR_NETWORK_CHANGED        | 20:48:25.789 (    +0ms)
        Worker-4     | wg104    | 🚀 브라우저 시작 중            | 20:48:23.000 ( -2789ms)
    ==========================================================================================
```

**분석**:
- Worker-2가 VPN 연결 중 (1.3초 전) → Worker-3에서 ERR_NETWORK_CHANGED 발생
- **결론**: Worker-2의 VPN 연결로 인한 netlink 이벤트가 Worker-3에 영향

### 기존 방식: 수동 상관분석

**목표**: ERR_NETWORK_CHANGED가 발생했을 때, 어떤 워커의 VPN 연결/해제와 관련이 있는지 파악

**절차**:

1. **ERR_NETWORK_CHANGED 발생 시각 확인**:
   ```bash
   grep "ERR_NETWORK_CHANGED" /tmp/chrome_network_errors.log
   ```

   출력 예시:
   ```
   [20:48:25.123] [Worker-5] [CRITICAL] 🚨 ERR_NETWORK_CHANGED 감지!
   ```

   → 발생 시각: `20:48:25.123`

2. **동일 시각 시스템 네트워크 이벤트 확인**:
   ```bash
   grep "20:48:25" /tmp/network_events.log
   ```

   출력 예시:
   ```
   [20:48:25.100] [EVENT] 🟢 [#8] 인터페이스 추가: wg103
   [20:48:25.102] [EVENT] 📋 [#9] 라우팅 규칙 추가 (Worker-3): ...
   [20:48:25.105] [EVENT] 🛤️  [#10] 경로 추가 (Worker-3, Table 103): ...
   ```

3. **상관관계 분석**:
   - Worker-5가 ERR_NETWORK_CHANGED 발생 (20:48:25.123)
   - 거의 동시에 Worker-3이 VPN 연결 (20:48:25.100~105)
   - **결론**: Worker-3의 VPN 연결로 인한 netlink 이벤트가 Worker-5에 영향

### 상관분석 스크립트 (자동화)

```bash
# 상관분석 스크립트 작성 예정 (analyze_correlation.py)
python3 analyze_correlation.py \
    --network-log /tmp/network_events.log \
    --chrome-log /tmp/chrome_network_errors.log \
    --time-window 1.0
```

**출력 예시**:
```
=== ERR_NETWORK_CHANGED 상관분석 ===

발생 시각: 20:48:25.123
영향받은 워커: Worker-5

근접 시스템 이벤트 (±1초):
  [20:48:25.100] Worker-3: wg103 인터페이스 추가
  [20:48:25.102] Worker-3: 라우팅 규칙 추가
  [20:48:25.105] Worker-3: 경로 추가

추정 원인: Worker-3의 VPN 연결로 인한 전역 네트워크 이벤트
```

---

## 로그 파일 위치

| 로그 타입 | 파일 경로 | 설명 |
|-----------|-----------|------|
| 시스템 네트워크 이벤트 | `/tmp/network_events.log` | wg 인터페이스, 라우팅 변경 |
| Chrome 네트워크 에러 | `/tmp/chrome_network_errors.log` | ERR_NETWORK_CHANGED 등 |
| 워커 실행 로그 | `/tmp/worker_test.log` | uc_run_workers.py 출력 |

---

## 모니터링 중지

```bash
# 시스템 네트워크 모니터 중지
pkill -f monitor_network_events.py

# CDP 모니터는 워커 종료 시 자동 중지됨
```

---

## 설정 변경

### CDP 모니터 비활성화

[common/constants.py](../common/constants.py):
```python
class Config:
    # Network Monitoring
    ENABLE_NETWORK_ERROR_MONITOR = False  # True → False로 변경
```

### 시스템 모니터 간격 조정

[monitor_network_events.py](../monitor_network_events.py):
```python
def main():
    monitor = NetworkEventMonitor(log_file="/tmp/network_events.log")
    monitor.monitor_loop(interval=0.5)  # 0.1초 → 0.5초로 변경
```

---

## 예상 결과

### ERR_NETWORK_CHANGED 발생 시

**시스템 네트워크 로그**:
```
[20:48:25.100] [EVENT] 🟢 [#8] 인터페이스 추가: wg103
[20:48:25.102] [EVENT] 📋 [#9] 라우팅 규칙 추가 (Worker-3)
[20:48:25.105] [EVENT] 🛤️  [#10] 경로 추가 (Worker-3, Table 103)
[20:48:25.107] [EVENT] 🟢 [#11] 인터페이스 추가: wg104
[20:48:25.110] [EVENT] 📋 [#12] 라우팅 규칙 추가 (Worker-4)
```

**Chrome 네트워크 로그**:
```
[20:48:25.123] [Worker-5] [CRITICAL] 🚨 ERR_NETWORK_CHANGED 감지!
[20:48:25.129] [Worker-6] [CRITICAL] 🚨 ERR_NETWORK_CHANGED 감지!
```

**분석**:
- 20:48:25.100~110: 여러 워커가 동시에 VPN 연결 (wg103, wg104)
- 20:48:25.123~129: 다른 워커들이 ERR_NETWORK_CHANGED 감지
- **결론**: 다중 VPN 연결로 인한 netlink 이벤트 폭주가 원인

### 정상 동작 시 (DNS 설정 제거 후)

**시스템 네트워크 로그**:
```
[20:48:24.500] [EVENT] 🟢 [#1] 인터페이스 추가: wg101
[20:48:24.850] [EVENT] 🟢 [#2] 인터페이스 추가: wg102  # 0.35초 간격
[20:48:25.200] [EVENT] 🟢 [#3] 인터페이스 추가: wg103  # 0.35초 간격
```

**Chrome 네트워크 로그**:
```
[20:48:30.000] [Worker-1] [INFO] 모니터링 중... (에러: 0회)
[20:48:40.000] [Worker-2] [INFO] 모니터링 중... (에러: 0회)
```

**분석**:
- 워커 시작이 랜덤 지연(0.3~0.7초)로 분산됨
- ERR_NETWORK_CHANGED 발생 0건
- **결론**: DNS 설정 제거 + 워커 시작 지연 효과 확인

---

## 문제 해결

### "Permission denied" 에러
```bash
# monitor_network_events.py 실행 시
sudo python3 monitor_network_events.py

# 또는 일반 사용자로 실행 가능하도록 설정
chmod +x monitor_network_events.py
```

### 로그 파일이 생성되지 않음
```bash
# /tmp 디렉토리 권한 확인
ls -ld /tmp

# 로그 파일 위치 변경 (필요 시)
python3 monitor_network_events.py /home/tech/network_events.log
```

### CDP 모니터가 시작되지 않음
```bash
# Config 확인
grep "ENABLE_NETWORK_ERROR_MONITOR" common/constants.py

# 수동으로 활성화
# Config.ENABLE_NETWORK_ERROR_MONITOR = True
```

---

## 마지막 업데이트
2025-11-07 21:30 KST
