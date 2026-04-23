import webbrowser
import threading
import logging
from datetime import datetime
from typing import List

import tkinter as tk
from tkinter import ttk, messagebox
import platform

from config import Config
from models.job import JobPosting
from crawlers import SaraminCrawler, JobKoreaCrawler, WantedCrawler
from services.filter_service import FilterService
from services.mail_service import MailService
from scheduler.daily_scheduler import DailyScheduler
from utils.helpers import get_source_display_name

logger = logging.getLogger(__name__)


class App:
    """표준 tkinter 기반 메인 애플리케이션"""

    SOURCE_COLORS = {
        "saramin": "#0D47A1",
        "jobkorea": "#00897B",
        "wanted": "#3F51B5"
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("💼 취업 조지기 : 취조")
        self.root.geometry("1100x850")
        self.root.minsize(900, 600)

        self.all_jobs: List[JobPosting] = []
        self.filtered_jobs: List[JobPosting] = []
        self.scheduler: DailyScheduler = None
        self.is_crawling = False

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Title.TLabel", font=("Helvetica", 16, "bold"))
        self.style.configure("Sub.TLabel", font=("Helvetica", 12))
        self.style.configure("Status.TLabel", font=("Helvetica", 10), foreground="#666")

        self.current_page = 0
        self.page_size = 20
        self.rendered_count = 0

        self._build_ui()

    # ==================================================
    #  UI 구성
    # ==================================================
    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)
        self._build_search_panel(main_frame)
        self._build_result_area(main_frame)
        self._build_status_bar()

    def _build_search_panel(self, parent):
        search_frame = ttk.LabelFrame(parent, text="🔍 검색 조건", padding=10)
        search_frame.pack(fill="x", pady=(0, 5))

        # 1줄: 키워드 + 검색 + 사이트
        row1 = ttk.Frame(search_frame)
        row1.pack(fill="x", pady=(0, 5))
        ttk.Label(row1, text="키워드:", font=("Helvetica", 12, "bold")).pack(side="left", padx=(0, 5))

        self.keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(row1, textvariable=self.keyword_var, width=30, font=("Helvetica", 12))
        keyword_entry.pack(side="left", padx=(0, 10))
        keyword_entry.bind("<Return>", lambda e: self.start_crawling())

        self.search_btn = ttk.Button(row1, text="🔍 검색", command=self.start_crawling)
        self.search_btn.pack(side="left", padx=5)

        site_frame = ttk.Frame(row1)
        site_frame.pack(side="right")
        self.saramin_var = tk.BooleanVar(value=True)
        self.jobkorea_var = tk.BooleanVar(value=True)
        self.wanted_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(site_frame, text="사람인", variable=self.saramin_var).pack(side="left", padx=5)
        ttk.Checkbutton(site_frame, text="잡코리아", variable=self.jobkorea_var).pack(side="left", padx=5)
        ttk.Checkbutton(site_frame, text="원티드", variable=self.wanted_var).pack(side="left", padx=5)

        # 2줄: 필터
        row2 = ttk.Frame(search_frame)
        row2.pack(fill="x", pady=(0, 5))
        filters = [
            ("직종:", "category", Config.JOB_CATEGORIES),
            ("경력:", "experience", Config.EXPERIENCE_LEVELS),
            ("학력:", "education", Config.EDUCATION_LEVELS),
            ("지역:", "location", Config.LOCATIONS),
        ]
        self.filter_vars = {}
        for label_text, key, values in filters:
            ttk.Label(row2, text=label_text).pack(side="left", padx=(10, 3))
            var = tk.StringVar(value="전체")
            self.filter_vars[key] = var
            ttk.Combobox(row2, textvariable=var, values=values, width=10, state="readonly").pack(side="left", padx=(0, 5))

        # 3줄: 기술스택
        row3 = ttk.Frame(search_frame)
        row3.pack(fill="x", pady=(0, 5))
        ttk.Label(row3, text="기술스택:", font=("Helvetica", 12, "bold")).pack(side="left", padx=(0, 5))

        tech_canvas = tk.Canvas(row3, height=30, highlightthickness=0)
        tech_scroll = ttk.Scrollbar(row3, orient="horizontal", command=tech_canvas.xview)
        tech_inner = ttk.Frame(tech_canvas)
        tech_inner.bind("<Configure>", lambda e: tech_canvas.configure(scrollregion=tech_canvas.bbox("all")))
        tech_canvas.create_window((0, 0), window=tech_inner, anchor="nw")
        tech_canvas.configure(xscrollcommand=tech_scroll.set)
        tech_canvas.pack(side="left", fill="x", expand=True)
        tech_scroll.pack(side="bottom", fill="x")

        self.tech_vars = {}
        for tech in Config.TECH_STACKS:
            var = tk.BooleanVar(value=False)
            self.tech_vars[tech] = var
            ttk.Checkbutton(tech_inner, text=tech, variable=var).pack(side="left", padx=2, pady=2)

        # 4줄: 버튼
        row4 = ttk.Frame(search_frame)
        row4.pack(fill="x", pady=(5, 0))
        ttk.Button(row4, text="📧 메일 발송", command=self.send_email).pack(side="left", padx=5)
        self.auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row4, text=f"매일 자동 발송 ({Config.DAILY_SEND_TIME})",
                        variable=self.auto_var, command=self.toggle_scheduler).pack(side="left", padx=20)
        ttk.Button(row4, text="🔄 초기화", command=self.reset_filters).pack(side="right", padx=5)

    def _build_result_area(self, parent):
        result_frame = ttk.LabelFrame(parent, text="📋 검색 결과", padding=5)
        result_frame.pack(fill="both", expand=True, pady=(5, 0))

        header = ttk.Frame(result_frame)
        header.pack(fill="x", pady=(0, 5))
        self.result_label = ttk.Label(header, text="검색 결과가 여기에 표시됩니다", style="Title.TLabel")
        self.result_label.pack(side="left")

        self.sort_var = tk.StringVar(value="최신순")
        self.sort_combo = ttk.Combobox(
            header, textvariable=self.sort_var,
            values=["최신순", "회사명순", "사이트순"],
            width=10, state="readonly"
        )
        self.sort_combo.pack(side="right")
        self.sort_combo.bind("<<ComboboxSelected>>", self.on_sort_changed)

        result_inner = ttk.Frame(result_frame)
        result_inner.pack(fill="both", expand=True)

        self.result_canvas = tk.Canvas(result_inner, highlightthickness=0)
        scrollbar = ttk.Scrollbar(result_inner, orient="vertical", command=self.result_canvas.yview)
        self.cards_frame = ttk.Frame(self.result_canvas)
        self.cards_frame.bind(
            "<Configure>",
            lambda e: self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all"))
        )
        self.result_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.result_canvas.configure(yscrollcommand=scrollbar.set)
        self.result_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ✅ 결과 영역에 마우스가 들어올 때만 스크롤 활성화, 나갈 때 비활성화
        self.result_canvas.bind("<Enter>", self._bind_mousewheel)
        self.result_canvas.bind("<Leave>", self._unbind_mousewheel)

    # ==================================================
    #  마우스 휠 스크롤 (결과 영역 한정)
    # ==================================================
    def _bind_mousewheel(self, event=None):
        """결과 영역에 마우스 진입 시 전역 스크롤 등록"""
        self.result_canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows / macOS
        self.result_canvas.bind_all("<Button-4>", self._on_mousewheel)    # Linux 스크롤 업
        self.result_canvas.bind_all("<Button-5>", self._on_mousewheel)    # Linux 스크롤 다운

    def _unbind_mousewheel(self, event=None):
        """결과 영역에서 마우스 이탈 시 전역 스크롤 해제"""
        self.result_canvas.unbind_all("<MouseWheel>")
        self.result_canvas.unbind_all("<Button-4>")
        self.result_canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:          # Linux 업
            self.result_canvas.yview_scroll(-1, "units")
        elif event.num == 5:        # Linux 다운
            self.result_canvas.yview_scroll(1, "units")
        elif platform.system() == "Darwin":   # macOS: delta가 1~5 단위
            self.result_canvas.yview_scroll(int(-1 * event.delta), "units")
        else:                                 # Windows: delta가 120 단위
            self.result_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_status_bar(self):
        status_frame = ttk.Frame(self.root, padding=(10, 3))
        status_frame.pack(fill="x", side="bottom")
        self.status_label = ttk.Label(status_frame, text=f"준비 완료 | {datetime.now().strftime('%Y-%m-%d %H:%M')}", style="Status.TLabel")
        self.status_label.pack(side="left")
        self.count_label = ttk.Label(status_frame, text="", style="Status.TLabel")
        self.count_label.pack(side="right")

    # ==================================================
    #  기능 메서드
    # ==================================================
    def get_selected_tech_stacks(self) -> List[str]:
        return [t for t, v in self.tech_vars.items() if v.get()]

    def get_search_params(self) -> dict:
        return {
            "keyword": self.keyword_var.get().strip(),
            "category": self.filter_vars["category"].get(),
            "experience": self.filter_vars["experience"].get(),
            "education": self.filter_vars["education"].get(),
            "location": self.filter_vars["location"].get(),
            "tech_stacks": self.get_selected_tech_stacks(),
        }

    def start_crawling(self):
        if self.is_crawling: return
        self.is_crawling = True
        self.search_btn.configure(state="disabled", text="⏳ 검색 중...")
        self.update_status("크롤링 진행 중...")
        self._clear_cards()
        threading.Thread(target=self._crawl_worker, daemon=True).start()

    def _crawl_worker(self):
        params = self.get_search_params()
        keyword = params.pop("keyword", "")
        all_jobs: List[JobPosting] = []

        crawlers = []
        if self.saramin_var.get(): crawlers.append(("사람인", SaraminCrawler()))
        if self.jobkorea_var.get(): crawlers.append(("잡코리아", JobKoreaCrawler()))
        if self.wanted_var.get(): crawlers.append(("원티드", WantedCrawler()))

        for name, crawler in crawlers:
            self.root.after(0, lambda n=name: self.update_status(f"{n} 크롤링 중..."))
            try:
                jobs = crawler.run(keyword=keyword, **params)
                all_jobs.extend(jobs)
                self.root.after(0, lambda n=name, c=len(jobs): self.update_status(f"{n}: {c}개 수집"))
            except Exception as e:
                logger.error(f"[{name}] 에러: {e}")
                self.root.after(0, lambda n=name: self.update_status(f"{n} 크롤링 실패"))

        self.all_jobs = all_jobs
        self.filtered_jobs = FilterService.filter_jobs(all_jobs, keyword=keyword, **params)
        self.root.after(0, lambda: self._apply_results(all_jobs, keyword, params))

    def _on_crawl_complete(self):
        self.is_crawling = False
        self.search_btn.configure(state="normal", text="🔍 검색")
        count = len(self.filtered_jobs)
        self.result_label.configure(text=f"📋 결과: {count}건 (전체 {len(self.all_jobs)}건)")
        self.count_label.configure(text=f"표시: {count}건")
        self.update_status(f"검색 완료 - {count}건")
        self._display_cards(self.filtered_jobs)

    def _clear_cards(self):
        for w in self.cards_frame.winfo_children(): w.destroy()

    def _display_cards(self, jobs: List[JobPosting]):
        self._clear_cards()

        if not jobs:
            ttk.Label(self.cards_frame, text="😢 검색 결과가 없습니다.", font=("Helvetica", 16)).pack(pady=50)
            return

        self._render_next_page()

    def _create_card(self, job: JobPosting):
        card = tk.Frame(self.cards_frame, relief="solid", bd=1, bg="#FFFFFF", padx=10, pady=8)
        card.pack(fill="x", padx=5, pady=4)
        color = self.SOURCE_COLORS.get(job.source, "#333")
        source_name = get_source_display_name(job.source)

        top = tk.Frame(card, bg="#FFFFFF")
        top.pack(fill="x")
        tk.Label(top, text=f" {source_name} ", bg=color, fg="white", font=("Helvetica", 9, "bold"), padx=6, pady=1).pack(side="left")
        deadline = f"마감: {job.deadline}" if job.deadline else ""
        tk.Label(top, text=deadline, bg="#FFFFFF", fg="#999", font=("Helvetica", 9)).pack(side="right")

        title = job.title if len(job.title) <= 60 else job.title[:57] + "..."
        title_lbl = tk.Label(card, text=title, bg="#FFFFFF", font=("Helvetica", 13, "bold"), fg="#212121", anchor="w", cursor="hand2")
        title_lbl.pack(fill="x", pady=(4, 2))
        title_lbl.bind("<Button-1>", lambda e, u=job.url: webbrowser.open(u))

        tk.Label(card, text=f"🏢 {job.company}", bg="#FFFFFF", fg="#555", font=("Helvetica", 11), anchor="w").pack(fill="x")

        parts = []
        if job.location: parts.append(f"📍 {job.location}")
        if job.experience: parts.append(f"💼 {job.experience}")
        if job.education: parts.append(f"🎓 {job.education}")
        if job.salary: parts.append(f"💰 {job.salary}")
        if parts:
            tk.Label(card, text="  |  ".join(parts), bg="#FFFFFF", fg="#777", font=("Helvetica", 10), anchor="w").pack(fill="x", pady=(2, 2))

        if job.tech_stack:
            sf = tk.Frame(card, bg="#FFFFFF")
            sf.pack(fill="x", pady=(2, 4))
            for tech in job.tech_stack[:8]:
                tk.Label(sf, text=f" {tech} ", bg="#E3F2FD", fg=color, font=("Helvetica", 9), padx=4, pady=1).pack(side="left", padx=2, pady=1)

        bf = tk.Frame(card, bg="#FFFFFF")
        bf.pack(fill="x")
        tk.Button(bf, text="🔗 공고 보기", bg=color, fg="white", font=("Helvetica", 10, "bold"), padx=12, pady=4, relief="flat", cursor="hand2",
                  command=lambda u=job.url: webbrowser.open(u)).pack(side="right")

        def on_enter(e, c=card): c.configure(bg="#F5F5F5")
        def on_leave(e, c=card): c.configure(bg="#FFFFFF")
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def on_sort_changed(self, event=None):
        sort_map = {"최신순": "latest", "회사명순": "company", "사이트순": "source"}
        sort_by = sort_map.get(self.sort_var.get(), "latest")
        self.filtered_jobs = FilterService.sort_jobs(self.filtered_jobs, sort_by)
        self._display_cards(self.filtered_jobs)

    def send_email(self):
        if not self.filtered_jobs:
            messagebox.showwarning("알림", "발송할 공고가 없습니다.\n먼저 검색하세요.")
            return
        self.update_status("이메일 발송 중...")
        def _send():
            success = MailService.send_jobs_email(self.filtered_jobs)
            if success:
                self.root.after(0, lambda: messagebox.showinfo("성공", f"✅ {len(self.filtered_jobs)}건 발송 완료"))
            else:
                self.root.after(0, lambda: messagebox.showerror("실패", "❌ 이메일 발송 실패\n.env를 확인하세요"))
        threading.Thread(target=_send, daemon=True).start()

    def toggle_scheduler(self):
        if self.auto_var.get():
            params = self.get_search_params()
            self.scheduler = DailyScheduler(search_params=params, callback=lambda jobs: self.root.after(0, lambda: self._on_scheduled_crawl(jobs)))
            self.scheduler.start()
            self.update_status(f"자동 발송 ON (매일 {Config.DAILY_SEND_TIME})")
            messagebox.showinfo("자동 발송", f"✅ 매일 {Config.DAILY_SEND_TIME}에 자동 발송")
        else:
            if self.scheduler: self.scheduler.stop(); self.scheduler = None
            self.update_status("자동 발송 OFF")

    def _on_scheduled_crawl(self, jobs):
        self.all_jobs = jobs
        self.filtered_jobs = jobs
        self._display_cards(jobs)
        self.result_label.configure(text=f"📋 자동 수집: {len(jobs)}건")

    def reset_filters(self):
        self.keyword_var.set("")
        for var in self.filter_vars.values(): var.set("전체")
        for var in self.tech_vars.values(): var.set(False)
        self.saramin_var.set(True); self.jobkorea_var.set(True); self.wanted_var.set(True)
        self.update_status("필터 초기화됨")

    def update_status(self, message: str):
        self.status_label.configure(text=f"{message} | {datetime.now().strftime('%H:%M:%S')}")

    def run(self):
        self.root.mainloop()

    def _apply_results(self, all_jobs, keyword, params):
        self.all_jobs = all_jobs
        self.filtered_jobs = FilterService.filter_jobs(
            all_jobs, keyword=keyword, **params
        )
        self.current_page = 0
        self.rendered_count = 0
        self._on_crawl_complete()

    def _render_next_page(self):
        start = self.rendered_count
        end = start + self.page_size

        page_jobs = self.filtered_jobs[start:end]

        for job in page_jobs:
            self._create_card(job)

        self.rendered_count += len(page_jobs)

        if self.rendered_count < len(self.filtered_jobs):
            btn = ttk.Button(
                self.cards_frame,
                text="⬇️ 더 보기",
                command=self._load_more
            )
            btn.pack(pady=10)

    def _load_more(self):
        for widget in self.cards_frame.winfo_children():
            if isinstance(widget, ttk.Button) and widget.cget("text") == "⬇️ 더 보기":
                widget.destroy()
        self._render_next_page()