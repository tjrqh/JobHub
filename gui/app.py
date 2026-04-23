import webbrowser
import threading
import logging
from datetime import datetime
from typing import List

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox  # pip install CTkMessagebox 필요 시

from config import Config
from models.job import JobPosting
from crawlers import SaraminCrawler, JobKoreaCrawler, WantedCrawler
from services.filter_service import FilterService
from services.mail_service import MailService
from scheduler.daily_scheduler import DailyScheduler
from utils.helpers import get_source_display_name, get_source_color, truncate_text

logger = logging.getLogger(__name__)

# 테마 설정
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class JobCard(ctk.CTkFrame):
    """채용공고 카드 위젯"""

    SOURCE_COLORS = {
        "saramin": ("#0D47A1", "#BBDEFB"),
        "jobkorea": ("#00897B", "#B2DFDB"),
        "wanted": ("#3F51B5", "#C5CAE9")
    }

    def __init__(self, master, job: JobPosting, **kwargs):
        super().__init__(master, **kwargs)
        self.job = job
        self.configure(
            corner_radius=12,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E0E0E0"
        )

        # 마우스 호버 효과
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self._build_card()

    def _build_card(self):
        """카드 UI 구성"""
        colors = self.SOURCE_COLORS.get(self.job.source, ("#333", "#EEE"))
        source_name = get_source_display_name(self.job.source)

        # 상단: 소스 + 마감일
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(12, 0))

        source_label = ctk.CTkLabel(
            top_frame,
            text=f" {source_name} ",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=colors[0],
            text_color="white",
            corner_radius=6,
            padx=8, pady=2
        )
        source_label.pack(side="left")

        deadline_text = f"마감: {self.job.deadline}" if self.job.deadline else ""
        deadline_label = ctk.CTkLabel(
            top_frame,
            text=deadline_text,
            font=ctk.CTkFont(size=11),
            text_color="#999999"
        )
        deadline_label.pack(side="right")

        # 제목
        title_label = ctk.CTkLabel(
            self,
            text=truncate_text(self.job.title, 60),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#212121",
            anchor="w",
            wraplength=450
        )
        title_label.pack(fill="x", padx=15, pady=(8, 2))

        # 회사명
        company_label = ctk.CTkLabel(
            self,
            text=f"🏢 {self.job.company}",
            font=ctk.CTkFont(size=13),
            text_color="#555555",
            anchor="w"
        )
        company_label.pack(fill="x", padx=15, pady=(0, 4))

        # 상세 정보
        info_parts = []
        if self.job.location:
            info_parts.append(f"📍 {self.job.location}")
        if self.job.experience:
            info_parts.append(f"💼 {self.job.experience}")
        if self.job.education:
            info_parts.append(f"🎓 {self.job.education}")

        if info_parts:
            info_label = ctk.CTkLabel(
                self,
                text="  |  ".join(info_parts),
                font=ctk.CTkFont(size=12),
                text_color="#777777",
                anchor="w"
            )
            info_label.pack(fill="x", padx=15, pady=(0, 2))

        # 기술 스택
        if self.job.tech_stack:
            stack_frame = ctk.CTkFrame(self, fg_color="transparent")
            stack_frame.pack(fill="x", padx=15, pady=(4, 4))

            for i, tech in enumerate(self.job.tech_stack[:6]):
                chip = ctk.CTkLabel(
                    stack_frame,
                    text=f" {tech} ",
                    font=ctk.CTkFont(size=10),
                    fg_color=colors[1],
                    text_color=colors[0],
                    corner_radius=4,
                    padx=4, pady=1
                )
                chip.pack(side="left", padx=2)

            if len(self.job.tech_stack) > 6:
                more = ctk.CTkLabel(
                    stack_frame,
                    text=f"+{len(self.job.tech_stack) - 6}",
                    font=ctk.CTkFont(size=10),
                    text_color="#999"
                )
                more.pack(side="left", padx=2)

        # 하단: 공고 보기 버튼
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(6, 12))

        view_btn = ctk.CTkButton(
            btn_frame,
            text="🔗 공고 보기",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors[0],
            hover_color=colors[1],
            text_color="white",
            corner_radius=8,
            width=120, height=32,
            command=lambda: webbrowser.open(self.job.url)
        )
        view_btn.pack(side="right")

        # 연봉 정보
        if self.job.salary:
            salary_label = ctk.CTkLabel(
                btn_frame,
                text=f"💰 {self.job.salary}",
                font=ctk.CTkFont(size=12),
                text_color="#4CAF50"
            )
            salary_label.pack(side="left")

        # 전체 클릭 이벤트
        for widget in [self, title_label, company_label]:
            widget.bind("<Button-1>", lambda e: webbrowser.open(self.job.url))
            widget.configure(cursor="hand2")

    def _on_enter(self, event):
        self.configure(border_color="#1976D2", fg_color="#FAFAFA")

    def _on_leave(self, event):
        self.configure(border_color="#E0E0E0", fg_color="#FFFFFF")


class App(ctk.CTk):
    """메인 애플리케이션"""

    def __init__(self):
        super().__init__()
        self.title("💼 취업 공고 자동 수집기")
        self.geometry("1100x800")
        self.minsize(900, 600)

        self.all_jobs: List[JobPosting] = []
        self.filtered_jobs: List[JobPosting] = []
        self.scheduler: DailyScheduler = None
        self.is_crawling = False

        self._build_ui()

    def _build_ui(self):
        """전체 UI 구성"""
        # 메인 컨테이너
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ===== 상단: 검색 패널 =====
        self._build_search_panel()

        # ===== 하단: 결과 영역 =====
        self._build_result_area()

        # ===== 상태바 =====
        self._build_status_bar()

    def _build_search_panel(self):
        """검색 조건 패널"""
        search_frame = ctk.CTkFrame(self, corner_radius=12)
        search_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        # ---- 첫 번째 줄: 키워드 + 검색 ----
        row1 = ctk.CTkFrame(search_frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            row1, text="🔍 키워드",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left", padx=(0, 8))

        self.keyword_entry = ctk.CTkEntry(
            row1, placeholder_text="검색어를 입력하세요 (예: Python 개발자)",
            width=350, height=36, font=ctk.CTkFont(size=13)
        )
        self.keyword_entry.pack(side="left", padx=(0, 10))
        self.keyword_entry.bind("<Return>", lambda e: self.start_crawling())

        self.search_btn = ctk.CTkButton(
            row1, text="🔍 검색 시작",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1976D2", hover_color="#1565C0",
            width=130, height=36,
            command=self.start_crawling
        )
        self.search_btn.pack(side="left", padx=5)

        # 사이트 선택 체크박스
        site_frame = ctk.CTkFrame(row1, fg_color="transparent")
        site_frame.pack(side="right")

        self.saramin_var = ctk.BooleanVar(value=True)
        self.jobkorea_var = ctk.BooleanVar(value=True)
        self.wanted_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            site_frame, text="사람인", variable=self.saramin_var,
            font=ctk.CTkFont(size=12), checkbox_width=18, checkbox_height=18
        ).pack(side="left", padx=4)
        ctk.CTkCheckBox(
            site_frame, text="잡코리아", variable=self.jobkorea_var,
            font=ctk.CTkFont(size=12), checkbox_width=18, checkbox_height=18
        ).pack(side="left", padx=4)
        ctk.CTkCheckBox(
            site_frame, text="원티드", variable=self.wanted_var,
            font=ctk.CTkFont(size=12), checkbox_width=18, checkbox_height=18
        ).pack(side="left", padx=4)

        # ---- 두 번째 줄: 필터 옵션 ----
        row2 = ctk.CTkFrame(search_frame, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=5)

        # 직종
        ctk.CTkLabel(row2, text="직종", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0, 4)
        )
        self.category_combo = ctk.CTkComboBox(
            row2, values=Config.JOB_CATEGORIES,
            width=130, height=32, font=ctk.CTkFont(size=12)
        )
        self.category_combo.set("전체")
        self.category_combo.pack(side="left", padx=(0, 12))

        # 경력
        ctk.CTkLabel(row2, text="경력", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0, 4)
        )
        self.exp_combo = ctk.CTkComboBox(
            row2, values=Config.EXPERIENCE_LEVELS,
            width=110, height=32, font=ctk.CTkFont(size=12)
        )
        self.exp_combo.set("전체")
        self.exp_combo.pack(side="left", padx=(0, 12))

        # 학력
        ctk.CTkLabel(row2, text="학력", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0, 4)
        )
        self.edu_combo = ctk.CTkComboBox(
            row2, values=Config.EDUCATION_LEVELS,
            width=110, height=32, font=ctk.CTkFont(size=12)
        )
        self.edu_combo.set("전체")
        self.edu_combo.pack(side="left", padx=(0, 12))

        # 지역
        ctk.CTkLabel(row2, text="지역", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0, 4)
        )
        self.region_combo = ctk.CTkComboBox(
            row2, values=Config.REGIONS,
            width=110, height=32, font=ctk.CTkFont(size=12)
        )
        self.region_combo.set("전체")
        self.region_combo.pack(side="left", padx=(0, 12))

        # ---- 세 번째 줄: 기술 스택 ----
        row3 = ctk.CTkFrame(search_frame, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=(5, 10))

        ctk.CTkLabel(
            row3, text="🔧 기술스택",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 8))

        # 기술 스택 체크박스 (스크롤 가능)
        self.tech_frame = ctk.CTkScrollableFrame(
            row3, height=35, orientation="horizontal",
            fg_color="transparent"
        )
        self.tech_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.tech_vars = {}
        for tech in Config.TECH_STACKS:
            var = ctk.BooleanVar(value=False)
            self.tech_vars[tech] = var
            cb = ctk.CTkCheckBox(
                self.tech_frame, text=tech, variable=var,
                font=ctk.CTkFont(size=11),
                checkbox_width=16, checkbox_height=16
            )
            cb.pack(side="left", padx=3)

        # ---- 네 번째 줄: 부가 기능 ----
        row4 = ctk.CTkFrame(search_frame, fg_color="transparent")
        row4.pack(fill="x", padx=15, pady=(0, 12))

        # 메일 발송 버튼
        self.mail_btn = ctk.CTkButton(
            row4, text="📧 결과 메일 발송",
            font=ctk.CTkFont(size=12),
            fg_color="#4CAF50", hover_color="#388E3C",
            width=140, height=32,
            command=self.send_email
        )
        self.mail_btn.pack(side="left", padx=5)

        # 일일 자동 발송 토글
        self.auto_var = ctk.BooleanVar(value=False)
        self.auto_switch = ctk.CTkSwitch(
            row4, text=f"매일 {Config.DAILY_SEND_TIME} 자동 발송",
            variable=self.auto_var,
            font=ctk.CTkFont(size=12),
            command=self.toggle_scheduler
        )
        self.auto_switch.pack(side="left", padx=20)

        # 필터 초기화
        reset_btn = ctk.CTkButton(
            row4, text="🔄 초기화",
            font=ctk.CTkFont(size=12),
            fg_color="#757575", hover_color="#616161",
            width=100, height=32,
            command=self.reset_filters
        )
        reset_btn.pack(side="right", padx=5)

    def _build_result_area(self):
        """결과 표시 영역"""
        result_container = ctk.CTkFrame(self, corner_radius=12)
        result_container.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        result_container.grid_columnconfigure(0, weight=1)
        result_container.grid_rowconfigure(1, weight=1)

        # 결과 헤더
        header = ctk.CTkFrame(result_container, fg_color="transparent")
        header.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")

        self.result_label = ctk.CTkLabel(
            header,
            text="검색 결과가 여기에 표시됩니다",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#555"
        )
        self.result_label.pack(side="left")

        # 정렬 옵션
        self.sort_combo = ctk.CTkComboBox(
            header,
            values=["최신순", "회사명순", "사이트순"],
            width=120, height=30,
            font=ctk.CTkFont(size=11),
            command=self.on_sort_changed
        )
        self.sort_combo.set("최신순")
        self.sort_combo.pack(side="right")

        # 카드 표시 영역 (스크롤 가능)
        self.cards_frame = ctk.CTkScrollableFrame(
            result_container,
            fg_color="#F5F5F5",
            corner_radius=8
        )
        self.cards_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # 진행 표시
        self.progress_bar = ctk.CTkProgressBar(result_container, mode="indeterminate")
        self.progress_bar.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.progress_bar.grid_remove()

    def _build_status_bar(self):
        """하단 상태바"""
        status_frame = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#E8EAF6")
        status_frame.grid(row=2, column=0, sticky="ew")

        self.status_label = ctk.CTkLabel(
            status_frame,
            text=f"준비 완료 | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            font=ctk.CTkFont(size=11),
            text_color="#555"
        )
        self.status_label.pack(side="left", padx=15, pady=4)

        self.count_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#555"
        )
        self.count_label.pack(side="right", padx=15, pady=4)

    # ============= 기능 메서드 =============

    def get_selected_tech_stacks(self) -> List[str]:
        """선택된 기술 스택 반환"""
        return [tech for tech, var in self.tech_vars.items() if var.get()]

    def get_search_params(self) -> dict:
        """검색 파라미터 수집"""
        return {
            "keyword": self.keyword_entry.get().strip(),
            "category": self.category_combo.get(),
            "experience": self.exp_combo.get(),
            "education": self.edu_combo.get(),
            "region": self.region_combo.get(),
            "tech_stacks": self.get_selected_tech_stacks()
        }

    def start_crawling(self):
        """크롤링 시작"""
        if self.is_crawling:
            return

        self.is_crawling = True
        self.search_btn.configure(state="disabled", text="⏳ 검색 중...")
        self.progress_bar.grid()
        self.progress_bar.start()
        self.update_status("크롤링 진행 중...")

        # 카드 영역 초기화
        self._clear_cards()

        # 별도 스레드에서 실행
        thread = threading.Thread(target=self._crawl_worker, daemon=True)
        thread.start()

    def _crawl_worker(self):
        """크롤링 워커 (백그라운드 스레드)"""
        params = self.get_search_params()
        keyword = params.get("keyword", "")
        all_jobs: List[JobPosting] = []

        crawlers_to_run = []
        if self.saramin_var.get():
            crawlers_to_run.append(("사람인", SaraminCrawler()))
        if self.jobkorea_var.get():
            crawlers_to_run.append(("잡코리아", JobKoreaCrawler()))
        if self.wanted_var.get():
            crawlers_to_run.append(("원티드", WantedCrawler()))

        for name, crawler in crawlers_to_run:
            self.after(0, lambda n=name: self.update_status(f"{n} 크롤링 중..."))
            try:
                jobs = crawler.run(keyword, **params)
                all_jobs.extend(jobs)
                self.after(0, lambda n=name, c=len(jobs):
                           self.update_status(f"{n}: {c}개 수집 완료"))
            except Exception as e:
                logger.error(f"[{name}] 에러: {e}")
                self.after(0, lambda n=name:
                           self.update_status(f"{n} 크롤링 실패"))

        # 필터링
        self.all_jobs = all_jobs
        self.filtered_jobs = FilterService.filter_jobs(
            all_jobs, **params
        )

        # UI 업데이트 (메인 스레드)
        self.after(0, self._on_crawl_complete)

    def _on_crawl_complete(self):
        """크롤링 완료 후 UI 업데이트"""
        self.is_crawling = False
        self.search_btn.configure(state="normal", text="🔍 검색 시작")
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

        count = len(self.filtered_jobs)
        self.result_label.configure(
            text=f"📋 검색 결과: {count}건 (전체 {len(self.all_jobs)}건 중)"
        )
        self.count_label.configure(text=f"표시: {count}건")
        self.update_status(f"검색 완료 - {count}건 표시")

        self._display_cards(self.filtered_jobs)

    def _clear_cards(self):
        """카드 영역 초기화"""
        for widget in self.cards_frame.winfo_children():
            widget.destroy()

    def _display_cards(self, jobs: List[JobPosting]):
        """카드 표시"""
        self._clear_cards()

        if not jobs:
            no_result = ctk.CTkLabel(
                self.cards_frame,
                text="😢 검색 결과가 없습니다.\n검색 조건을 변경해 보세요.",
                font=ctk.CTkFont(size=16),
                text_color="#999",
                justify="center"
            )
            no_result.pack(pady=50)
            return

        for job in jobs:
            card = JobCard(self.cards_frame, job)
            card.pack(fill="x", padx=10, pady=5)

    def on_sort_changed(self, value):
        """정렬 변경"""
        sort_map = {
            "최신순": "latest",
            "회사명순": "company",
            "사이트순": "source"
        }
        sort_by = sort_map.get(value, "latest")
        self.filtered_jobs = FilterService.sort_jobs(self.filtered_jobs, sort_by)
        self._display_cards(self.filtered_jobs)

    def send_email(self):
        """이메일 발송"""
        if not self.filtered_jobs:
            self._show_message("알림", "발송할 공고가 없습니다.\n먼저 검색을 실행하세요.", "warning")
            return

        self.update_status("이메일 발송 중...")

        def _send():
            success = MailService.send_jobs_email(self.filtered_jobs)
            if success:
                self.after(0, lambda: self._show_message(
                    "성공", f"✅ {len(self.filtered_jobs)}건의 공고를 이메일로 발송했습니다.", "check"
                ))
                self.after(0, lambda: self.update_status("이메일 발송 성공"))
            else:
                self.after(0, lambda: self._show_message(
                    "실패", "❌ 이메일 발송에 실패했습니다.\nconfig.py의 이메일 설정을 확인하세요.", "cancel"
                ))
                self.after(0, lambda: self.update_status("이메일 발송 실패"))

        threading.Thread(target=_send, daemon=True).start()

    def toggle_scheduler(self):
        """일일 자동 발송 토글"""
        if self.auto_var.get():
            params = self.get_search_params()
            self.scheduler = DailyScheduler(
                search_params=params,
                callback=lambda jobs: self.after(
                    0, lambda: self._on_scheduled_crawl(jobs)
                )
            )
            self.scheduler.start()
            self.update_status(f"자동 발송 활성화 (매일 {Config.DAILY_SEND_TIME})")
            self._show_message(
                "자동 발송",
                f"✅ 매일 {Config.DAILY_SEND_TIME}에 자동으로\n크롤링 후 이메일을 발송합니다.",
                "check"
            )
        else:
            if self.scheduler:
                self.scheduler.stop()
                self.scheduler = None
            self.update_status("자동 발송 비활성화")

    def _on_scheduled_crawl(self, jobs: List[JobPosting]):
        """스케줄 크롤링 완료 콜백"""
        self.all_jobs = jobs
        self.filtered_jobs = jobs
        self._display_cards(jobs)
        self.result_label.configure(text=f"📋 자동 수집 결과: {len(jobs)}건")

    def reset_filters(self):
        """필터 초기화"""
        self.keyword_entry.delete(0, "end")
        self.category_combo.set("전체")
        self.exp_combo.set("전체")
        self.edu_combo.set("전체")
        self.region_combo.set("전체")

        for var in self.tech_vars.values():
            var.set(False)

        self.saramin_var.set(True)
        self.jobkorea_var.set(True)
        self.wanted_var.set(True)

        self.update_status("필터 초기화됨")

    def update_status(self, message: str):
        """상태 업데이트"""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.status_label.configure(text=f"{message} | {time_str}")

    def _show_message(self, title: str, message: str, icon: str = "info"):
        """메시지 표시 - CTkMessagebox 없으면 기본 방식"""
        try:
            CTkMessagebox(
                title=title, message=message,
                icon=icon, font=ctk.CTkFont(size=13)
            )
        except NameError:
            # CTkMessagebox가 없으면 간단한 팝업
            popup = ctk.CTkToplevel(self)
            popup.title(title)
            popup.geometry("400x200")
            popup.resizable(False, False)
            popup.grab_set()

            ctk.CTkLabel(
                popup, text=message,
                font=ctk.CTkFont(size=14),
                wraplength=350
            ).pack(pady=30)

            ctk.CTkButton(
                popup, text="확인", width=100,
                command=popup.destroy
            ).pack(pady=10)