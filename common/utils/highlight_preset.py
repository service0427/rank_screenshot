#!/usr/bin/env python3
"""
상품 강조 표시 프리셋
스크린샷 시 매칭된 상품을 시각적으로 강조하는 다양한 스타일 제공
"""

from typing import Dict, Any
from dataclasses import dataclass
from common.constants import Config


@dataclass
class HighlightStyle:
    """하이라이트 스타일 설정"""

    # 테두리 설정
    border_width: int = 5
    border_color: str = "#FF0000"
    border_style: str = "solid"  # solid, dashed, dotted
    border_offset: int = -5

    # 배경 오버레이 설정
    background_overlay: bool = True
    background_color: str = "rgba(255, 255, 0, 0.15)"  # 연한 노란색

    # P/I/V 라벨 표시 설정
    show_piv_labels: bool = True
    label_font_size: int = 15
    label_background: str = "rgba(0, 0, 0, 0.85)"
    label_text_color: str = "#CCCCCC"
    label_padding: int = 10
    label_border_radius: int = 4

    # 매칭 강조 색상
    match_highlight_color: str = "#FFFF00"

    # 순위 배지 설정
    show_rank_badge: bool = True
    rank_badge_size: int = 45
    rank_badge_color: str = "#FF6B6B"
    rank_badge_text_color: str = "#FFFFFF"


# HighlightPresets 클래스 제거됨
# 이제 Config 값을 직접 사용하여 HighlightStyle 생성


def generate_highlight_js(
    element_selector: str,
    style: HighlightStyle,
    product_data: Dict[str, Any],
    match_condition: str
) -> str:
    """
    하이라이트 JavaScript 코드 생성

    Args:
        element_selector: 대상 요소 (element 객체를 직접 전달)
        style: 하이라이트 스타일
        product_data: 상품 데이터 (product_id, item_id, vendor_item_id, rank 포함)
        match_condition: 매칭 조건 (어떤 값이 일치했는지)

    Returns:
        실행할 JavaScript 코드
    """

    # 매칭된 항목 파싱
    matched_fields = []

    # 완전 일치 체크 (모든 필드 일치)
    if "완전" in match_condition or "complete" in match_condition.lower():
        matched_fields = ["product", "item", "vendor"]
    else:
        # 개별 필드 매칭 체크
        if "product_id" in match_condition.lower():
            matched_fields.append("product")
        if "item_id" in match_condition.lower():
            matched_fields.append("item")
        if "vendor_item_id" in match_condition.lower():
            matched_fields.append("vendor")

    # P/I/V 라벨 HTML 생성
    piv_html = ""
    if style.show_piv_labels:
        # Config 값으로 위치 직접 설정
        from common.constants import Config
        pos_parts = []
        if Config.HIGHLIGHT_LABEL_TOP: pos_parts.append(f"top: {Config.HIGHLIGHT_LABEL_TOP};")
        if Config.HIGHLIGHT_LABEL_RIGHT: pos_parts.append(f"right: {Config.HIGHLIGHT_LABEL_RIGHT};")
        if Config.HIGHLIGHT_LABEL_BOTTOM: pos_parts.append(f"bottom: {Config.HIGHLIGHT_LABEL_BOTTOM};")
        if Config.HIGHLIGHT_LABEL_LEFT: pos_parts.append(f"left: {Config.HIGHLIGHT_LABEL_LEFT};")
        position_style = " ".join(pos_parts)

        # 각 항목의 색상 결정 (매칭된 항목은 강조)
        def get_color(field_name):
            return style.match_highlight_color if field_name in matched_fields else style.label_text_color

        product_color = get_color("product")
        item_color = get_color("item")
        vendor_color = get_color("vendor")

        piv_html = f"""
        <div class="piv-label" style="
            position: absolute;
            {position_style}
            background: {style.label_background};
            color: {style.label_text_color};
            padding: {style.label_padding}px;
            border-radius: {style.label_border_radius}px;
            font-family: 'Courier New', monospace;
            font-size: {style.label_font_size}px;
            line-height: 1.4;
            z-index: 10000;
            pointer-events: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        ">
            <div class="piv-product" style="color: {product_color}; font-weight: {'bold' if 'product' in matched_fields else 'normal'};">
                P: {product_data.get('product_id', 'N/A')}
            </div>
            <div class="piv-item" style="color: {item_color}; font-weight: {'bold' if 'item' in matched_fields else 'normal'};">
                I: {product_data.get('item_id', 'N/A')}
            </div>
            <div class="piv-vendor" style="color: {vendor_color}; font-weight: {'bold' if 'vendor' in matched_fields else 'normal'};">
                V: {product_data.get('vendor_item_id', 'N/A')}
            </div>
        </div>
        """

    # 순위 배지 HTML 생성 (11등 이상만 표시)
    from common.constants import Config
    rank_badge_html = ""
    rank = product_data.get('rank')
    if style.show_rank_badge and rank and rank >= Config.HIGHLIGHT_RANK_BADGE_MIN_RANK:
        # Config 값으로 위치 직접 설정
        pos_parts = []
        if Config.HIGHLIGHT_RANK_BADGE_TOP: pos_parts.append(f"top: {Config.HIGHLIGHT_RANK_BADGE_TOP};")
        if Config.HIGHLIGHT_RANK_BADGE_RIGHT: pos_parts.append(f"right: {Config.HIGHLIGHT_RANK_BADGE_RIGHT};")
        if Config.HIGHLIGHT_RANK_BADGE_BOTTOM: pos_parts.append(f"bottom: {Config.HIGHLIGHT_RANK_BADGE_BOTTOM};")
        if Config.HIGHLIGHT_RANK_BADGE_LEFT: pos_parts.append(f"left: {Config.HIGHLIGHT_RANK_BADGE_LEFT};")
        badge_position = " ".join(pos_parts)

        rank_badge_html = f"""
        <div class="rank-badge" style="
            position: absolute;
            {badge_position}
            width: {style.rank_badge_size}px;
            height: {style.rank_badge_size}px;
            background: {style.rank_badge_color};
            color: {style.rank_badge_text_color};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: Arial, sans-serif;
            font-size: {style.rank_badge_size // 2}px;
            font-weight: bold;
            z-index: 10001;
            pointer-events: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        ">
            {product_data.get('rank', '?')}
        </div>
        """

    # JavaScript 코드 생성 (arguments[0]를 element로 사용)
    js_code = f"""
var element = arguments[0];

// 테두리 설정
element.style.outline = '{style.border_width}px {style.border_style} {style.border_color}';
element.style.outlineOffset = '{style.border_offset}px';
element.style.position = 'relative';

// 배경 오버레이
{'element.style.backgroundColor = "' + style.background_color + '";' if style.background_overlay else ''}

// P/I/V 라벨 추가
{f"element.insertAdjacentHTML('beforeend', `{piv_html}`);" if style.show_piv_labels else ''}

// 순위 배지 추가
{f"element.insertAdjacentHTML('beforeend', `{rank_badge_html}`);" if style.show_rank_badge else ''}
    """

    return js_code.strip()
