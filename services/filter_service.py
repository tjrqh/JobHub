import logging
from typing import List
from models.job import JobPosting

logger = logging.getLogger(__name__)


class FilterService:

    @staticmethod
    def filter_jobs(
        jobs: List[JobPosting],
        keyword: str = "",
        category: str = "전체",
        experience: str = "전체",
        education: str = "전체",
        tech_stacks: List[str] = None,
        location: str = "전체"
    ) -> List[JobPosting]:

        filtered = []
        logger.info(f"필터링 프로세스 시작: 총 {len(jobs)}개 대상")
        logger.info(f"설정된 필터 - 키워드: '{keyword}', 경력: '{experience}', 지역: '{location}'")

        # 🔥 처음 5개만 상세 정보 출력 (INFO 레벨이라 항상 보임)
        for idx, job in enumerate(jobs):
            try:
                is_match = job.matches_filter(
                    keyword=keyword,
                    category=category,
                    experience=experience,
                    education=education,
                    tech_stacks=tech_stacks,
                    location=location
                )

                if is_match:
                    filtered.append(job)

            except Exception as e:
                logger.error(f"[필터오류] {idx}번째 공고 처리 중 에러: {e}")
                continue

        after_filter_count = len(filtered)

        seen = set()
        unique = []
        for job in filtered:
            clean_company = job.company.replace("(주)", "").strip()
            clean_title = job.title.strip()
            key = f"{clean_company}_{clean_title}".lower().replace(" ", "")
            if key not in seen:
                seen.add(key)
                unique.append(job)

        # 🔥 요약은 항상 INFO로
        logger.info(
            f"필터링 요약: 원본({len(jobs)}) -> "
            f"필터통과({after_filter_count}) -> "
            f"중복제거최종({len(unique)})"
        )

        if len(unique) == 0 and len(jobs) > 0:
            logger.error("!!! 모든 공고가 필터링에서 탈락했습니다. !!!")

        return unique

    @staticmethod
    def remove_expired(jobs: List[JobPosting]) -> List[JobPosting]:
        active = [j for j in jobs if not j.is_expired()]
        removed_count = len(jobs) - len(active)
        if removed_count > 0:
            logger.info(f"만료된 공고 {removed_count}개 제거 완료")
        return active

    @staticmethod
    def sort_jobs(jobs: List[JobPosting], sort_by: str = "latest") -> List[JobPosting]:
        if sort_by == "company":
            return sorted(jobs, key=lambda j: j.company)
        elif sort_by == "source":
            return sorted(jobs, key=lambda j: j.source)
        else:
            return sorted(jobs, key=lambda j: j.crawled_at, reverse=True)