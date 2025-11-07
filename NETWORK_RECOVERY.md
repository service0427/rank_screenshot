# 네트워크 자동 복구 시스템

## 개요

VPN 키 풀 테스트 중 메인 라우팅이 손상되어 전체 인터넷이 마비되는 상황을 방지하기 위한 자동 복구 시스템입니다.

## 구성 요소

### 1. 네트워크 와치독 (`network_watchdog.sh`)

**기능**:
- 1분마다 네트워크 연결 상태 체크 (ping 8.8.8.8)
- 연속 3회 실패 시 자동 복구 시작
- 연속 5회 실패 시 긴급 복구 모드 (모든 VPN 강제 종료)
- 메인 라우팅 테이블 자동 복구
- DNS 설정 자동 복구

**실행 방법**:
```bash
# 포그라운드 실행 (테스트용)
./network_watchdog.sh

# 백그라운드 실행 (운영용)
nohup ./network_watchdog.sh > /tmp/network_watchdog.log 2>&1 &

# 로그 확인
tail -f /tmp/network_watchdog.log
```

**중지 방법**:
```bash
# 프로세스 찾기
ps aux | grep network_watchdog.sh | grep -v grep

# PID로 종료
kill <PID>
```

### 2. VPN 연결 해제 시 메인 라우팅 보호

**위치**: `lib/modules/vpn_api_client.py`의 `VPNConnection.disconnect()`

**기능**:
- VPN 연결 해제 시 메인 라우팅 자동 확인
- 메인 라우팅이 없으면 자동 복구
- `default via 121.172.70.254 dev enp4s0` 자동 추가

## 사용 시나리오

### 시나리오 1: 정상 운영

```bash
# 1. 네트워크 와치독 시작
nohup ./network_watchdog.sh > /tmp/network_watchdog.log 2>&1 &

# 2. VPN 키 풀 워커 실행
python3 run_workers.py -t 12 -i 100

# 3. 로그 모니터링 (다른 터미널)
tail -f /tmp/network_watchdog.log
```

### 시나리오 2: 네트워크 장애 발생

**증상**: 인터넷 연결이 끊김

**자동 복구**:
1. 와치독이 3회 연속 실패 감지 (약 3분)
2. 자동으로 VPN 워커 인터페이스 종료
3. 메인 라우팅 복구
4. DNS 설정 복구
5. DHCP 갱신

**수동 복구** (와치독이 없을 경우):
```bash
# 모든 VPN 워커 인터페이스 강제 종료
for iface in $(ip link show | grep -o 'wg-worker-[0-9]*'); do
    sudo ip link set "$iface" down
    sudo ip link delete "$iface"
done

# 메인 라우팅 복구
sudo ip route add default via 121.172.70.254 dev enp4s0

# DHCP 갱신
sudo dhclient -r enp4s0
sudo dhclient enp4s0
```

### 시나리오 3: 긴급 복구 모드

**발동 조건**: 연속 5회 이상 네트워크 실패 (약 5분)

**동작**:
1. 모든 WireGuard 인터페이스 강제 종료 (wg*, wg-*)
2. 메인 라우팅 복구
3. 메인 인터페이스 재시작
4. DHCP 재할당

## 설정

### `network_watchdog.sh` 설정 변경

```bash
# 체크 주기 (기본: 60초)
CHECK_INTERVAL=60

# Ping 대상 (기본: 8.8.8.8)
PING_TARGET="8.8.8.8"

# 연속 실패 임계값 (기본: 3회)
FAIL_THRESHOLD=3

# 메인 게이트웨이 (기본: 121.172.70.254)
MAIN_GATEWAY="121.172.70.254"

# 메인 인터페이스 (기본: enp4s0)
MAIN_INTERFACE="enp4s0"
```

### 메인 라우팅 보호 설정 변경

`lib/modules/vpn_api_client.py:365`:
```python
main_gateway = "121.172.70.254"  # 환경에 맞게 변경
```

## 로그 확인

### 와치독 로그

```bash
# 전체 로그
cat /tmp/network_watchdog.log

# 실시간 모니터링
tail -f /tmp/network_watchdog.log

# 복구 이벤트만 확인
grep "복구" /tmp/network_watchdog.log

# 실패 이벤트만 확인
grep "실패" /tmp/network_watchdog.log
```

### VPN 키 풀 로그

```bash
# 오늘 날짜 로그
cat logs/$(date +%Y-%m-%d).txt

# 메인 라우팅 복구 이벤트
cat logs/*.txt | grep "메인 라우팅"
```

## 모니터링

### 실시간 라우팅 테이블 확인

```bash
# 1초마다 라우팅 테이블 출력
watch -n 1 'ip route show | head -20'
```

### VPN 인터페이스 모니터링

```bash
# 1초마다 WireGuard 인터페이스 확인
watch -n 1 'ip link show | grep wg'
```

### 네트워크 연결 테스트

```bash
# 메인 게이트웨이 ping
ping -c 3 121.172.70.254

# 외부 ping
ping -c 3 8.8.8.8

# DNS 테스트
nslookup google.com
```

## 문제 해결

### Q1. 와치독이 실행되지 않음

```bash
# 실행 권한 확인
ls -la network_watchdog.sh

# 권한 부여
chmod +x network_watchdog.sh
```

### Q2. 자동 복구가 작동하지 않음

```bash
# 와치독 실행 확인
ps aux | grep network_watchdog.sh

# 로그 확인
tail -100 /tmp/network_watchdog.log

# 수동으로 복구 테스트
./network_watchdog.sh
```

### Q3. VPN 종료 후에도 라우팅이 복구되지 않음

```bash
# 메인 라우팅 직접 확인
ip route show | grep default

# 없으면 수동 추가
sudo ip route add default via 121.172.70.254 dev enp4s0
```

## 주의사항

1. **와치독 필수**: VPN 키 풀 사용 시 반드시 와치독을 실행하세요
2. **게이트웨이 확인**: 환경에 맞는 게이트웨이 IP를 설정하세요
3. **로그 모니터링**: 와치독 로그를 주기적으로 확인하세요
4. **테스트**: 운영 전에 소규모 워커로 테스트하세요

## 복구 시나리오별 대응

| 상황 | 자동 복구 | 수동 복구 | 예상 시간 |
|------|----------|----------|----------|
| VPN 워커 1개 실패 | ✅ (즉시) | - | 즉시 |
| 네트워크 3회 실패 | ✅ (자동) | - | 3분 |
| 네트워크 5회 실패 | ✅ (긴급) | - | 5분 |
| 와치독 없음 | ❌ | ✅ (필수) | 수동 |
| 메인 라우팅 손상 | ✅ (즉시) | ✅ (백업) | 1분 |

---

**2025-11-07 작성**
