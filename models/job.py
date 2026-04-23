from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class JobPosting:
    """채용 공고 데이터 모델"""
    title: str
    company: str
    url: str
    source: str  # saramin, jobkorea, wanted

    location: str = ""
    experience: str = ""
    education: str = ""
    salary: str = ""
    tech_stack: List[str] = field(default_factory=list)
    job_type: str = ""  # 정규직, 계약직 등
    deadline: str = ""
    posted_date: str = ""
    description: str = ""

    crawled_at: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """마감일이 지났는지 확인"""
        if not self.deadline:
            return False

        now = datetime.now()

        # "상시채용", "채용시 마감" 등은 만료되지 않음
        skip_keywords = ["상시", "채용시", "수시", "마감시", "상시채용"]
        for kw in skip_keywords:
            if kw in self.deadline:
                return False

        # 날짜 파싱 시도
        date_formats = [
            "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d",
            "%m/%d", "%m.%d", "~%m.%d",
            "~%Y.%m.%d", "~ %Y.%m.%d", "~ %m.%d"
        ]

        deadline_str = self.deadline.replace("~", "").replace("까지", "").strip()

        for fmt in date_formats:
            try:
                deadline_date = datetime.strptime(deadline_str, fmt)
                # 연도가 없는 경우 올해로 설정
                if deadline_date.year == 1900:
                    deadline_date = deadline_date.replace(year=now.year)
                    if deadline_date < now:
                        deadline_date = deadline_date.replace(year=now.year + 1)
                return deadline_date < now
            except ValueError:
                continue

        return False

    def matches_filter(
        self,
        keyword: str = "",
        category: str = "전체",
        experience: str = "전체",
        education: str = "전체",
        tech_stacks: List[str] = None,
        region: str = "전체"
    ) -> bool:
        """필터 조건에 맞는지 확인"""
        # 만료 체크
        if self.is_expired():
            return False

        # 키워드 검색
        if keyword:
            keyword_lower = keyword.lower()
            searchable = f"{self.title} {self.company} {self.description}".lower()
            if keyword_lower not in searchable:
                return False

        # 직종 필터
        if category and category != "전체":
            category_lower = category.lower()
            searchable = f"{self.title} {self.description} {self.job_type}".lower()
            if category_lower not in searchable:
                return False

        # 경력 필터
        if experience and experience != "전체":
            if experience == "신입":
                if "신입" not in self.experience and "경력무관" not in self.experience:
                    return False

        # 학력 필터
        if education and education != "전체":
            if education != "학력무관" and education not in self.education:
                if "학력무관" not in self.education:
                    return False

        # 기술스택 필터
        if tech_stacks:
            job_stacks = " ".join(self.tech_stack).lower()
            job_searchable = f"{self.title} {self.description}".lower()
            combined = f"{job_stacks} {job_searchable}"
            if not any(ts.lower() in combined for ts in tech_stacks):
                return False

        # 지역 필터
        if region and region != "전체":
            if region not in self.location:
                return False

        return True

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "source": self.source,
            "location": self.location,
            "experience": self.experience,
            "education": self.education,
            "salary": self.salary,
            "tech_stack": self.tech_stack,
            "job_type": self.job_type,
            "deadline": self.deadline,
            "posted_date": self.posted_date,
            "description": self.description,
            "crawled_at": self.crawled_at.isoformat()
        }

    def to_html_card(self) -> str:
        """이메일용 HTML 카드"""
        source_colors = {
            "saramin": "#0D47A1",
            "jobkorea": "#00897B",
            "wanted": "#3F51B5"
        }
        source_names = {
            "saramin": "사람인",
            "jobkorea": "잡코리아",
            "wanted": "원티드"
        }
        color = source_colors.get(self.source, "#333")
        source_name = source_names.get(self.source, self.source)
        stacks = ", ".join(self.tech_stack[:5]) if self.tech_stack else "-"

        return f"""
        <div style="border:1px solid #ddd;border-radius:12px;padding:20px;
                    margin:10px 0;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="background:{color};color:#fff;padding:4px 10px;
                            border-radius:6px;font-size:12px;">{source_name}</span>
                <span style="color:#999;font-size:12px;">마감: {self.deadline or '미정'}</span>
            </div>
            <h3 style="margin:12px 0 6px;color:#222;">{self.title}</h3>
            <p style="margin:4px 0;color:#555;font-size:14px;font-weight:bold;">
                🏢 {self.company}
            </p>
            <p style="margin:4px 0;color:#777;font-size:13px;">
                📍 {self.location or '-'} | 💼 {self.experience or '-'} |
                🎓 {self.education or '-'}
            </p>
            <p style="margin:4px 0;color:#777;font-size:13px;">
                🔧 {stacks}
            </p>
            <a href="{self.url}" style="display:inline-block;margin-top:10px;
                    background:{color};color:#fff;padding:8px 20px;border-radius:6px;
                    text-decoration:none;font-size:13px;">공고 보기 →</a>
        </div>
        """