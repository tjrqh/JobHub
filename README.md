# JobHub

구직 공고를 여러 채용 플랫폼에서 수집하고, 조건에 맞는 공고를 한 화면에서 확인할 수 있는 Python 데스크탑 애플리케이션입니다.

사람인, 잡코리아, 원티드의 채용 공고를 Selenium 기반 크롤러로 수집하고, 키워드/직종/경력/학력/지역/기술스택 기준으로 필터링합니다. 검색 결과는 tkinter GUI에서 카드 형태로 확인할 수 있으며, 필요한 경우 이메일로 발송할 수 있습니다.

## 주요 기능

- 사람인, 잡코리아, 원티드 채용 공고 수집
- 키워드, 직종, 경력, 학력, 지역, 기술스택 필터
- 회사명과 공고 제목 기준 중복 제거
- 검색 결과 카드 UI 제공
- 결과 정렬: 최신순, 회사명순, 사이트순
- 결과 목록 스크롤 및 추가 로딩
- HTML 이메일 발송
- 수집/필터링/발송 로그 기록

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Language | Python 3.11+ |
| Crawling | Selenium, webdriver-manager |
| GUI | tkinter, ttk |
| Email | smtplib, MIMEText |
| Scheduling | schedule |
| Config | python-dotenv |

## 프로젝트 구조

```text
JobHub/
├── main.py                      # 애플리케이션 진입점
├── config.py                    # 크롤링, 필터, 이메일 설정
├── requirements.txt             # pip 의존성
├── pyproject.toml               # 프로젝트 메타데이터
├── crawler.log                  # 실행 로그
├── crawlers/
│   ├── base_crawler.py          # Selenium 공통 크롤러
│   ├── saramin_crawler.py       # 사람인 크롤러
│   ├── jobkorea_crawler.py      # 잡코리아 크롤러
│   └── wanted_crawler.py        # 원티드 크롤러
├── gui/
│   └── app.py                   # tkinter GUI
├── models/
│   └── job.py                   # 채용 공고 데이터 모델
├── services/
│   ├── filter_service.py        # 필터링/중복 제거
│   └── mail_service.py          # 이메일 발송
├── scheduler/
│   └── daily_scheduler.py       # 일일 실행 스케줄러
└── utils/
    └── helpers.py               # 표시명/색상 등 유틸리티
```

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/tjrqh/JobHub.git
cd JobHub
```

### 2. 가상환경 생성 및 활성화

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows에서는 다음 명령을 사용합니다.

```bash
.venv\Scripts\activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECEIVER=receiver@gmail.com
```

Gmail을 사용하는 경우 일반 계정 비밀번호가 아니라 앱 비밀번호가 필요합니다.

## 실행

```bash
python main.py
```

실행하면 tkinter 기반 데스크탑 앱이 열립니다. ChromeDriver는 `webdriver-manager`가 로컬 Chrome 버전에 맞춰 자동으로 준비합니다.

## 사용 방법

1. 키워드를 입력합니다. 예: `Python`, `백엔드`, `신입`, `React`
2. 수집할 사이트를 선택합니다.
3. 직종, 경력, 학력, 지역, 기술스택 필터를 선택합니다.
4. `검색` 버튼을 누르거나 Enter를 입력합니다.
5. 결과 카드에서 공고 제목 또는 `공고 보기` 버튼을 눌러 원문 페이지로 이동합니다.
6. 필요하면 `메일 발송` 버튼으로 검색 결과를 이메일로 보냅니다.

## 크롤러 동작 방식

### 사람인

사람인 검색 페이지의 공고 목록을 페이지 단위로 순회하며 제목, 회사명, 지역, 경력, 학력, 마감일, 기술스택 정보를 수집합니다.

### 잡코리아

잡코리아의 최신 검색 화면 구조에 맞춰 `CardJob` 기반 공고 카드를 탐색합니다. 검색 URL에서 안정적으로 동작하는 조건만 적용하고, 지역/학력/기술스택 등은 수집 이후 내부 필터에서 처리합니다.

### 원티드

원티드는 무한 스크롤 방식의 목록을 처리합니다. 페이지 하단으로 스크롤하며 추가 공고를 로드한 뒤 카드 정보를 파싱합니다.

## 설정

주요 설정은 `config.py`에서 관리합니다.

```python
CHROME_HEADLESS = True
PAGE_LOAD_TIMEOUT = 15
MAX_PAGES = 5
SCROLL_PAUSE = 2
DAILY_SEND_TIME = "09:00"
```

필터 옵션도 `config.py`에서 확장할 수 있습니다.

- `JOB_CATEGORIES`
- `EXPERIENCE_LEVELS`
- `EDUCATION_LEVELS`
- `TECH_STACKS`
- `LOCATIONS`

## 로그

실행 로그는 콘솔과 `crawler.log`에 동시에 기록됩니다.

- 크롤링 시작/완료
- 사이트별 수집 건수
- 필터링 결과
- 파싱 실패
- 이메일 발송 성공/실패

## 트러블슈팅

### ChromeDriver 실행 오류

Chrome이 설치되어 있는지 확인하고, Chrome 버전이 정상적으로 감지되는지 확인합니다. macOS에서 처음 실행한 드라이버가 차단되는 경우 보안 설정에서 실행 허용이 필요할 수 있습니다.

### 검색 결과가 없는 경우

채용 사이트의 검색 URL, DOM 구조, 차단 정책이 바뀌었을 수 있습니다. 각 크롤러의 셀렉터와 URL 파라미터를 확인해야 합니다.

### 이메일 발송 실패

`.env`의 `EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECEIVER` 값을 확인합니다. Gmail은 앱 비밀번호를 사용해야 합니다.

## 개발 포인트

- 사이트별 DOM 구조가 달라 크롤러를 개별 클래스로 분리했습니다.
- 공통 Selenium 동작은 `BaseCrawler`에서 관리합니다.
- 수집 데이터는 `JobPosting` 모델로 표준화해 GUI, 필터링, 이메일 발송에서 같은 구조를 사용합니다.
- GUI와 크롤링 작업을 분리하기 위해 검색은 백그라운드 스레드에서 실행합니다.
- 채용 사이트 구조 변경에 대응할 수 있도록 다중 셀렉터와 안전한 파싱 로직을 사용합니다.

## 주의사항

이 프로젝트는 개인 학습 및 포트폴리오 목적의 프로젝트입니다. 수집한 데이터의 저작권은 각 채용 플랫폼과 원 게시자에게 있으며, 과도한 요청은 서비스 이용 제한 또는 차단의 원인이 될 수 있습니다.
