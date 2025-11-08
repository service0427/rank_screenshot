# ERR_NETWORK_CHANGED 상관분석 결과 (2025-11-07)

## 📊 분석 시스템

### 워커별 개별 로그 시스템

각 워커가 자신의 로그 파일에 이벤트를 JSON 형식으로 기록:

```
/tmp/vpn_events_wg101.log  (Worker-1)
/tmp/vpn_events_wg102.log  (Worker-2)
...
/tmp/vpn_events_wg112.log  (Worker-12)
```

**장점:**
- 파일 권한 충돌 없음 (각자 자기 파일만 씀)
- 동기화 불필요
- 마이크로초 정밀도 타임스탬프
- 병합 분석 도구로 전체 타임라인 재구성

### 분석 도구

```bash
# 전체 로그 병합 (시간순 정렬)
python3 analyze_vpn_logs.py

# ERR_NETWORK_CHANGED 전후 ±5초 상관분석
python3 analyze_vpn_logs.py --correlate

# 특정 시간 범위 필터링
python3 analyze_vpn_logs.py --start 22:03:30 --end 22:03:40
```

## 🔍 주요 발견사항

### 1. VPN 연결과 ERR_NETWORK_CHANGED의 시간 상관관계

**타임라인 분석 (2025-11-07 22:03):**

```
22:03:34.332  Worker-1 (wg101)  VPN_CONNECTING
22:03:34.367  Worker-1 (wg101)  VPN_CONNECTED
                                    ↓ +0.207초
22:03:34.574  Worker-4 (wg104)  🔴 ERR_NETWORK_CHANGED (다른 워커!)
                                    ↓ +0.143초
22:03:34.717  Worker-7 (wg107)  🔴 ERR_NETWORK_CHANGED (다른 워커!)
                                    ↓ +0.096초
22:03:34.813  Worker-2 (wg102)  VPN_CONNECTING
22:03:34.846  Worker-2 (wg102)  VPN_CONNECTED
```

**핵심 패턴:**
- Worker-1이 VPN 연결하면 **0.2~0.4초 뒤**에 다른 워커들에서 ERR_NETWORK_CHANGED 발생
- Worker-2가 VPN 연결할 때도 동일한 패턴 반복
- **에러가 발생하는 워커는 VPN을 연결한 워커가 아님!**

### 2. 연쇄 반응 (Cascade Effect)

하나의 VPN 연결이 여러 워커에서 동시에 ERR_NETWORK_CHANGED 유발:

```
Worker-1 VPN 연결 (22:03:34.367)
    ↓
├─ Worker-4: 6개 ERR_NETWORK_CHANGED (22:03:34.574~35.090)
├─ Worker-7: 6개 ERR_NETWORK_CHANGED (22:03:34.717~36.224)
└─ Worker-8: 3개 ERR_NETWORK_CHANGED (22:03:35.068~36.606)
```

### 3. 이전 테스트 잔존 Chrome 세션

**문제:**
- 2개 워커 테스트 실행 (Worker-1, Worker-2)
- 하지만 Worker-4, Worker-7, Worker-8의 로그에도 ERR_NETWORK_CHANGED 기록됨
- 원인: 이전 테스트의 Chrome 프로세스가 완전히 종료되지 않고 백그라운드에서 실행 중

**증거:**
```bash
$ ps aux | grep wg107
wg107     381516  python3 uc_agent.py --vpn-pool-worker 7
wg107     381519  chrome --remote-debugging-port=9229
wg107     383477  chrome --type=renderer (메인 렌더러)
wg107     383536  chrome --type=renderer
wg107     383581  chrome --type=renderer
```

**결론:**
ERR_NETWORK_CHANGED는 VPN을 연결한 워커가 아니라 **이전에 실행 중인 다른 워커의 Chrome 세션**에서 발생합니다.

## 🎯 근본 원인 (Root Cause)

### VPN 연결 시 시스템 네트워크 이벤트

Worker-N이 VPN을 연결하면 다음 시스템 이벤트가 발생:

1. **인터페이스 추가** (`ip link add wgN`)
   - Netlink 이벤트: `RTM_NEWLINK`

2. **IP 주소 할당** (`ip addr add`)
   - Netlink 이벤트: `RTM_NEWADDR`

3. **라우팅 규칙 추가** (`ip rule add uidrange N-N table N`)
   - Netlink 이벤트: `RTM_NEWRULE`

4. **라우팅 테이블 업데이트** (`ip route add default dev wgN table N`)
   - Netlink 이벤트: `RTM_NEWROUTE`

### Chrome의 네트워크 변경 감지

Chrome은 Netlink를 모니터링하여 시스템 네트워크 변경을 감지합니다:

1. **Chrome Network Service**: Netlink 소켓으로 네트워크 이벤트 수신
2. **UID 정책 라우팅 무시**: Chrome은 자신의 UID에 영향받는 규칙만 체크하지 않음
3. **시스템 전역 이벤트 감지**: 다른 UID의 인터페이스 추가/제거도 "네트워크 변경"으로 간주
4. **모든 연결 중단**: `ERR_NETWORK_CHANGED` 발생 → 진행 중인 모든 HTTP 요청 취소

**코드 경로 (Chromium):**
```
services/network/network_service.cc
    ↓
net/base/network_change_notifier_linux.cc
    ↓ Netlink 이벤트 수신
NetworkChangeNotifier::NotifyObserversOfNetworkChange()
    ↓
URLRequest::OnNetworkChanged()
    ↓
ERR_NETWORK_CHANGED
```

## 📈 영향도 분석

### 테스트 데이터 (2025-11-07 22:03)

| 워커 | VPN 연결 | ERR_NETWORK_CHANGED 횟수 | 시간 범위 |
|------|----------|--------------------------|-----------|
| Worker-1 (wg101) | ✅ 22:03:34.367 | 0 | N/A |
| Worker-2 (wg102) | ✅ 22:03:34.846 | 0 | N/A |
| Worker-4 (wg104) | ❌ (이전 테스트 잔존) | 6 | 22:03:34.574~35.090 |
| Worker-7 (wg107) | ❌ (이전 테스트 잔존) | 6 | 22:03:32.429~36.224 |
| Worker-8 (wg108) | ❌ (이전 테스트 잔존) | 3 | 22:03:35.068~36.606 |

**패턴:**
- VPN을 **연결한** 워커: ERR_NETWORK_CHANGED 없음
- 이미 **실행 중인** 다른 워커: ERR_NETWORK_CHANGED 다수 발생

## 🛠️ 해결 방안

### 1. 완전한 프로세스 정리 (단기 해결)

**현재 문제:**
- `uc_run_workers.py` 종료 시 일부 Chrome 프로세스가 살아남음
- `--close` 플래그가 있어도 강제 종료되지 않는 경우 발생

**해결책:**
```bash
# 테스트 전 모든 Chrome 프로세스 강제 종료
./cleanup_all_wg.sh --kill-chrome

# 테스트 실행
python3 uc_run_workers.py -t 2 -i 1

# 테스트 후 다시 정리
./cleanup_all_wg.sh --kill-chrome
```

### 2. VPN 연결 순차화 (중기 해결)

**개념:**
- 모든 워커를 동시 시작하지 않고 순차적으로 시작
- 각 워커의 VPN 연결 후 안정화 시간 확보

**구현:**
```python
# uc_run_workers.py
for worker_id in range(1, num_threads + 1):
    start_worker(worker_id)
    time.sleep(5)  # 5초 지연 (VPN 연결 + 안정화)
```

**효과:**
- 동시 Netlink 이벤트 폭주 방지
- 각 워커가 VPN 안정화 후 Chrome 시작

### 3. Chrome 네트워크 변경 무시 (장기 해결)

**Chrome 플래그:**
```python
--disable-features=NetworkChangeNotifier
```

**위험:**
- 실제 네트워크 변경도 감지 못 함 (WiFi 끊김 등)
- 테스트 환경에서만 사용 권장

### 4. Netlink 이벤트 필터링 (연구 필요)

**개념:**
- Chrome이 자신의 UID와 관련된 라우팅 규칙 변경만 감지하도록 패치
- Chromium 소스 수정 필요 (net/base/network_change_notifier_linux.cc)

**구현 난이도:** 높음

## 📝 권장 사항

### 즉시 적용
1. **테스트 전 완전 정리**: `cleanup_all_wg.sh --kill-chrome`
2. **워커별 로그 분석**: `analyze_vpn_logs.py --correlate`로 상관관계 추적

### 단기 개선
1. **VPN 연결 순차화**: 3~5초 간격으로 워커 시작
2. **프로세스 정리 강화**: `uc_run_workers.py` 종료 시 모든 자식 프로세스 강제 종료

### 장기 연구
1. **Chrome 플래그 테스트**: `--disable-features=NetworkChangeNotifier` 효과 검증
2. **Netlink 이벤트 필터링**: Chromium 패치 가능성 연구

## 🎓 Insight

`★ Insight ─────────────────────────────────────`

**ERR_NETWORK_CHANGED의 역설**

- Chrome은 보안을 위해 네트워크 변경을 감지하고 모든 연결을 중단합니다
- 하지만 UID 정책 라우팅 환경에서는 이것이 오히려 문제가 됩니다
- 다른 UID의 VPN 연결은 현재 UID의 네트워크 경로에 영향을 주지 않지만
- Chrome은 시스템 전역 Netlink 이벤트만 보고 "네트워크가 바뀌었다"고 판단합니다

**교훈:**
- UID 정책 라우팅은 커널 레벨 격리지만
- 애플리케이션 (Chrome)은 이를 인지하지 못합니다
- 멀티 워커 환경에서는 VPN 연결 타이밍이 매우 중요합니다

`─────────────────────────────────────────────────`

## 📚 참고 자료

- [Chromium Network Change Notifier (Linux)](https://source.chromium.org/chromium/chromium/src/+/main:net/base/network_change_notifier_linux.cc)
- [Linux Netlink Protocol](https://man7.org/linux/man-pages/man7/netlink.7.html)
- [ERR_NETWORK_CHANGED_ISSUE.md](ERR_NETWORK_CHANGED_ISSUE.md) - 기존 분석 문서
- [NETWORK_MONITORING_GUIDE.md](NETWORK_MONITORING_GUIDE.md) - 모니터링 설정 가이드
