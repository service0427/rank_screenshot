#!/usr/bin/env python3
"""
브라우저 핑거프린트 랜덤화 모듈
IP 1개로 무한 우회를 위한 다층 핑거프린트 변조
"""

import random


class FingerprintRandomizer:
    """브라우저 핑거프린트를 랜덤하게 변조"""

    @staticmethod
    def apply_all(driver):
        """
        모든 핑거프린트 랜덤화 적용 (극한 모드)

        Args:
            driver: Selenium WebDriver 인스턴스
        """
        print("🎭 핑거프린트 랜덤화 적용 중 (극한 모드)...")

        FingerprintRandomizer.randomize_user_agent(driver)
        FingerprintRandomizer.randomize_http_headers(driver)
        FingerprintRandomizer.randomize_screen(driver)
        FingerprintRandomizer.randomize_canvas(driver)
        FingerprintRandomizer.randomize_webgl(driver)
        FingerprintRandomizer.randomize_navigator(driver)
        FingerprintRandomizer.randomize_plugins(driver)
        FingerprintRandomizer.block_webrtc(driver)
        FingerprintRandomizer.randomize_fonts(driver)
        FingerprintRandomizer.randomize_audio(driver)

        print("   ✓ 핑거프린트 랜덤화 완료 (극한 모드)\n")

    @staticmethod
    def randomize_user_agent(driver):
        """User-Agent 완전 변조 (다른 OS/브라우저로 위장)"""
        user_agents = [
            # Windows Chrome
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            # macOS Chrome
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            # Linux Chrome (기본)
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            # Windows Firefox 위장
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            # macOS Safari 위장
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        ]

        ua = random.choice(user_agents)

        try:
            # CDP로 User-Agent 설정
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                'userAgent': ua
            })
            print(f"   ✓ User-Agent: {ua[:60]}...")
        except Exception as e:
            print(f"   ⚠ User-Agent 설정 실패: {e}")

    @staticmethod
    def randomize_http_headers(driver):
        """HTTP 헤더 랜덤화 (극한 모드)"""
        # Accept-Encoding 순서 변경
        accept_encodings = [
            'gzip, deflate, br',
            'br, gzip, deflate',
            'gzip, deflate',
            'deflate, gzip, br',
        ]

        # Accept 헤더 변경
        accept_headers = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        ]

        # Accept-Language 변형
        accept_languages = [
            'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'ko-KR,ko;q=0.9',
            'ko;q=0.9,en;q=0.8',
        ]

        # sec-ch-ua 변형
        sec_ch_ua_variants = [
            '"Chromium";v="130", "Not(A:Brand";v="24"',
            '"Google Chrome";v="130", "Chromium";v="130", "Not=A?Brand";v="24"',
            '"Chromium";v="130", "Google Chrome";v="130"',
        ]

        # Referer 추가 (구글에서 유입된 것처럼)
        referers = [
            'https://www.google.com/',
            'https://www.naver.com/',
            '',  # Referer 없음
        ]

        headers = {
            'Accept': random.choice(accept_headers),
            'Accept-Encoding': random.choice(accept_encodings),
            'Accept-Language': random.choice(accept_languages),
            'sec-ch-ua': random.choice(sec_ch_ua_variants),
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': random.choice(['"Linux"', '"Windows"', '"macOS"']),
            'DNT': random.choice(['1', '']),  # Do Not Track
            'Upgrade-Insecure-Requests': '1',
        }

        # Referer는 빈 문자열이 아닐 때만 추가
        referer = random.choice(referers)
        if referer:
            headers['Referer'] = referer

        try:
            driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': headers})
            print(f"   ✓ HTTP 헤더: Accept-Encoding={headers['Accept-Encoding']}, Referer={referer or 'None'}")
        except Exception as e:
            print(f"   ⚠ HTTP 헤더 설정 실패: {e}")

    @staticmethod
    def randomize_screen(driver):
        """화면 해상도 및 DPI 랜덤화"""
        resolutions = [
            {'width': 1920, 'height': 1080, 'scale': 1.0},
            {'width': 2560, 'height': 1440, 'scale': 1.0},
            {'width': 1366, 'height': 768, 'scale': 1.0},
            {'width': 1536, 'height': 864, 'scale': 1.25},
            {'width': 1920, 'height': 1080, 'scale': 1.5},
        ]

        res = random.choice(resolutions)

        try:
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width': res['width'],
                'height': res['height'],
                'deviceScaleFactor': res['scale'],
                'mobile': False
            })
            print(f"   ✓ Screen: {res['width']}x{res['height']} @ {res['scale']}x")
        except Exception as e:
            print(f"   ⚠ Screen 설정 실패: {e}")

    @staticmethod
    def randomize_canvas(driver):
        """Canvas 핑거프린트 랜덤화"""
        script = """
        // Canvas toDataURL 변조
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            const context = this.getContext('2d');
            if (context) {
                const imageData = context.getImageData(0, 0, this.width, this.height);

                // 픽셀에 미세한 랜덤 노이즈 추가 (육안 구분 불가)
                for (let i = 0; i < imageData.data.length; i += 4) {
                    const noise = Math.floor(Math.random() * 3) - 1;
                    imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
                }

                context.putImageData(imageData, 0, 0);
            }
            return originalToDataURL.call(this, type);
        };
        """

        try:
            driver.execute_script(script)
            print(f"   ✓ Canvas: 노이즈 추가")
        except Exception as e:
            print(f"   ⚠ Canvas 변조 실패: {e}")

    @staticmethod
    def randomize_webgl(driver):
        """WebGL 핑거프린트 랜덤화"""
        vendors = [
            'Intel Inc.',
            'Google Inc.',
            'NVIDIA Corporation',
        ]

        renderers = [
            'Intel Iris OpenGL Engine',
            'ANGLE (Intel, Intel(R) UHD Graphics 620, OpenGL 4.1)',
            'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0)',
            'ANGLE (Intel(R) HD Graphics 630 Direct3D11 vs_5_0 ps_5_0)',
        ]

        vendor = random.choice(vendors)
        renderer = random.choice(renderers)

        script = f"""
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {{
                return '{vendor}';
            }}
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {{
                return '{renderer}';
            }}
            return getParameter.call(this, parameter);
        }};

        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{vendor}';
            if (parameter === 37446) return '{renderer}';
            return getParameter2.call(this, parameter);
        }};
        """

        try:
            driver.execute_script(script)
            print(f"   ✓ WebGL: {vendor[:20]}...")
        except Exception as e:
            print(f"   ⚠ WebGL 변조 실패: {e}")

    @staticmethod
    def randomize_navigator(driver):
        """Navigator 속성 랜덤화"""
        hardware_concurrency = random.choice([2, 4, 6, 8, 12, 16])
        device_memory = random.choice([2, 4, 8, 16])

        script = f"""
        // CPU 코어 수
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {hardware_concurrency}
        }});

        // 메모리
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {device_memory}
        }});

        // 배터리 API 차단 (핑거프린팅 방지)
        Object.defineProperty(navigator, 'getBattery', {{
            get: () => undefined
        }});
        """

        try:
            driver.execute_script(script)
            print(f"   ✓ Navigator: {hardware_concurrency} cores, {device_memory}GB RAM")
        except Exception as e:
            print(f"   ⚠ Navigator 변조 실패: {e}")

    @staticmethod
    def randomize_plugins(driver):
        """Plugin 및 MIME Type 랜덤화"""
        script = """
        // Plugin 목록 변조
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
                    {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}
                ];
                return plugins;
            }
        });

        // MimeTypes 변조
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => {
                return [
                    {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'},
                    {type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format'}
                ];
            }
        });
        """

        try:
            driver.execute_script(script)
            print(f"   ✓ Plugins: 변조됨")
        except Exception as e:
            print(f"   ⚠ Plugin 변조 실패: {e}")

    @staticmethod
    def block_webrtc(driver):
        """WebRTC IP 유출 차단"""
        script = """
        // WebRTC IP 유출 방지
        const originalRTCPeerConnection = window.RTCPeerConnection;
        window.RTCPeerConnection = function(...args) {
            throw new Error('WebRTC is disabled');
        };

        // getUserMedia 차단
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia = function() {
                return Promise.reject(new Error('getUserMedia is disabled'));
            };
        }
        """

        try:
            driver.execute_script(script)
            print(f"   ✓ WebRTC: 차단됨")
        except Exception as e:
            print(f"   ⚠ WebRTC 차단 실패: {e}")

    @staticmethod
    def randomize_fonts(driver):
        """Font 핑거프린트 랜덤화"""
        script = """
        // Font measurement 변조
        const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
        const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');

        Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
            get: function() {
                const width = originalOffsetWidth.get.call(this);
                return width + (Math.random() * 0.0001 - 0.00005);
            }
        });

        Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
            get: function() {
                const height = originalOffsetHeight.get.call(this);
                return height + (Math.random() * 0.0001 - 0.00005);
            }
        });
        """

        try:
            driver.execute_script(script)
            print(f"   ✓ Fonts: 측정값 변조")
        except Exception as e:
            print(f"   ⚠ Font 변조 실패: {e}")

    @staticmethod
    def randomize_audio(driver):
        """Audio 핑거프린트 랜덤화"""
        script = """
        // AudioContext 변조
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
            AudioContext.prototype.createAnalyser = function() {
                const analyser = originalCreateAnalyser.call(this);
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
                analyser.getFloatFrequencyData = function(array) {
                    originalGetFloatFrequencyData.call(this, array);
                    // 미세한 노이즈 추가
                    for (let i = 0; i < array.length; i++) {
                        array[i] += Math.random() * 0.0001 - 0.00005;
                    }
                };
                return analyser;
            };
        }
        """

        try:
            driver.execute_script(script)
            print(f"   ✓ Audio: 노이즈 추가")
        except Exception as e:
            print(f"   ⚠ Audio 변조 실패: {e}")

    @staticmethod
    def get_fingerprint_info(driver):
        """
        현재 브라우저의 핑거프린트 정보 추출

        Returns:
            dict: 핑거프린트 정보
        """
        script = """
        return {
            userAgent: navigator.userAgent,
            language: navigator.language,
            languages: navigator.languages,
            platform: navigator.platform,
            hardwareConcurrency: navigator.hardwareConcurrency,
            deviceMemory: navigator.deviceMemory,
            screen: {
                width: screen.width,
                height: screen.height,
                availWidth: screen.availWidth,
                availHeight: screen.availHeight,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth
            },
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            }
        };
        """

        try:
            return driver.execute_script(script)
        except Exception as e:
            print(f"⚠ 핑거프린트 정보 추출 실패: {e}")
            return {}
