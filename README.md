# 💼 취업 공고 자동 수집기

<div align="center">

**사람인 · 잡코리아 · 원티드 채용 공고 자동 수집 데스크탑 애플리케이션**

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
![Chrome](https://img.shields.io/badge/Chrome-Driver-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)
![tkinter](https://img.shields.io/badge/GUI-tkinter-FF6F00?style=for-the-badge&logo=python&logoColor=white)

</div>

---

## 📖 목차

- [주요 기능](#-주요-기능)
- [프로젝트 구조](#-프로젝트-구조)
- [설치 방법](#-설치-방법)
- [실행 방법](#-실행-방법)
- [사용 방법](#-사용-방법)
- [설정](#-설정)
- [수집 현황](#-수집-현황)
- [로그](#-로그)
- [트러블슈팅](#-트러블슈팅)
- [주의사항](#-주의사항)

---

## ✨ 주요 기능

<table>
  <tr>
    <td>🔍 <b>멀티 사이트 크롤링</b></td>
    <td>사람인, 잡코리아, 원티드 동시 수집</td>
  </tr>
  <tr>
    <td>🎯 <b>다양한 필터링</b></td>
    <td>키워드, 직종, 경력, 학력, 지역, 기술스택</td>
  </tr>
  <tr>
    <td>🔄 <b>중복 제거</b></td>
    <td>회사명 + 공고 제목 기준 자동 중복 제거</td>
  </tr>
  <tr>
    <td>📧 <b>이메일 자동 발송</b></td>
    <td>수집된 공고를 HTML 형식으로 이메일 발송</td>
  </tr>
  <tr>
    <td>⏰ <b>자동 스케줄링</b></td>
    <td>매일 지정한 시간에 자동 수집 및 발송</td>
  </tr>
  <tr>
    <td>🖥️ <b>GUI 인터페이스</b></td>
    <td>tkinter 기반 데스크탑 UI</td>
  </tr>
</table>

---

## 🗂️ 프로젝트 구조
💼 pyc/
├── 📄 main.py # 진입점
├── 📄 config.py # 설정 파일
├── 📄 .env # 환경변수 (이메일 등)
├── 📄 requirements.txt # 패키지 목록
├── 📄 crawler.log # 실행 로그 (자동 생성)
│
├── 📁 crawlers/ # 크롤러 모듈
│ ├── init.py
│ ├── base_crawler.py # 크롤러 베이스 클래스
│ ├── saramin_crawler.py # 사람인 크롤러
│ ├── jobkorea_crawler.py # 잡코리아 크롤러
│ └── wanted_crawler.py # 원티드 크롤러 (무한 스크롤)
│
├── 📁 models/ # 데이터 모델
│ └── job.py # JobPosting 데이터 클래스
│
├── 📁 services/ # 비즈니스 로직
│ ├── filter_service.py # 필터링 서비스
│ └── mail_service.py # 이메일 발송 서비스
│
├── 📁 scheduler/ # 스케줄러
│ └── daily_scheduler.py # 일일 자동 수집 스케줄러
│
├── 📁 gui/ # GUI
│ └── app.py # tkinter 메인 앱
│
└── 📁 utils/ # 유틸리티
└── helpers.py # 헬퍼 함수

text


---

## ⚙️ 설치 방법

### 요구사항

- Python `3.12` 이상
- Google Chrome 브라우저

### Step 1. 저장소 클론

```bash
git clone https://github.com/your-repo/job-crawler.git
cd job-crawler
Step 2. 가상환경 생성
Bash

python -m venv venv
Bash

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
Step 3. 패키지 설치
Bash

pip install -r requirements.txt
txt

# requirements.txt
selenium
webdriver-manager
python-dotenv
schedule
Step 4. 환경변수 설정
프로젝트 루트에 .env 파일 생성:

env

# .env

# 발신자 이메일
MAIL_SENDER=your_email@gmail.com

# Gmail 앱 비밀번호 (계정 비밀번호 X)
MAIL_PASSWORD=your_app_password

# 수신자 이메일
MAIL_RECEIVER=receiver@gmail.com

# SMTP 설정
MAIL_SMTP=smtp.gmail.com
MAIL_PORT=587
[!IMPORTANT]
Gmail 사용 시 앱 비밀번호를 사용해야 합니다.
일반 계정 비밀번호로는 발송이 되지 않습니다.
👉 Google 앱 비밀번호 설정

🚀 실행 방법
Bash

python main.py
[!NOTE]
실행 시 Chrome 브라우저가 자동으로 열리며 크롤링이 시작됩니다.
ChromeDriver는 webdriver-manager가 자동으로 설치합니다.

🖥️ 사용 방법
1️⃣ 기본 검색
키워드 입력 (예: Python, 백엔드, 신입)
수집할 사이트 체크 (사람인 / 잡코리아 / 원티드)
🔍 검색 버튼 클릭 또는 Enter
2️⃣ 필터 설정
필터	설명	예시
직종	모집 직종 필터	개발, 디자인, 기획
경력	경력 조건 필터	신입, 1년, 3년, 5년
학력	학력 조건 필터	학력무관, 대졸, 석사
지역	근무 지역 필터	서울, 경기, 부산
기술스택	사용 기술 필터	Python, Java, React
3️⃣ 결과 정렬
정렬	기준
최신순	수집 시간 기준 (기본값)
회사명순	가나다 순
사이트순	수집 사이트 기준
4️⃣ 이메일 발송
검색 완료 후 📧 메일 발송 클릭
.env에 설정된 수신자 이메일로 HTML 형식 발송
5️⃣ 자동 스케줄링
매일 자동 발송 체크박스 활성화
config.py의 DAILY_SEND_TIME에 설정된 시간에 자동 수집 및 발송
🔧 설정
config.py에서 주요 설정을 변경할 수 있습니다:

Python

# ⏱️ 크롤링 설정
MAX_PAGES = 5               # 최대 크롤링 페이지 수
SCROLL_PAUSE = 2            # 무한 스크롤 대기 시간 (초)

# ⏰ 스케줄러 설정
DAILY_SEND_TIME = "09:00"   # 자동 발송 시간

# 🛠️ 기술스택 목록
TECH_STACKS = [
    "Python", "Java", "React", "Node.js",
    "Spring", "Django", "Vue", "Kotlin", ...
]

# 📍 지역 목록
LOCATIONS = ["전체", "서울", "경기", "부산", "대구", ...]

# 💼 경력 레벨
EXPERIENCE_LEVELS = ["전체", "신입", "1년", "3년", "5년", "10년 이상"]

# 🎓 학력 레벨
EDUCATION_LEVELS = ["전체", "학력무관", "고졸", "대졸", "석사", "박사"]
📊 수집 현황
사이트	수집 방식	평균 수집량
사람인	Selenium 페이지네이션	~500개
잡코리아	Selenium 페이지네이션	~500개
원티드	Selenium 무한 스크롤	~700개
합계		~1,700개
📝 로그
실행 시 콘솔 및 crawler.log 파일에 로그가 저장됩니다:

log

2026-04-24 01:54:28 [INFO] crawlers.saramin_crawler: [사람인] 총 512개 수집 완료
2026-04-24 01:54:29 [INFO] crawlers.jobkorea_crawler: [잡코리아] 총 487개 수집 완료
2026-04-24 01:54:30 [INFO] crawlers.wanted_crawler: [원티드] 총 728개 수집 완료
2026-04-24 01:54:30 [INFO] services.filter_service: 필터링 요약: 원본(1727) -> 필터통과(150) -> 중복제거최종(143)
로그 레벨
레벨	출력 대상
INFO	크롤링 결과, 필터링 요약, 수집 건수
WARNING	파싱 실패, 크롤러 경고
ERROR	필터링 전체 실패, 이메일 발송 실패
억제	selenium, urllib3 내부 디버그 로그
🛠️ 트러블슈팅
<details> <summary><b>Chrome 드라이버 오류</b></summary>
Bash

# webdriver-manager가 자동으로 드라이버를 다운로드 및 설치합니다
pip install webdriver-manager
</details><details> <summary><b>이메일 발송 실패</b></summary>
Gmail 앱 비밀번호 사용 확인 (일반 비밀번호 X)
.env 파일 설정 확인
방화벽 / 보안 프로그램 확인
앱 비밀번호 발급
</details><details> <summary><b>공고가 0개로 필터링됨</b></summary>
필터 조건 완화 (지역: 전체, 경력: 전체)
키워드 단순화 (예: 백엔드 개발자 → 백엔드)
crawler.log 파일에서 탈락 원인 확인
</details><details> <summary><b>크롤링 속도가 느림</b></summary>
config.py의 SCROLL_PAUSE 값 줄이기
MAX_PAGES 값 줄이기
수집 사이트 수 줄이기 (체크박스 해제)
</details>
⚠️ 주의사항
[!WARNING]

크롤링 시 Chrome 브라우저가 자동 실행됩니다
사이트 정책에 따라 크롤링이 일시적으로 차단될 수 있습니다
과도한 크롤링은 IP 차단의 원인이 될 수 있습니다
수집된 데이터는 개인적인 용도로만 사용하세요
수집된 데이터의 저작권은 각 사이트에 있습니다
📄 License
This project is for personal use only.
수집된 데이터의 저작권은 각 사이트에 있습니다.