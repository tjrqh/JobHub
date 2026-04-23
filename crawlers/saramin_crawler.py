import time
import logging
from typing import List
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from crawlers.base_crawler import BaseCrawler
from models.job import JobPosting
from config import Config

logger = logging.getLogger(__name__)


class SaraminCrawler(BaseCrawler):
    """사람인 크롤러"""

    BASE_URL = "https://www.saramin.co.kr"

    def __init__(self):
        super().__init__()
        self.source_name = "saramin"

    def build_search_url(self, keyword: str = "", **filters) -> str:
        params = []

        if keyword:
            params.append(f"searchword={quote_plus(keyword)}")
            params.append("searchType=search")

        # ✅ 직무
        category = filters.get("category")
        category_map = {
            "전체": "2",
            "웹개발": "87",
            "SW개발": "2",
            "앱개발": "86",
            "데이터분석": "82",
            "AI/ML": "109,181",
            "서버/백엔드": "84",
            "프론트엔드": "92",
            "DevOps": "146",
            "QA/테스트": "99",
            "보안": "90",
            "DBA": "95",
            "네트워크": "104"
        }
        if category in category_map:
            if category in ["SW개발", "전체"]:
                params.append(f"cat_mcls={category_map[category]}")
            else:
                params.append(f"cat_kewd={category_map[category]}")

        # 경력
        exp = filters.get("experience", "전체")
        exp_map = {
            "신입": "1",
            "1년": "1",
            "2년": "2",
            "3년": "3",
            "5년": "5",
            "7년": "7",
            "10년 이상": "10"
        }

        if exp in exp_map:
            code = exp_map[exp]
            if exp == "신입":
                params.append(f"exp_cd={code}")
            else:
                params.append(f"exp_cd={1}")
                params.append(f"exp_min={1}")
                params.append(f"exp_max={code}")

        # 학력
        edu = filters.get("education", "전체")

        edu_map = {
            "학력무관": "y",
            "고졸": "9",
            "초대졸": "10",
            "대졸": "11",
            "석사": "12",
            "박사": "6"
        }

        if edu in edu_map:
            code = edu_map[edu]

            if edu == "박사":
                params.append(f"edu_min={code}")   # ✅ 박사만 min
            elif edu == "학력무관":
                params.append(f"edu_none={code}")       # 학력무관
            else:
                params.append(f"edu_max={code}")   # ✅ 나머지는 max
        # 지역
        location = filters.get("location", "전체")
        location_map = {
            "서울": "101000", "경기": "102000", "인천": "108000",
            "부산": "106000", "대구": "104000", "광주": "103000",
            "대전": "105000", "울산": "107000", "세종": "118000",
            "강원": "109000", "충북": "110000", "충남": "111000",
            "전북": "112000", "전남": "113000", "경북": "114000",
            "경남": "115000", "제주": "116000"
        }
        if location in location_map:
            params.append(f"loc_mcd={location_map[location]}")

        param_str = "&".join(params)
        return f"{self.BASE_URL}/zf_user/search/recruit?{param_str}"

    def crawl(self, keyword: str = "", **filters) -> List[JobPosting]:
        """사람인 크롤링"""
        url = self.build_search_url(keyword, **filters)
        jobs = []

        for page in range(1, Config.MAX_PAGES + 1):
            page_url = f"{url}&recruitPage={page}"
            logger.info(f"[사람인] 페이지 {page} 크롤링: {page_url}")

            try:
                self.driver.get(page_url)
                time.sleep(2)

                # 채용공고 목록 대기
                items = self.wait_for_elements(
                    By.CSS_SELECTOR, ".item_recruit", timeout=10
                )

                if not items:
                    logger.info(f"[사람인] 페이지 {page}: 결과 없음, 종료")
                    break

                for item in items:
                    try:
                        job = self._parse_item(item)
                        if job and not job.is_expired():
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"[사람인] 아이템 파싱 에러: {e}")
                        continue

            except Exception as e:
                logger.error(f"[사람인] 페이지 {page} 에러: {e}")
                break

        return jobs

    def _parse_item(self, item) -> JobPosting:
        """개별 공고 파싱"""
        # 제목, URL
        title = self.safe_get_text(item, "h2.job_tit a, .job_tit a")
        url = self.safe_get_attribute(item, "h2.job_tit a, .job_tit a", "href")

        if not title:
            return None

        if url and not url.startswith("http"):
            url = self.BASE_URL + url

        # 회사명
        company = self.safe_get_text(
            item, ".corp_name a, .area_corp .corp_name a"
        )

        # 조건 정보
        conditions = self.safe_get_text(item, ".job_condition")
        cond_parts = [c.strip() for c in conditions.split("|")] if conditions else []

        location = cond_parts[0] if len(cond_parts) > 0 else ""
        experience = cond_parts[1] if len(cond_parts) > 1 else ""
        education = cond_parts[2] if len(cond_parts) > 2 else ""
        job_type = cond_parts[3] if len(cond_parts) > 3 else ""

        # 마감일
        deadline = self.safe_get_text(item, ".job_date .date")

        # 기술 스택 (직무 분야에서 추출)
        sector = self.safe_get_text(item, ".job_sector")
        tech_stack = []
        if sector:
            known_stacks = Config.TECH_STACKS
            for tech in known_stacks:
                if tech.lower() in sector.lower():
                    tech_stack.append(tech)

        # 연봉
        salary = self.safe_get_text(item, ".area_job .job_salary")

        return JobPosting(
            title=title,
            company=company,
            url=url,
            source="saramin",
            location=location,
            experience=experience,
            education=education,
            salary=salary,
            tech_stack=tech_stack,
            job_type=job_type,
            deadline=deadline,
            description=sector
        )