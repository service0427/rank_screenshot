# VPN 키 풀 API - Gateway 필드 추가 가이드

## 개요

~~VPN 키 풀 클라이언트가 정책 라우팅을 올바르게 설정하려면, 각 VPN 서버의 **Gateway 정보**가 필요합니다.~~

**2025-11-07 해결**: Gateway 정보는 **필요하지 않음**. WireGuard는 Point-to-Point 인터페이스이므로 "via gateway" 없이 인터페이스로 직접 라우팅합니다.

이 문서는 참고용으로 유지되며, Gateway 기반 라우팅 방식의 문제점과 해결 과정을 기록합니다.

## 현재 상황 (2025-11-07)

### VPN 서버 네트워크 구조
```
서버 IP (Gateway): 10.8.0.1/24
클라이언트 IP 범위: 10.8.0.10 ~ 10.8.0.19 (10개 동시 접속)
서브넷: 10.8.0.0/24
```

### 현재 동작 (Fallback)
```python
# 클라이언트 코드 (common/vpn_api_client.py:261-262)
gateway = '.'.join(internal_ip.split('.')[:3]) + '.1'
# 예: 10.8.0.10 → 10.8.0.1 ✅ 정확!
```

**현재 상태**:
- ✅ 모든 VPN 서버가 `.1`을 Gateway로 사용 (확인됨)
- ✅ Fallback 로직이 정확하게 동작 중
- ✅ 2개 워커 테스트 성공 (100%)

**실제 문제 원인** (2025-11-07 발견):
- ❌ Gateway 정보 부족 (X)
- ✅ **WireGuard P2P 특성 무시** (O)

**해결책**:
```bash
# 잘못됨:
PostUp = ip route add default via 10.8.0.1 dev %i table 101
# Error: Nexthop has invalid gateway

# 올바름 (WireGuard는 Point-to-Point):
PostUp = ip route add default dev %i table 101
# ✅ 성공!
```

**기술적 배경**:
- WireGuard는 **Point-to-Point (P2P)** 인터페이스
- P2P에서는 "via gateway" 없이 인터페이스로 직접 라우팅
- Gateway는 동일 서브넷에 있어도 "onlink" 없이는 접근 불가

---

## ⚠️  아래 내용은 참고용 (실제로는 Gateway 필요 없음)

### 이상적인 동작 (API 제공) - 불필요함!
```json
{
  "success": true,
  "internal_ip": "10.8.0.12",
  "gateway": "10.8.0.1",  // ← API에서 정확한 값 제공
  ...
}
```

## API 서버 수정 방법

### 1. 응답 구조 업데이트

#### 변경 전 (`/api/vpn/allocate-key` 응답):
```json
{
  "success": true,
  "server_ip": "222.100.114.73",
  "server_port": 51820,
  "server_pubkey": "BHhF...",
  "private_key": "aEGr...",
  "public_key": "BMbX...",
  "internal_ip": "10.8.0.16",
  "config": "[Interface]\nPrivateKey = ...\n[Peer]\n..."
}
```

#### 변경 후 (권장):
```json
{
  "success": true,
  "server_ip": "222.100.114.73",
  "server_port": 51820,
  "server_pubkey": "BHhF...",
  "private_key": "aEGr...",
  "public_key": "BMbX...",
  "internal_ip": "10.8.0.16",
  "gateway": "10.8.0.1",           // ← 이 필드 추가!
  "config": "[Interface]\nPrivateKey = ...\n[Peer]\n..."
}
```

### 2. Gateway 값 결정 로직

#### Option A: 서버 설정에서 읽기 (권장)
```python
# VPN 서버 설정 파일에서 Gateway 정보 읽기
def get_gateway_for_server(server_config):
    """
    각 VPN 서버의 Gateway 정보를 서버 설정에서 읽어옴

    Args:
        server_config: 서버 설정 객체 (예: WireGuard 서버 설정)

    Returns:
        Gateway IP 주소 (예: "10.8.0.1")
    """
    # 서버 설정에서 Gateway 읽기
    # 예: wg0.conf에서 [Interface] 섹션의 Address 첫 번째 IP
    return server_config.get('gateway', '10.8.0.1')  # fallback: .1
```

#### Option B: 네트워크 CIDR에서 자동 계산
```python
import ipaddress

def calculate_gateway(network_cidr):
    """
    네트워크 CIDR에서 Gateway를 계산

    Args:
        network_cidr: "10.8.0.0/24" 형식의 네트워크 주소

    Returns:
        Gateway IP 주소 (일반적으로 네트워크 첫 번째 주소 + 1)

    Examples:
        >>> calculate_gateway("10.8.0.0/24")
        "10.8.0.1"
    """
    network = ipaddress.ip_network(network_cidr, strict=False)
    gateway = str(network.network_address + 1)  # 첫 번째 주소 + 1
    return gateway
```

### 3. API 엔드포인트 수정 예시

#### Python (Flask/FastAPI):
```python
from flask import Flask, jsonify

@app.route('/api/vpn/allocate-key', methods=['GET'])
def allocate_key():
    # ... 기존 키 할당 로직 ...

    # Gateway 정보 추가
    server_config = get_server_config(allocated_server_ip)
    gateway = server_config.get('gateway', calculate_gateway(server_config['network']))

    response = {
        "success": True,
        "server_ip": allocated_server_ip,
        "server_port": 51820,
        "server_pubkey": server_pubkey,
        "private_key": private_key,
        "public_key": public_key,
        "internal_ip": internal_ip,
        "gateway": gateway,  # ← 추가!
        "config": wireguard_config
    }

    return jsonify(response)
```

#### Node.js (Express):
```javascript
app.get('/api/vpn/allocate-key', async (req, res) => {
  // ... 기존 키 할당 로직 ...

  // Gateway 정보 추가
  const serverConfig = getServerConfig(allocatedServerIp);
  const gateway = serverConfig.gateway || calculateGateway(serverConfig.network);

  res.json({
    success: true,
    server_ip: allocatedServerIp,
    server_port: 51820,
    server_pubkey: serverPubkey,
    private_key: privateKey,
    public_key: publicKey,
    internal_ip: internalIp,
    gateway: gateway,  // ← 추가!
    config: wireguardConfig
  });
});
```

## Gateway 결정 규칙

### 일반적인 VPN 네트워크 구조:
```
10.8.0.0/24 네트워크:
  - 10.8.0.0      : 네트워크 주소 (사용 불가)
  - 10.8.0.1      : Gateway (VPN 서버)  ← 일반적으로 여기
  - 10.8.0.2~254  : 클라이언트 할당 가능 범위
  - 10.8.0.255    : 브로드캐스트 주소 (사용 불가)
```

### 예외 케이스:
일부 VPN 서버는 다른 규칙을 사용할 수 있습니다:
- Gateway가 `.254` (예: 10.8.0.254)
- Gateway가 서버의 내부 IP와 동일
- 여러 서브넷 사용 (10.8.0.0/24, 10.8.1.0/24, ...)

**중요**: 각 VPN 서버의 실제 설정에 맞는 Gateway를 반환해야 합니다.

## 클라이언트 동작 (Fallback 포함)

### 클라이언트 코드 (`common/vpn_api_client.py`):
```python
# Line 254-262
# Gateway 정보 가져오기
# Option 1: API 응답에서 직접 가져오기 (권장)
# Option 2: 없으면 internal_ip 대역의 .1로 fallback
internal_ip = self.vpn_key_data['internal_ip']
gateway = self.vpn_key_data.get('gateway')
if not gateway:
    # Fallback: 내부 IP 대역의 .1 (예: 10.8.0.14 → 10.8.0.1)
    gateway = '.'.join(internal_ip.split('.')[:3]) + '.1'
    print(f"   ⚠️  API에 gateway 정보 없음, fallback 사용: {gateway}")
```

### 동작 시나리오:

**시나리오 A**: API에서 `gateway` 제공 (권장)
```
1. API 응답: {"gateway": "10.8.0.1", ...}
2. 클라이언트: gateway = "10.8.0.1" (API 응답 사용)
3. WireGuard 설정: PostUp = ip route add default via 10.8.0.1 dev wg101 table 101
4. 결과: ✅ 정상 연결
```

**시나리오 B**: API에서 `gateway` 미제공 (Fallback)
```
1. API 응답: {"internal_ip": "10.8.0.16", ...} (gateway 없음)
2. 클라이언트: gateway = "10.8.0.1" (internal_ip 기반 계산)
3. 경고 메시지: "⚠️  API에 gateway 정보 없음, fallback 사용: 10.8.0.1"
4. WireGuard 설정: PostUp = ip route add default via 10.8.0.1 dev wg101 table 101
5. 결과: ✅ 또는 ❌ (서버 설정에 따라 다름)
```

## 테스트 방법

### 1. API 응답 확인:
```bash
curl -X GET "http://220.121.120.83:55558/api/vpn/allocate-key" | jq '.'
```

**기대 출력**:
```json
{
  "success": true,
  "server_ip": "222.100.114.73",
  "internal_ip": "10.8.0.16",
  "gateway": "10.8.0.1",  // ← 이 필드 확인!
  ...
}
```

### 2. 클라이언트 연결 테스트:
```bash
cd /home/tech/rank_screenshot
python3 uc_run_workers.py -t 1 -i 1
```

**기대 출력** (gateway 제공 시):
```
   ✅ VPN 키 할당 완료
      서버: 222.100.114.73
      내부 IP: 10.8.0.16
   📝 WireGuard 설정 파일 생성: /tmp/vpn_configs/wg101.conf
      ✓ Table = off (메인 라우팅 테이블 보존)
      ✓ 정책 라우팅: wg101 (UID 1101) → 테이블 101
   🔌 WireGuard 연결 중 (wg101)...
   ✅ VPN 연결 완료 (10.8.0.16)
```

**기대 출력** (gateway 미제공 시):
```
   ✅ VPN 키 할당 완료
      서버: 222.100.114.73
      내부 IP: 10.8.0.16
   ⚠️  API에 gateway 정보 없음, fallback 사용: 10.8.0.1  // ← 경고 출력
   📝 WireGuard 설정 파일 생성: /tmp/vpn_configs/wg101.conf
   ...
```

### 3. 라우팅 테이블 확인:
```bash
# 메인 라우팅 테이블 확인 (10.8.0.X 경로가 없어야 함)
ip route show table main

# 정책 라우팅 테이블 확인 (default 경로가 있어야 함)
ip route show table 101
# 기대 출력: default via 10.8.0.1 dev wg101

# 라우팅 규칙 확인
ip rule list
# 기대 출력: 10101:  from all uidrange 1101-1101 lookup 101
```

## 문제 해결

### "Nexthop has invalid gateway" 오류
**원인**: Gateway IP가 잘못됨 (서버가 `.1`이 아닌 다른 Gateway 사용)
**해결**: API에서 정확한 `gateway` 값 제공

### "RTNETLINK answers: File exists" 오류
**원인**: 이전 VPN 연결의 라우팅 규칙이 남아있음
**해결**: 이미 처리됨 (PostUp에서 기존 규칙 삭제)

### Gateway fallback 경고 메시지
**원인**: API 응답에 `gateway` 필드 없음
**해결**: API 서버에 `gateway` 필드 추가 (이 문서 참고)

## 요약

1. **API 서버 수정 필요**:
   - `/api/vpn/allocate-key` 응답에 `"gateway": "10.8.0.1"` 필드 추가

2. **Gateway 값 결정**:
   - 각 VPN 서버의 실제 설정에서 읽거나
   - 네트워크 CIDR에서 자동 계산 (첫 번째 주소 + 1)

3. **클라이언트 동작**:
   - API에서 `gateway` 제공 시: 해당 값 사용 (권장)
   - API에서 `gateway` 미제공 시: Fallback 사용 + 경고 메시지

4. **기대 효과**:
   - 모든 VPN 서버에서 안정적인 연결
   - "Nexthop has invalid gateway" 오류 제거
   - 명확한 Gateway 정보로 디버깅 용이

## 참고 문서

- [VPN 키 풀 API 문서](VPN_KEY_POOL_API.md)
- [wg101-112 통합 시스템](../CLAUDE.md#vpn-키-풀-시스템)
- [정책 라우팅 가이드](../CLAUDE.md#정책-라우팅-policy-routing)
