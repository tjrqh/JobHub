import time
import logging
import threading
import schedule
from datetime import datetime
from typing import List, Callable

from config import Config
from crawlers import SaraminCrawler, JobKoreaCrawler, WantedCrawler
from services.filter_service import FilterService
from services.mail_service import MailService
from models.job import JobPosting

logger = logging.getLogger(__name__)


class DailyScheduler:
    """일일 크롤링 + 메일 발송 스케줄러"""

    def __init__(self, search_params: dict = None, callback: Callable = None):
        self.search_params = search_params or {}
        self.callback = callback  # GUI 콜백
        self.is_running = False
        self._thread = None

    def daily_job(self):
        """일일 크롤링 + 이메일 발송"""
        logger.info(f"=== 일일 크롤링 시작 ({datetime.now()}) ===")

        all_jobs: List[JobPosting] = []
        keyword = self.search_params.get("keyword", "")

        # 각 사이트 크롤링
        crawlers = [
            ("사람인", SaraminCrawler()),
            ("잡코리아", JobKoreaCrawler()),
            ("원티드", WantedCrawler())
        ]

        for name, crawler in crawlers:
            try:
                logger.info(f"[{name}] 크롤링 시작")
                jobs = crawler.run(keyword, **self.search_params)
                all_jobs.extend(jobs)
                logger.info(f"[{name}] {len(jobs)}개 수집")
            except Exception as e:
                logger.error(f"[{name}] 크롤링 실패: {e}")

        # 필터링
        all_jobs = FilterService.remove_expired(all_jobs)
        all_jobs = FilterService.filter_jobs(
            all_jobs,
            keyword=keyword,
            category=self.search_params.get("category", "전체"),
            experience=self.search_params.get("experience", "전체"),
            education=self.search_params.get("education", "전체"),
            tech_stacks=self.search_params.get("tech_stacks", []),
            region=self.search_params.get("region", "전체")
        )

        # 이메일 발송
        if all_jobs:
            success = MailService.send_jobs_email(all_jobs)
            if success:
                logger.info(f"이메일 발송 성공: {len(all_jobs)}건")
            else:
                logger.error("이메일 발송 실패")
        else:
            logger.info("수집된 공고가 없어 이메일을 발송하지 않습니다.")

        # GUI 콜백
        if self.callback:
            self.callback(all_jobs)

        logger.info(f"=== 일일 크롤링 완료 ({len(all_jobs)}건) ===")

    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            return

        self.is_running = True

        # 매일 지정 시간에 실행
        schedule.every().day.at(Config.DAILY_SEND_TIME).do(self.daily_job)
        logger.info(f"스케줄러 시작 (매일 {Config.DAILY_SEND_TIME})")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        """스케줄 루프"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(30)

    def stop(self):
        """스케줄러 중지"""
        self.is_running = False
        schedule.clear()
        logger.info("스케줄러 중지")

    def run_now(self):
        """즉시 실행"""
        thread = threading.Thread(target=self.daily_job, daemon=True)
        thread.start()