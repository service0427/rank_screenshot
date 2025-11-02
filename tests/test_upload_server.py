#!/usr/bin/env python3
"""
스크린샷 업로드 테스트 서버
Flask를 사용한 간단한 업로드 서버

사용법:
    pip install flask
    python3 test_upload_server.py
"""

from flask import Flask, request, jsonify
from pathlib import Path
from datetime import datetime
import os

app = Flask(__name__)

# 업로드 파일 저장 디렉토리
UPLOAD_DIR = Path(__file__).parent / "uploaded_screenshots"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    스크린샷 파일 업로드 엔드포인트
    실제 서버(toprekr.com)와 동일한 형식
    """
    try:
        # 파일 확인 ('image' 필드 사용 - 실제 서버와 동일)
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image part in request'
            }), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # 메타데이터 추출
        keyword = request.form.get('keyword', '')
        version = request.form.get('version', '')
        vpn_num = request.form.get('vpn_num', '')
        product_name = request.form.get('product_name', '')
        product_rank = request.form.get('product_rank', '')
        capture_type = request.form.get('capture_type', '')
        timestamp = request.form.get('timestamp', '')

        # 저장 경로 생성
        version_dir = UPLOAD_DIR / f"chrome-{version}" if version else UPLOAD_DIR / "chrome-unknown"

        if vpn_num and vpn_num != '0':
            target_dir = version_dir / f"vpn{vpn_num}"
        else:
            target_dir = version_dir / "local"

        target_dir.mkdir(parents=True, exist_ok=True)

        # 파일 저장
        save_path = target_dir / file.filename
        file.save(str(save_path))

        # 파일 크기 확인
        file_size = save_path.stat().st_size

        # 로그 출력
        print("\n" + "=" * 60)
        print("📥 파일 업로드 수신")
        print("=" * 60)
        print(f"파일명: {file.filename}")
        print(f"크기: {file_size / 1024:.2f} KB")
        print(f"저장 경로: {save_path}")
        print(f"키워드: {keyword}")
        print(f"버전: {version}")
        print(f"VPN: {vpn_num if vpn_num else 'local'}")
        print(f"상품명: {product_name[:50]}..." if len(product_name) > 50 else f"상품명: {product_name}")
        print(f"상품 순위: {product_rank}")
        print(f"캡처 타입: {capture_type}")
        print(f"타임스탬프: {timestamp}")
        print("=" * 60 + "\n")

        # 성공 응답 (실제 서버와 동일한 형식)
        image_url = f"http://localhost:8000/images/{file.filename}"

        return jsonify({
            'success': True,
            'id': 1,  # 임시 ID
            'url': image_url,
            'filename': file.filename,
            'original_name': file.filename,
            'size': file_size,
            'width': 1920,  # 임시 값
            'height': 1080,  # 임시 값
            'mime_type': 'image/png',
            'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'metadata': {
                'keyword': keyword,
                'version': version,
                'vpn_num': vpn_num,
                'product_name': product_name,
                'product_rank': product_rank,
                'capture_type': capture_type,
                'timestamp': timestamp
            }
        }), 200

    except Exception as e:
        print(f"\n❌ 업로드 처리 오류: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'ok',
        'message': 'Upload server is running',
        'upload_dir': str(UPLOAD_DIR)
    }), 200


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 스크린샷 업로드 테스트 서버 시작")
    print("=" * 60)
    print(f"서버 주소: http://localhost:8000")
    print(f"업로드 엔드포인트: http://localhost:8000/upload")
    print(f"헬스 체크: http://localhost:8000/health")
    print(f"저장 디렉토리: {UPLOAD_DIR}")
    print("=" * 60 + "\n")

    # 서버 실행 (포트 8000)
    app.run(host='0.0.0.0', port=8000, debug=True)
