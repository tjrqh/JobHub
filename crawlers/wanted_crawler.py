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
            return f"{self.BASE_URL}/wdlist/518?country=kr&job_sort=job.latest_order&years=-1&locations=all"

    def crawl(self, keyword: str = "", **filters) -> List[JobPosting]:
        """원티드 크롤링 - 무한 스크롤 처리"""
        jobs = []

        if keyword:
            jobs = self._crawl_search(keyword, **filters)
        else:
            jobs = self._crawl_listing(**filters)

        logger.info(f"[원티드] 총 {len(jobs)}개 수집 완료")
        return jobs

    def _crawl_search(self, keyword: str, **filters) -> List[JobPosting]:
        """검색 결과 크롤링"""
        url = self.build_search_url(keyword)
        logger.info(f"[원티드] 검색 크롤링: {url}")

        try:
            self.driver.get(url)
            time.sleep(3)
            self._infinite_scroll(max_scrolls=Config.MAX_PAGES * 5)
            return self._parse_search_results()
        except Exception as e:
            logger.error(f"[원티드] 검색 크롤링 실패: {e}")
            return []

    def _crawl_listing(self, **filters) -> List[JobPosting]:
        """목록 페이지 크롤링"""

        # 1. 카테고리
        category = filters.get("category", "전체")
        category_map = {
            "웹개발": "873",
            "SW개발": "10110",
            "앱개발": "677",
            "데이터분석": "1024",
            "AI/ML" : "1634",
            "서버/백엔드" : "872",
            "프론트엔드": "669",
            "DevOps": "674",
            "QA/테스트": "676",
            "보안": "10556",
            "DBA": "10231",
            "네트워크": "665"

        }
        category_code = category_map.get(category, "518")  # 기본 518

        # 2. 경력
        exp = filters.get("experience", "전체")
        years_param = "-1"
        exp_map = {
            "신입": "0", "1년": "1", "2년": "2",
            "3년": "3", "5년": "5", "7년": "7", "10년 이상": "10"
        }
        if exp in exp_map:
            years_param = exp_map[exp]

        # 3. 지역
        location = filters.get("location", "전체")
        location_param = "all"
        location_map = {
            "서울": "seoul", "경기": "gyeonggi",
            "부산": "busan", "대구": "daegu",
            "인천": "incheon", "광주": "gwangju"
        }
        if location in location_map:
            location_param = f"kr.{location_map[location]}.all"
        # ✅ URL 분기 처리
        if category == "전체" or not category_code:
            # 기본
            path = "518"
        elif category == "보안":
            # 👉 518 없이 바로
            path = category_code
        else:
            # 👉 518 + 하위 카테고리
            path = f"518/{category_code}"

        url = (
            f"{self.BASE_URL}/wdlist/{path}?country=kr"
            f"&job_sort=job.latest_order"
            f"&years={years_param}"
            f"&locations={location_param}"
        )

        logger.info(f"[원티드] 목록 크롤링: {url}")

        try:
            self.driver.get(url)
            time.sleep(3)
            self._infinite_scroll(max_scrolls=Config.MAX_PAGES * 5)
            return self._parse_listing_results()
        except Exception as e:
            logger.error(f"[원티드] 목록 크롤링 실패: {e}")
            return []

    def _infinite_scroll(self, max_scrolls=20):
        """원티드 무한 스크롤 처리"""
        logger.info("[원티드] 무한 스크롤 시작")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        no_change_count = 0

        while scroll_count < max_scrolls:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(Config.SCROLL_PAUSE)

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
                            logger.debug("[원티드] 더보기 버튼 클릭")
                            break
            except Exception as e:
                logger.debug(f"[원티드] 더보기 버튼 처리 중 에러: {e}")

            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:
                    logger.info("[원티드] 스크롤 끝 도달")
                    break
            else:
                no_change_count = 0

            last_height = new_height
            scroll_count += 1
            
            if scroll_count % 5 == 0:
                logger.debug(f"[원티드] 스크롤 진행 중: {scroll_count}회")

        logger.info(f"[원티드] 스크롤 완료: 총 {scroll_count}회")

    def _parse_search_results(self) -> List[JobPosting]:
        """검색 결과 파싱"""
        jobs = []

        card_selectors = [
            "[class*='JobCard']", 
            "[class*='job-card']",
            "a[href*='/wd/']", 
            ".position-card",
            "[data-cy='job-card']",
            "[class*='Card']"
        ]

        items = []
        for sel in card_selectors:
            items = self.driver.find_elements(By.CSS_SELECTOR, sel)
            if items:
                logger.info(f"[원티드] 셀렉터 '{sel}'로 {len(items)}개 발견")
                break

        if not items:
            logger.warning("[원티드] 공고 카드를 찾지 못했습니다")
            return []

        for idx, item in enumerate(items):
            try:
                job = self._parse_card(item)
                if job:
                    if not job.is_expired():
                        jobs.append(job)
                        if len(jobs) % 100 == 0:
                            logger.debug(f"[원티드] 파싱 진행 중: {len(jobs)}개")
                else:
                    logger.debug(f"[원티드] {idx}번째 카드 파싱 실패")
            except Exception as e:
                logger.debug(f"[원티드] {idx}번째 카드 파싱 에러: {e}")
                continue

        logger.info(f"[원티드] 파싱 완료: {len(jobs)}개")
        return jobs

    def _parse_listing_results(self) -> List[JobPosting]:
        """목록 결과 파싱"""
        return self._parse_search_results()

    def _parse_card(self, item) -> JobPosting:
        """개별 카드 파싱"""
        try:
            url = self._extract_url(item)
            full_text = item.text.strip()
            
            if not full_text:
                return None
            
            # 🔥 광고 제거 (여기에 넣기)
            AD_KEYWORDS = ["합격보상금", "채용보상금", "추천보상금", "리워드"]
            if any(k in full_text for k in AD_KEYWORDS):
                logger.debug("[원티드] 광고 카드 제거")
                return None
            
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            
            if len(lines) < 2:
                return None
            
            title = lines[0] if len(lines) > 0 else ""
            company = lines[1] if len(lines) > 1 else ""
            location_raw = lines[2] if len(lines) > 2 else ""
            
            location = ""
            experience = ""
            
            if location_raw:
                # "서울 서초구 · 신입-경력 3년" 형태 파싱
                if "·" in location_raw:
                    parts = location_raw.split("·")
                    location = parts[0].strip()
                    experience = parts[1].strip() if len(parts) > 1 else ""
                elif "•" in location_raw:
                    parts = location_raw.split("•")
                    location = parts[0].strip()
                    experience = parts[1].strip() if len(parts) > 1 else ""
                else:
                    location = location_raw.strip()
            
            if not title or len(title) < 2:
                return None
            
            # 회사명 재시도
            if not company or len(company) < 2:
                company_selectors = [
                    "[class*='company']",
                    "[class*='Company']",
                    ".company-name"
                ]
                for sel in company_selectors:
                    company = self.safe_get_text(item, sel)
                    if company and len(company) > 1:
                        break
            
            # 지역 재시도
            if not location:
                location_selectors = [
                    "[class*='location']",
                    "[class*='Location']"
                ]
                for sel in location_selectors:
                    location = self.safe_get_text(item, sel)
                    if location:
                        break
            
            # 기술스택 추출
            tech_stack = []
            full_text_lower = full_text.lower()
            for tech in Config.TECH_STACKS:
                if tech.lower() in full_text_lower:
                    tech_stack.append(tech)
            
            logger.info(
                f"[원티드 파싱] 제목='{title}' | "
                f"회사='{company}' | "
                f"지역='{location}' | "
                f"경력='{experience}'"
            )
            
            # experience를 JobPosting에 직접 전달
            return JobPosting(
                title=title,
                company=company or "회사명 미제공",
                url=url,
                source="wanted",
                location=location or "위치 미제공",
                experience=experience,  # ← 여기 추가!
                tech_stack=tech_stack,
                deadline="상시채용"
            )
            
        except Exception as e:
            logger.debug(f"[원티드] 카드 파싱 중 예외: {e}")
            return None
    def _extract_url(self, item) -> str:
        """URL 추출"""
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
        
        return url