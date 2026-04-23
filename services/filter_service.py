import logging
from typing import List
from models.job import JobPosting

logger = logging.getLogger(__name__)


class FilterService:
    """채용 공고 필터링 서비스"""

    @staticmethod
    def filter_jobs(
        jobs: List[JobPosting],
        keyword: str = "",
        category: str = "전체",
        experience: str = "전체",
        education: str = "전체",
        tech_stacks: List[str] = None,
        region: str = "전체"
    ) -> List[JobPosting]:
        """조건에 맞는 공고만 필터링"""
        filtered = []

        for job in jobs:
            if job.matches_filter(
                keyword=keyword,
                category=category,
                experience=experience,
                education=education,
                tech_stacks=tech_stacks,
                region=region
            ):
                filtered.append(job)

        # 중복 제거 (회사명 + 제목 기준)
        seen = set()
        unique = []
        for job in filtered:
            key = f"{job.company}_{job.title}".lower().replace(" ", "")
            if key not in seen:
                seen.add(key)
                unique.append(job)

        logger.info(f"필터링 결과: {len(jobs)} → {len(unique)}개")
        return unique

    @staticmethod
    def remove_expired(jobs: List[JobPosting]) -> List[JobPosting]:
        """만료된 공고 제거"""
        active = [j for j in jobs if not j.is_expired()]
        removed = len(jobs) - len(active)
        if removed > 0:
            logger.info(f"만료 공고 {removed}개 제거")
        return active

    @staticmethod
    def sort_jobs(
        jobs: List[JobPosting],
        sort_by: str = "latest"
    ) -> List[JobPosting]:
        """공고 정렬"""
        if sort_by == "company":
            return sorted(jobs, key=lambda j: j.company)
        elif sort_by == "source":
            return sorted(jobs, key=lambda j: j.source)
        else:
            return sorted(jobs, key=lambda j: j.crawled_at, reverse=True)