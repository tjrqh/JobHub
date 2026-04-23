# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # 이메일 설정
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_app_password")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "receiver@gmail.com")

    # 크롤링 설정
    CHROME_HEADLESS = True
    PAGE_LOAD_TIMEOUT = 15
    MAX_PAGES = 5
    SCROLL_PAUSE = 2

    # 스케줄러 설정
    DAILY_SEND_TIME = "09:00"

    # 검색 옵션
    JOB_CATEGORIES = [
        "전체", "SW개발", "웹개발", "앱개발", "데이터분석",
        "AI/ML", "서버/백엔드", "프론트엔드", "DevOps",
        "QA/테스트", "보안", "DBA", "네트워크"
    ]

    EXPERIENCE_LEVELS = [
        "전체", "신입", "1년", "2년", "3년",
        "5년", "7년", "10년 이상"
    ]

    EDUCATION_LEVELS = [
        "전체", "학력무관", "고졸", "초대졸",
        "대졸", "석사", "박사"
    ]

    TECH_STACKS = [
        "전체","Python", "Java", "JavaScript", "TypeScript",
        "React", "Vue.js", "Angular", "Node.js",
        "Spring", "Django", "Flask", "FastAPI",
        "AWS", "Docker", "Kubernetes", "Git",
        "MySQL", "PostgreSQL", "MongoDB", "Redis",
        "C++", "C#", "Go", "Rust", "Kotlin",
        "Swift", "Flutter", "React Native",
        "TensorFlow", "PyTorch", "Hadoop", "Spark",
        "Linux", "Jenkins", "Terraform", "GraphQL"
    ]

    LOCATIONS = [
        "전체", "서울", "경기", "인천", "부산",
        "대구", "광주", "대전", "울산", "세종",
        "강원", "충북", "충남", "전북", "전남",
        "경북", "경남", "제주"
    ]

    # ===== 헬퍼 메서드 =====
    @staticmethod
    def get_options(option_list: list, selected: str) -> list:
        """'전체' 선택 시 나머지 모든 옵션 반환"""
        if selected == "전체" or selected is None:
            return [opt for opt in option_list if opt != "전체"]
        return [selected]

    @classmethod
    def get_experience_options(cls, selected: str = "전체") -> list:
        return cls.get_options(cls.EXPERIENCE_LEVELS, selected)

    @classmethod
    def get_location_options(cls, selected: str = "전체") -> list:
        return cls.get_options(cls.LOCATIONS, selected)
    
    @classmethod
    def get_tech_stack_options(cls, selected: str = "전체") -> list:
        return cls.get_options(cls.TECH_STACKS, selected)

    @classmethod
    def get_category_options(cls, selected: str = "전체") -> list:
        return cls.get_options(cls.JOB_CATEGORIES, selected)