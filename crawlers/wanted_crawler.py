import time
import logging
from typing import List
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawlers.base_crawler import BaseCrawler
from models.job import JobPosting
from config import Config

logger = logging.getLogger(__name__)


class WantedCrawler(BaseCrawler):
    """원티드 크롤러 - 무한 스크롤 지원"""

    BASE_URL = "https://www.wanted.co.kr"

    def __init__(self):
        super().__init__()
        self.source_name = "wanted"

    def build_search_url(self, keyword: str = "", **filters) -> str:
        """원티드 검색 URL 생성"""
        if keyword:
            return f"{self.BASE_URL}/search?query={quote_plus(keyword)}&type=position"
        else:
            # 직종 카테고리별 URL
            return f"{self.BASE_URL}/wdlist/518?country=kr&job_sort=job.latest_order&years=-1&locations=all"

    def crawl(self, keyword: str = "", **filters) -> List[JobPosting]:
        """원티드 크롤링 - 무한 스크롤 처리"""
        jobs = []

        if keyword:
            jobs = self._crawl_search(keyword, **filters)
        else:
            jobs = self._crawl_listing(**filters)

        return jobs

    def _crawl_search(self, keyword: str, **filters) -> List[JobPosting]:
        """검색 결과 크롤링"""
        url = self.build_search_url(keyword)
        logger.info(f"[원티드] 검색 크롤링: {url}")

        self.driver.get(url)
        time.sleep(3)

        # 무한 스크롤로 데이터 로드
        self._infinite_scroll(max_scrolls=Config.MAX_PAGES * 5)

        return self._parse_search_results()

    def _crawl_listing(self, **filters) -> List[JobPosting]:
        """목록 페이지 크롤링"""
        # 경력 필터
        exp = filters.get("experience", "전체")
        years_param = "-1"
        exp_map = {
            "신입": "0", "1년": "1", "2년": "2",
            "3년": "3", "5년": "5", "7년": "7", "10년 이상": "10"
        }
        if exp in exp_map:
            years_param = exp_map[exp]

        # 지역 필터
        region = filters.get("region", "전체")
        location_param = "all"
        region_map = {
            "서울": "seoul", "경기": "gyeonggi",
            "부산": "busan", "대구": "daegu",
            "인천": "incheon", "광주": "gwangju"
        }
        if region in region_map:
            location_param = f"kr.{region_map[region]}.all"

        url = (
            f"{self.BASE_URL}/wdlist/518?country=kr"
            f"&job_sort=job.latest_order"
            f"&years={years_param}"
            f"&locations={location_param}"
        )
        logger.info(f"[원티드] 목록 크롤링: {url}")

        self.driver.get(url)
        time.sleep(3)

        # 무한 스크롤
        self._infinite_scroll(max_scrolls=Config.MAX_PAGES * 5)

        return self._parse_listing_results()

    def _infinite_scroll(self, max_scrolls=20):
        """원티드 무한 스크롤 처리"""
        logger.info("[원티드] 무한 스크롤 시작")
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight"
        )
        scroll_count = 0
        no_change_count = 0

        while scroll_count < max_scrolls:
            # 스크롤 다운
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(Config.SCROLL_PAUSE)

            # "더보기" 버튼 확인 및 클릭
            try:
                more_btn_selectors = [
                    "button.more", "[class*='ShowMoreButton']",
                    "[class*='more-btn']", "button[data-attribute-id='show__more']"
                ]
                for sel in more_btn_selectors:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for btn in btns:
                        if btn.is_displayed():
                            self.safe_click(btn)
                            time.sleep(1.5)
                            break
            except Exception:
                pass

            new_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )

            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:
                    break
            else:
                no_change_count = 0

            last_height = new_height
            scroll_count += 1

        logger.info(f"[원티드] 스크롤 완료: {scroll_count}회")

    def _parse_search_results(self) -> List[JobPosting]:
        """검색 결과 파싱"""
        jobs = []

        card_selectors = [
            "[class*='JobCard']", "[class*='job-card']",
            "a[href*='/wd/']", ".position-card",
            "[data-cy='job-card']"
        ]

        items = []
        for sel in card_selectors:
            items = self.driver.find_elements(By.CSS_SELECTOR, sel)
            if items:
                logger.info(f"[원티드] 셀렉터 '{sel}'로 {len(items)}개 발견")
                break

        for item in items:
            try:
                job = self._parse_card(item)
                if job and not job.is_expired():
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[원티드] 카드 파싱 에러: {e}")
                continue

        return jobs

    def _parse_listing_results(self) -> List[JobPosting]:
        """목록 결과 파싱"""
        return self._parse_search_results()

    def _parse_card(self, item) -> JobPosting:
        """개별 카드 파싱"""
        # URL 추출
        url = ""
        try:
            if item.tag_name == "a":
                url = item.get_attribute("href") or ""
            else:
                link = item.find_element(By.CSS_SELECTOR, "a")
                url = link.get_attribute("href") or ""
        except Exception:
            pass

        if url and not url.startswith("http"):
            url = self.BASE_URL + url

        # 제목
        title_selectors = [
            "[class*='job-card-position']", "[class*='JobCard__title']",
            "[class*='position']", "p.job-card-position",
            "strong", "h3", "h4", ".title"
        ]
        title = ""
        for sel in title_selectors:
            title = self.safe_get_text(item, sel)
            if title and len(title) > 2:
                break

        if not title:
            # 전체 텍스트에서 추출
            full_text = item.text.strip()
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            title = lines[0] if lines else ""

        if not title:
            return None

        # 회사명
        company_selectors = [
            "[class*='job-card-company']", "[class*='JobCard__company']",
            "[class*='company']", ".company-name", "span.company"
        ]
        company = ""
        for sel in company_selectors:
            company = self.safe_get_text(item, sel)
            if company:
                break

        if not company:
            full_text = item.text.strip()
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            company = lines[1] if len(lines) > 1 else ""

        # 지역
        location_selectors = [
            "[class*='job-card-location']", "[class*='location']",
            ".location"
        ]
        location = ""
        for sel in location_selectors:
            location = self.safe_get_text(item, sel)
            if location:
                break

        if not location:
            full_text = item.text.strip()
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            location = lines[2] if len(lines) > 2 else ""

        # 기술스택 추출 (텍스트에서)
        tech_stack = []
        full_text = item.text.lower()
        for tech in Config.TECH_STACKS:
            if tech.lower() in full_text:
                tech_stack.append(tech)

        return JobPosting(
            title=title,
            company=company,
            url=url,
            source="wanted",
            location=location,
            tech_stack=tech_stack,
            deadline="상시채용"
        )