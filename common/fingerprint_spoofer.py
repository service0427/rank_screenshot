#!/usr/bin/env python3
"""
브라우저 핑거프린트 스푸핑 모듈

Canvas, WebGL, Hardware 등 다양한 핑거프린트 속성을 랜덤하게 변조하여
무제한 고유 핑거프린트 생성

사용법:
    from common.fingerprint_spoofer import FingerprintSpoofer

    spoofer = FingerprintSpoofer()
    script = spoofer.generate_spoof_script()

    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': script
    })
"""

import random
from typing import Dict, Tuple


class FingerprintSpoofer:
    """브라우저 핑거프린트 스푸핑"""

    # 가능한 CPU 코어 수 (실제 존재하는 값들)
    CPU_CORES = [2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 32]

    # 가능한 메모리 크기 (GB)
    MEMORY_SIZES = [4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128]

    # 일반적인 화면 해상도
    SCREEN_RESOLUTIONS = [
        (1366, 768),   # HD+
        (1440, 900),   # WXGA+
        (1536, 864),   # HD+
        (1600, 900),   # HD+
        (1920, 1080),  # FHD
        (1920, 1200),  # WUXGA
        (2560, 1440),  # 2K
        (2560, 1600),  # WQXGA
        (3440, 1440),  # UWQHD
        (3840, 2160),  # 4K
        (5120, 2880),  # 5K
    ]

    # GPU 벤더/렌더러 조합
    GPU_CONFIGS = [
        ('NVIDIA Corporation', 'NVIDIA GeForce GTX 1060/PCIe/SSE2'),
        ('NVIDIA Corporation', 'NVIDIA GeForce RTX 3060/PCIe/SSE2'),
        ('NVIDIA Corporation', 'NVIDIA GeForce RTX 3070/PCIe/SSE2'),
        ('NVIDIA Corporation', 'NVIDIA GeForce RTX 4060/PCIe/SSE2'),
        ('AMD', 'AMD Radeon RX 580 Series'),
        ('AMD', 'AMD Radeon RX 6700 XT'),
        ('AMD', 'AMD Radeon RX 7900 XT'),
        ('Intel', 'Intel(R) UHD Graphics 630'),
        ('Intel', 'Intel(R) Iris(R) Xe Graphics'),
    ]

    # 언어 설정
    LANGUAGES = [
        'ko-KR',  # 한국어
        'en-US',  # 미국 영어
        'en-GB',  # 영국 영어
        'ja-JP',  # 일본어
        'zh-CN',  # 중국어 간체
        'de-DE',  # 독일어
        'fr-FR',  # 프랑스어
    ]

    # 터치 포인트
    TOUCH_POINTS = [0, 1, 5]

    # 스푸핑 프리셋 (단계적 테스트용)
    PRESETS = {
        'minimal': {
            # GPU + Audio + Canvas 노이즈 (가장 효과적인 조합)
            'hardware': False,
            'screen': False,
            'webgl': True,     # GPU 변경
            'canvas': True,    # Canvas 노이즈 추가
            'audio': True,     # Audio Context 변경
            'language': False,
            'touch': False,
        },
        'light': {
            # minimal + Hardware
            'hardware': True,
            'screen': False,
            'webgl': True,
            'canvas': True,
            'audio': True,
            'language': False,
            'touch': False,
        },
        'medium': {
            # light + Screen
            'hardware': True,
            'screen': True,
            'webgl': True,
            'canvas': True,
            'audio': True,
            'language': False,
            'touch': False,
        },
        'medium1': {
            # medium + Language (Language 단독 테스트)
            'hardware': True,
            'screen': True,
            'webgl': True,
            'canvas': True,
            'audio': True,
            'language': True,   # Language만 추가
            'touch': False,
        },
        'full': {
            # medium + Touch (안전한 최대 조합)
            'hardware': True,
            'screen': True,
            'webgl': True,
            'canvas': True,
            'audio': True,
            'language': False,  # Language는 제외 (TLS 차단 원인)
            'touch': True,
        },
    }

    def __init__(self, seed: int = None, preset: str = 'full'):
        """
        Args:
            seed: 랜덤 시드 (None이면 완전 랜덤)
            preset: 프리셋 모드 ('minimal', 'light', 'medium', 'full' 권장)
        """
        if seed is not None:
            random.seed(seed)

        self.preset = preset
        self.config = self.PRESETS.get(preset, self.PRESETS['full'])

    def generate_random_config(self) -> Dict:
        """랜덤 스푸핑 설정 생성"""
        # 1. CPU & Memory
        cores = random.choice(self.CPU_CORES)
        memory = random.choice(self.MEMORY_SIZES)

        # 2. Screen
        width, height = random.choice(self.SCREEN_RESOLUTIONS)
        color_depth = random.choice([24, 30, 32])

        # 3. WebGL GPU
        gpu_vendor, gpu_renderer = random.choice(self.GPU_CONFIGS)

        # 4. Canvas 노이즈 강도
        canvas_noise_rate = random.uniform(0.05, 0.25)
        canvas_noise_amount = random.randint(3, 10)

        # 5. Audio Context 노이즈
        audio_noise = random.uniform(0.0001, 0.001)

        # 6. Language
        language = random.choice(self.LANGUAGES)

        # 7. Touch
        touch_points = random.choice(self.TOUCH_POINTS)

        return {
            'cores': cores,
            'memory': memory,
            'screen': {
                'width': width,
                'height': height,
                'color_depth': color_depth,
            },
            'gpu': {
                'vendor': gpu_vendor,
                'renderer': gpu_renderer,
            },
            'canvas': {
                'noise_rate': canvas_noise_rate,
                'noise_amount': canvas_noise_amount,
            },
            'audio_noise': audio_noise,
            'language': language,
            'touch_points': touch_points,
        }

    def generate_spoof_script(self, config: Dict = None) -> Tuple[str, Dict]:
        """
        스푸핑 JavaScript 스크립트 생성 (프리셋 기반 조건부 생성)

        Args:
            config: 스푸핑 설정 (None이면 자동 생성)

        Returns:
            (script, config) 튜플
        """
        if config is None:
            config = self.generate_random_config()

        # JavaScript 섹션 리스트 (조건부로 추가)
        script_parts = []

        # 헤더
        active_features = [k for k, v in self.config.items() if v]
        script_parts.append(f"""(function() {{
    'use strict';

    // Preset: {self.preset}
    // Active features: {', '.join(active_features)}
""")

        # === 1. Hardware Spoofing ===
        if self.config.get('hardware', True):
            script_parts.append(f"""
    // === 1. Hardware Spoofing ===
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: function() {{ return {config['cores']}; }}
    }});

    Object.defineProperty(navigator, 'deviceMemory', {{
        get: function() {{ return {config['memory']}; }}
    }});
""")
        else:
            script_parts.append("\n    // === 1. Hardware Spoofing === DISABLED\n")

        # === 2. Screen Spoofing ===
        if self.config.get('screen', True):
            script_parts.append(f"""
    // === 2. Screen Spoofing ===
    Object.defineProperty(screen, 'width', {{
        get: function() {{ return {config['screen']['width']}; }}
    }});

    Object.defineProperty(screen, 'height', {{
        get: function() {{ return {config['screen']['height']}; }}
    }});

    Object.defineProperty(screen, 'availWidth', {{
        get: function() {{ return {config['screen']['width']}; }}
    }});

    Object.defineProperty(screen, 'availHeight', {{
        get: function() {{ return {config['screen']['height'] - 40}; }}
    }});

    Object.defineProperty(screen, 'colorDepth', {{
        get: function() {{ return {config['screen']['color_depth']}; }}
    }});

    Object.defineProperty(screen, 'pixelDepth', {{
        get: function() {{ return {config['screen']['color_depth']}; }}
    }});
""")
        else:
            script_parts.append("\n    // === 2. Screen Spoofing === DISABLED\n")

        # === 3. WebGL GPU Spoofing ===
        if self.config.get('webgl', True):
            script_parts.append(f"""
    // === 3. WebGL GPU Spoofing ===
    const getParameterOriginal = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return '{config['gpu']['vendor']}';
        if (parameter === 37446) return '{config['gpu']['renderer']}';
        return getParameterOriginal.call(this, parameter);
    }};

    if (typeof WebGL2RenderingContext !== 'undefined') {{
        WebGL2RenderingContext.prototype.getParameter = WebGLRenderingContext.prototype.getParameter;
    }}
""")
        else:
            script_parts.append("\n    // === 3. WebGL GPU Spoofing === DISABLED\n")

        # === 4. Canvas Noise Injection ===
        if self.config.get('canvas', True):
            script_parts.append(f"""
    // === 4. Canvas Noise Injection ===
    const getImageDataOriginal = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function(...args) {{
        const imageData = getImageDataOriginal.apply(this, args);
        const data = imageData.data;
        const noiseRate = {config['canvas']['noise_rate']};
        const noiseAmount = {config['canvas']['noise_amount']};

        for (let i = 0; i < data.length; i += 4) {{
            if (Math.random() < noiseRate) {{
                const noise = Math.floor(Math.random() * (noiseAmount * 2)) - noiseAmount;
                data[i] = Math.max(0, Math.min(255, data[i] + noise));
                data[i+1] = Math.max(0, Math.min(255, data[i+1] + noise));
                data[i+2] = Math.max(0, Math.min(255, data[i+2] + noise));
            }}
        }}
        return imageData;
    }};
""")
        else:
            script_parts.append("\n    // === 4. Canvas Noise Injection === DISABLED\n")

        # === 5. Audio Context Spoofing ===
        if self.config.get('audio', True):
            script_parts.append(f"""
    // === 5. Audio Context Spoofing ===
    const AudioContextOriginal = window.AudioContext || window.webkitAudioContext;
    if (AudioContextOriginal) {{
        const createOscillatorOriginal = AudioContextOriginal.prototype.createOscillator;
        AudioContextOriginal.prototype.createOscillator = function() {{
            const oscillator = createOscillatorOriginal.call(this);
            const frequencyOriginal = oscillator.frequency.value;
            Object.defineProperty(oscillator.frequency, 'value', {{
                get: function() {{ return frequencyOriginal + {config['audio_noise']}; }},
                set: function(v) {{ frequencyOriginal = v; }}
            }});
            return oscillator;
        }};
    }}
""")
        else:
            script_parts.append("\n    // === 5. Audio Context Spoofing === DISABLED\n")

        # === 6. Language Spoofing ===
        if self.config.get('language', True):
            script_parts.append(f"""
    // === 6. Language Spoofing ===
    Object.defineProperty(navigator, 'language', {{
        get: function() {{ return '{config['language']}'; }}
    }});

    Object.defineProperty(navigator, 'languages', {{
        get: function() {{ return ['{config['language']}']; }}
    }});
""")
        else:
            script_parts.append("\n    // === 6. Language Spoofing === DISABLED\n")

        # === 7. Touch Points Spoofing ===
        if self.config.get('touch', True):
            script_parts.append(f"""
    // === 7. Touch Points Spoofing ===
    Object.defineProperty(navigator, 'maxTouchPoints', {{
        get: function() {{ return {config['touch_points']}; }}
    }});
""")
        else:
            script_parts.append("\n    // === 7. Touch Points Spoofing === DISABLED\n")

        # === 8. WebRTC IP Leak Protection (항상 활성화) ===
        script_parts.append("""
    // === 8. WebRTC IP Leak Protection ===
    if (window.RTCPeerConnection) {
        const originalRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(...args) {
            if (args[0] && args[0].iceServers) {
                args[0].iceServers = [];
            }
            return new originalRTC(...args);
        };
    }
""")

        # 푸터
        script_parts.append(f"""
    console.log('[Fingerprint Spoofer] Preset: {self.preset}, Features: {", ".join(active_features)}');
}})();
""")

        script = "".join(script_parts)
        return script, config

    def print_config(self, config: Dict):
        """설정 정보 출력 (프리셋 정보 포함)"""
        active_features = [k for k, v in self.config.items() if v]
        print(f"   🎲 핑거프린트 스푸핑 설정 (Preset: {self.preset})")
        print(f"      활성 기능: {', '.join(active_features)}")

        if self.config.get('hardware', True):
            print(f"      CPU: {config['cores']}코어")
            print(f"      RAM: {config['memory']}GB")

        if self.config.get('screen', True):
            print(f"      화면: {config['screen']['width']}x{config['screen']['height']} ({config['screen']['color_depth']}bit)")

        if self.config.get('webgl', True):
            print(f"      GPU: {config['gpu']['vendor']} - {config['gpu']['renderer'][:50]}")

        if self.config.get('canvas', True):
            print(f"      Canvas: {config['canvas']['noise_rate']:.2%} 노이즈, ±{config['canvas']['noise_amount']}")

        if self.config.get('language', True):
            print(f"      언어: {config['language']}")

        if self.config.get('touch', True):
            print(f"      터치: {config['touch_points']}포인트")


# 편의 함수
def create_spoof_script(print_info: bool = True) -> Tuple[str, Dict]:
    """
    스푸핑 스크립트 생성 (편의 함수)

    Args:
        print_info: 설정 정보 출력 여부

    Returns:
        (script, config) 튜플
    """
    spoofer = FingerprintSpoofer()
    script, config = spoofer.generate_spoof_script()

    if print_info:
        spoofer.print_config(config)

    return script, config


if __name__ == "__main__":
    # 테스트
    print("=" * 60)
    print("🔬 핑거프린트 스푸핑 모듈 테스트")
    print("=" * 60)

    # 5개 랜덤 설정 생성
    spoofer = FingerprintSpoofer()

    for i in range(1, 6):
        print(f"\n[테스트 {i}]")
        script, config = spoofer.generate_spoof_script()
        spoofer.print_config(config)

    print("\n" + "=" * 60)
    print("✅ 모듈 테스트 완료")
    print("=" * 60)
