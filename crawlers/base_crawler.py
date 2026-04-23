import time
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager

from config import Config
from models.job import JobPosting

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """크롤러 베이스 클래스"""

    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.jobs: List[JobPosting] = []
        self.source_name = "base"

    def setup_driver(self):
        """Chrome WebDriver 설정"""
        options = Options()

        if Config.CHROME_HEADLESS:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)

        # Selenium 탐지 방지
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
        )

    def teardown_driver(self):
        """드라이버 종료"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def safe_click(self, element, retries=3):
        """안전한 클릭 (재시도 포함)"""
        for attempt in range(retries):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", element
                )
                time.sleep(0.5)
                element.click()
                return True
            except (ElementClickInterceptedException, StaleElementReferenceException):
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Click failed (attempt {attempt + 1}): {e}")
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    time.sleep(1)
        return False

    def scroll_down(self, times=3, pause=None):
        """페이지 스크롤 다운"""
        pause = pause or Config.SCROLL_PAUSE
        for _ in range(times):
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(pause)

    def scroll_until_no_change(self, max_scrolls=30, pause=None):
        """더 이상 컨텐츠가 로드되지 않을 때까지 스크롤"""
        pause = pause or Config.SCROLL_PAUSE
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight"
        )
        scroll_count = 0

        while scroll_count < max_scrolls:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(pause)

            new_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )
            if new_height == last_height:
                break
            last_height = new_height
            scroll_count += 1

    def wait_for_element(self, by, value, timeout=10):
        """요소가 나타날 때까지 대기"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def wait_for_elements(self, by, value, timeout=10):
        """요소들이 나타날 때까지 대기"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            return []

    def safe_get_text(self, element, selector, by=By.CSS_SELECTOR, default=""):
        """안전하게 텍스트 추출"""
        try:
            el = element.find_element(by, selector)
            return el.text.strip()
        except (NoSuchElementException, StaleElementReferenceException):
            return default

    def safe_get_attribute(self, element, selector, attr, by=By.CSS_SELECTOR, default=""):
        """안전하게 속성 추출"""
        try:
            el = element.find_element(by, selector)
            return el.get_attribute(attr) or default
        except (NoSuchElementException, StaleElementReferenceException):
            return default

    @abstractmethod
    def build_search_url(self, keyword: str = "", **filters) -> str:
        """검색 URL 생성"""
        pass

    @abstractmethod
    def crawl(self, keyword: str = "", **filters) -> List[JobPosting]:
        """크롤링 실행"""
        pass

    def run(self, keyword: str = "", **filters) -> List[JobPosting]:
        """크롤링 실행 (드라이버 관리 포함)"""
        try:
            logger.info(f"[{self.source_name}] 크롤링 시작: keyword={keyword}")
            self.setup_driver()
            self.jobs = self.crawl(keyword, **filters)
            logger.info(f"[{self.source_name}] {len(self.jobs)}개 수집 완료")
            return self.jobs
        except Exception as e:
            logger.error(f"[{self.source_name}] 크롤링 에러: {e}", exc_info=True)
            return []
        finally:
            self.teardown_driver()