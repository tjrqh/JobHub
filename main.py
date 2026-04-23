#!/usr/bin/env python3
"""
취업 공고 자동 수집 프로그램
- 사람인, 잡코리아, 원티드 크롤링
- GUI로 조건 검색 + 카드 형식 표시
- 일일 자동 이메일 발송
"""

import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.helpers import setup_logging


def main():
    """메인 실행"""
    # 로깅 설정
    setup_logging()

    # GUI 실행
    from gui.app import App
    app = App()
    app.mainloop()


def cli_mode():
    """CLI 모드로 즉시 크롤링 + 이메일 발송"""
    setup_logging()

    import argparse
    parser = argparse.ArgumentParser(description="취업 공고 수집기")
    parser.add_argument("-k", "--keyword", default="", help="검색 키워드")
    parser.add_argument("-e", "--experience", default="전체", help="경력")
    parser.add_argument("-r", "--region", default="전체", help="지역")
    parser.add_argument("--mail", action="store_true", help="이메일 발송")
    parser.add_argument("--schedule", action="store_true", help="일일 스케줄 모드")
    args = parser.parse_args()

    from scheduler.daily_scheduler import DailyScheduler

    params = {
        "keyword": args.keyword,
        "experience": args.experience,
        "region": args.region,
    }

    scheduler = DailyScheduler(search_params=params)

    if args.schedule:
        print(f"스케줄 모드 시작 (매일 {scheduler.search_params})")
        scheduler.start()
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()
            print("종료")
    else:
        scheduler.daily_job()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-k", "--keyword", "--mail", "--schedule", "-e", "-r"):
        cli_mode()
    else:
        main()