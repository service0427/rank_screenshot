#!/usr/bin/env python3
"""
Human Behavior Simulation - Selenium 기반
사람처럼 행동하는 시뮬레이션
"""

import time
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from ..constants import Config


def random_delay(min_ms: int, max_ms: int):
    """랜덤 딜레이"""
    delay = random.uniform(min_ms, max_ms) / 1000
    time.sleep(delay)


def natural_typing(element, text: str, clear_first: bool = True):
    """
    자연스러운 타이핑 시뮬레이션
    - 한 글자씩 입력
    - 랜덤 딜레이 (80-200ms)
    - 단어 사이 추가 딜레이

    Args:
        element: Selenium WebElement
        text: 입력할 텍스트
        clear_first: 먼저 지우기
    """
    if clear_first:
        try:
            element.clear()
        except:
            # clear()가 안 되면 Ctrl+A + Delete
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)

    for i, char in enumerate(text):
        element.send_keys(char)

        # 기본 타이핑 딜레이
        random_delay(Config.TYPING_MIN_DELAY, Config.TYPING_MAX_DELAY)

        # 단어 사이 추가 딜레이
        if char == " " and i < len(text) - 1:
            random_delay(200, 500)


def human_scroll(driver, distance: int = None, steps: int = 5):
    """
    사람처럼 스크롤
    - 여러 단계로 나누어 스크롤
    - 각 단계마다 랜덤 딜레이

    Args:
        driver: Selenium WebDriver
        distance: 스크롤 거리 (픽셀)
        steps: 스크롤 단계 수
    """
    if distance is None:
        distance = random.randint(300, 800)

    step_size = distance // steps

    for i in range(steps):
        # 마지막 스텝은 남은 거리 전부
        if i == steps - 1:
            scroll_amount = distance - (step_size * (steps - 1))
        else:
            scroll_amount = step_size + random.randint(-20, 20)

        driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
        random_delay(Config.SCROLL_PAUSE_MIN, Config.SCROLL_PAUSE_MAX)


def human_click(element, delay_after: bool = True):
    """
    사람처럼 클릭
    - 요소로 스크롤
    - 호버
    - 클릭
    - 딜레이

    Args:
        element: Selenium WebElement
        delay_after: 클릭 후 딜레이 여부
    """
    driver = element.parent

    # 스크롤
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        random_delay(200, 500)
    except:
        pass

    # 호버
    try:
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        random_delay(300, 700)
    except:
        pass

    # 클릭
    element.click()

    if delay_after:
        random_delay(Config.CLICK_MIN_DELAY, Config.CLICK_MAX_DELAY)


def hover_element(element, duration_ms: int = None):
    """
    요소에 마우스 호버
    - 호버 후 딜레이

    Args:
        element: Selenium WebElement
        duration_ms: 호버 유지 시간
    """
    if duration_ms is None:
        duration_ms = random.randint(500, 1500)

    driver = element.parent

    # 스크롤
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    except:
        pass

    # 호버
    try:
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
    except:
        pass

    # 딜레이
    time.sleep(duration_ms / 1000)


def move_mouse_random(driver):
    """
    랜덤 마우스 이동
    - 화면의 랜덤 위치로 마우스 이동

    Args:
        driver: Selenium WebDriver
    """
    try:
        # 페이지의 body 요소
        body = driver.find_element("tag name", "body")

        # 랜덤 오프셋
        offset_x = random.randint(-200, 200)
        offset_y = random.randint(-200, 200)

        actions = ActionChains(driver)
        actions.move_to_element_with_offset(body, offset_x, offset_y).perform()

        random_delay(100, 300)
    except:
        pass


# ===================================================================
# High-level Behavior Combinations
# ===================================================================

def after_page_load(driver):
    """페이지 로드 후 자연스러운 행동"""
    # 페이지 로드 대기
    random_delay(Config.PAGE_LOAD_MIN_DELAY, Config.PAGE_LOAD_MAX_DELAY)

    # 약간의 스크롤
    human_scroll(driver, distance=random.randint(100, 300), steps=3)

    # 마우스 이동
    move_mouse_random(driver)


def before_search(driver):
    """
    검색 전 자연스러운 행동 (1-3초 소요)
    - Akamai 봇 탐지 우회를 위한 마우스 움직임 패턴
    - 1-2회 랜덤 마우스 이동
    - 가끔 미세한 스크롤 추가
    """
    # 초기 딜레이 (200-500ms)
    random_delay(200, 500)

    # 랜덤 마우스 이동 (1-2회)
    num_moves = random.randint(1, 2)
    for i in range(num_moves):
        move_mouse_random(driver)
        random_delay(200, 500)

        # 20% 확률로 미세한 스크롤 추가
        if random.random() < 0.2:
            scroll_amount = random.randint(-100, 100)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
            random_delay(100, 300)

    # 검색 전 마지막 딜레이 (300-600ms)
    random_delay(300, 600)


def before_product_click(element):
    """상품 클릭 전 자연스러운 행동"""
    driver = element.parent

    # 요소까지 스크롤
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        random_delay(300, 800)
    except:
        pass

    # 호버
    try:
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        random_delay(800, 2000)
    except:
        pass
