import logging
import sys
from datetime import datetime


def setup_logging(level=logging.INFO):
    """로깅 설정"""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 파일 핸들러
    file_handler = logging.FileHandler(
        f"crawler_{datetime.now().strftime('%Y%m%d')}.log",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))

    # 루트 로거
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_source_display_name(source: str) -> str:
    """소스 표시 이름"""
    names = {
        "saramin": "사람인",
        "jobkorea": "잡코리아",
        "wanted": "원티드"
    }
    return names.get(source, source)


def get_source_color(source: str) -> str:
    """소스별 색상"""
    colors = {
        "saramin": "#0D47A1",
        "jobkorea": "#00897B",
        "wanted": "#3F51B5"
    }
    return colors.get(source, "#333333")


def truncate_text(text: str, max_length: int = 50) -> str:
    """텍스트 자르기"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."