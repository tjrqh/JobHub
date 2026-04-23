import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import datetime

from config import Config
from models.job import JobPosting

logger = logging.getLogger(__name__)


class MailService:
    """이메일 발송 서비스"""

    @staticmethod
    def send_jobs_email(
        jobs: List[JobPosting],
        receiver: str = None,
        subject: str = None
    ) -> bool:
        """채용 공고를 이메일로 발송"""
        if not jobs:
            logger.warning("발송할 공고가 없습니다.")
            return False

        receiver = receiver or Config.EMAIL_RECEIVER
        today = datetime.now().strftime("%Y-%m-%d")
        subject = subject or f"📋 오늘의 채용 공고 ({today}) - {len(jobs)}건"

        html = MailService._build_email_html(jobs, today)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = Config.EMAIL_SENDER
            msg["To"] = receiver

            msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
                server.sendmail(Config.EMAIL_SENDER, receiver, msg.as_string())

            logger.info(f"이메일 발송 성공: {receiver} ({len(jobs)}건)")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("이메일 인증 실패. 앱 비밀번호를 확인하세요.")
            return False
        except Exception as e:
            logger.error(f"이메일 발송 실패: {e}")
            return False

    @staticmethod
    def _build_email_html(jobs: List[JobPosting], date: str) -> str:
        """이메일 HTML 생성"""
        # 소스별 분류
        saramin_jobs = [j for j in jobs if j.source == "saramin"]
        jobkorea_jobs = [j for j in jobs if j.source == "jobkorea"]
        wanted_jobs = [j for j in jobs if j.source == "wanted"]

        cards_html = ""

        sections = [
            ("🔵 사람인", saramin_jobs),
            ("🟢 잡코리아", jobkorea_jobs),
            ("🟣 원티드", wanted_jobs)
        ]

        for section_title, section_jobs in sections:
            if section_jobs:
                cards_html += f"""
                <h2 style="color:#333;border-bottom:2px solid #ddd;
                           padding-bottom:8px;margin-top:30px;">
                    {section_title} ({len(section_jobs)}건)
                </h2>
                """
                for job in section_jobs:
                    cards_html += job.to_html_card()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
                     background:#f5f5f5;margin:0;padding:20px;">
            <div style="max-width:700px;margin:0 auto;background:#fff;
                        border-radius:16px;padding:30px;
                        box-shadow:0 4px 16px rgba(0,0,0,0.1);">

                <div style="text-align:center;margin-bottom:30px;">
                    <h1 style="color:#1a237e;margin:0;">📋 오늘의 채용 공고</h1>
                    <p style="color:#999;margin:8px 0;">{date} | 총 {len(jobs)}건</p>
                    <div style="display:inline-block;background:#e8eaf6;
                                padding:8px 16px;border-radius:8px;margin:4px;">
                        사람인 {len(saramin_jobs)}건 |
                        잡코리아 {len(jobkorea_jobs)}건 |
                        원티드 {len(wanted_jobs)}건
                    </div>
                </div>

                {cards_html}

                <div style="text-align:center;margin-top:40px;padding-top:20px;
                            border-top:1px solid #eee;">
                    <p style="color:#aaa;font-size:12px;">
                        이 메일은 취업 공고 자동 수집 프로그램에 의해 발송되었습니다.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return html