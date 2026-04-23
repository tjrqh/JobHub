import logging
import sys

def setup_logging():
    """로그 레벨을 모듈별로 다르게 설정"""
    
    # 전체 포맷
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    
    # 파일 핸들러 (선택사항)
    file_handler = logging.FileHandler('crawler.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # 루트 로거 설정
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # 전체는 DEBUG로 받되
    root.addHandler(console)
    root.addHandler(file_handler)
    
    # 🔥 핵심: 모듈별 레벨 설정
    logging.getLogger('selenium').setLevel(logging.WARNING)      # selenium 로그 억제
    logging.getLogger('urllib3').setLevel(logging.WARNING)       # urllib3 로그 억제
    logging.getLogger('crawlers').setLevel(logging.INFO)         # 크롤러는 INFO만
    logging.getLogger('services').setLevel(logging.INFO)         # 서비스는 INFO만
    logging.getLogger('gui').setLevel(logging.WARNING)           # GUI는 WARNING만
    
    return root

def main():
    setup_logging()
    
    from gui.app import App
    app = App()
    app.run()

if __name__ == "__main__":
    main()