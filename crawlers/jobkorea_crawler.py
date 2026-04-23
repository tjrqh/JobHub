import time
import logging
from typing import List
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By

from crawlers.base_crawler import BaseCrawler
from models.job import JobPosting
from config import Config

logger = logging.getLogger(__name__)


class JobKoreaCrawler(BaseCrawler):
    """잡코리아 크롤러"""

    BASE_URL = "https://www.jobkorea.co.kr"

    def __init__(self):
        super().__init__()
        self.source_name = "jobkorea"

    def build_search_url(self, keyword: str = "", **filters) -> str:
        """잡코리아 검색 URL 생성"""
        params = []

        if keyword:
            params.append(f"stext={quote_plus(keyword)}")

        # 경력
        exp = filters.get("experience", "전체")
        exp_map = {
            "신입": "1", "1년": "2", "2년": "2",
            "3년": "3", "5년": "5", "7년": "7", "10년 이상": "10"
        }
        if exp in exp_map:
            params.append(f"careerType={exp_map[exp]}")

        # 학력
        edu = filters.get("education", "전체")
        edu_map = {
            "학력무관": "0", "고졸": "1", "초대졸": "2",
            "대졸": "3", "석사": "4", "박사": "5"
        }
        if edu in edu_map:
            params.append(f"education={edu_map[edu]}")

        # 지역
        location = filters.get("location", "전체")
        location_map = {
            "서울": "I000", "경기": "B000", "인천": "H000",
            "부산": "C000", "대구": "F000", "광주": "D000",
            "대전": "G000", "울산": "E000", "세종": "S000"
        }
        if location in location_map:
            params.append(f"local={location_map[location]}")

        param_str = "&".join(params)
        return f"{self.BASE_URL}/Search/?{param_str}"

    def crawl(self, keyword: str = "", **filters) -> List[JobPosting]:
        """잡코리아 크롤링"""
        url = self.build_search_url(keyword, **filters)
        jobs = []

        for page in range(1, Config.MAX_PAGES + 1):
            page_url = f"{url}&Page_No={page}"
            logger.info(f"[잡코리아] 페이지 {page} 크롤링: {page_url}")

            try:
                self.driver.get(page_url)
                time.sleep(3)

                # 팝업 닫기
                self._close_popups()

                # "더보기" 버튼 클릭
                self._click_more_buttons()

                # 공고 목록
                items = self.wait_for_elements(
                    By.CSS_SELECTOR,
                    ".recruit-info .list-default .list-post, "
                    ".list-default .list-post, "
                    ".post-list-info .post-list-corp",
                    timeout=10
                )

                if not items:
                    # 대체 셀렉터
                    items = self.wait_for_elements(
                        By.CSS_SELECTOR,
                        "article.list-item, .dev-list .list-item",
                        timeout=5
                    )

                if not items:
                    logger.info(f"[잡코리아] 페이지 {page}: 결과 없음")
                    break

                for item in items:
                    try:
                        job = self._parse_item(item)
                        if job and not job.is_expired():
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"[잡코리아] 파싱 에러: {e}")
                        continue

            except Exception as e:
                logger.error(f"[잡코리아] 페이지 {page} 에러: {e}")
                break

        return jobs

    def _close_popups(self):
        """팝업 닫기"""
        popup_selectors = [
            ".devPopLayClose", ".btn-close", ".popup-close",
            "[class*='close']", ".modal .close"
        ]
        for sel in popup_selectors:
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in btns:
                    if btn.is_displayed():
                        self.safe_click(btn)
                        time.sleep(0.3)
            except Exception:
                pass

    def _click_more_buttons(self, max_clicks=3):
        """'더보기' 버튼 클릭"""
        more_selectors = [
            ".btn-more", ".btn_more", "[class*='more']",
            "button.more", "a.more"
        ]
        click_count = 0

        for sel in more_selectors:
            while click_count < max_clicks:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    clicked = False
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            if self.safe_click(btn):
                                click_count += 1
                                time.sleep(1.5)
                                clicked = True
                                break
                    if not clicked:
                        break
                except Exception:
                    break

    def _parse_item(self, item) -> JobPosting:
        """개별 공고 파싱"""
        # 제목
        title_selectors = [
            ".post-list-info a.title", ".list-section-title a",
            "a.title", ".title a", "h3 a", ".tit_job a"
        ]
        title = ""
        url = ""
        for sel in title_selectors:
            title = self.safe_get_text(item, sel)
            if title:
                url = self.safe_get_attribute(item, sel, "href")
                break

        if not title:
            return None

        if url and not url.startswith("http"):
            url = self.BASE_URL + url

        # 회사명
        company_selectors = [
            ".post-list-corp a.name", ".corp-name a",
            "a.name", ".name a", ".corp_name"
        ]
        company = ""
        for sel in company_selectors:
            company = self.safe_get_text(item, sel)
            if company:
                break

        # 조건
        option_selectors = [
            ".post-list-info .option", ".etc", ".info-detail",
            ".option span", ".chip-information-group"
        ]
        location = ""
        experience = ""
        education = ""

        for sel in option_selectors:
            try:
                spans = item.find_elements(By.CSS_SELECTOR, f"{sel} span, {sel} p")
                texts = [s.text.strip() for s in spans if s.text.strip()]
                if texts:
                    for t in texts:
                        if any(loc in t for loc in ["서울", "경기", "부산", "대구", "인천",
                                                      "광주", "대전", "울산", "세종", "강원"]):
                            location = t
                        elif any(e in t for e in ["신입", "경력", "년"]):
                            experience = t
                        elif any(e in t for e in ["대졸", "고졸", "석사", "박사", "학력"]):
                            education = t
                    break
            except Exception:
                continue

        # 마감일
        deadline_selectors = [".date", ".deadline", ".end-date"]
        deadline = ""
        for sel in deadline_selectors:
            deadline = self.safe_get_text(item, sel)
            if deadline:
                break

        return JobPosting(
            title=title,
            company=company,
            url=url,
            source="jobkorea",
            location=location,
            experience=experience,
            education=education,
            deadline=deadline
        )