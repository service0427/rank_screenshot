// Background script - 네트워크 필터 Extension

console.log('🛡️ Coupang Network Filter Extension Loaded');

// Extension 설치/업데이트 시 초기화
chrome.runtime.onInstalled.addListener(() => {
  console.log('🛡️ Extension installed/updated');

  // 현재 적용된 규칙 확인
  chrome.declarativeNetRequest.getDynamicRules((rules) => {
    console.log(`🛡️ Dynamic rules count: ${rules.length}`);
  });
});

// 네트워크 요청 차단 로깅
chrome.declarativeNetRequest.onRuleMatchedDebug.addListener((details) => {
  console.log('🚫 Blocked request:', details.request.url);
});

console.log('🛡️ Background script initialized');
