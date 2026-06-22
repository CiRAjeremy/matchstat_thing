"""
Configuration management for Matchstat scraper
Loads settings from .env file and environment variables
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Application configuration"""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not set in environment variables")
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = 'logs/scraper.log'
    
    # Scraping
    USER_AGENT = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))
    MIN_DELAY = float(os.getenv('MIN_DELAY', '2.0'))
    MAX_DELAY = float(os.getenv('MAX_DELAY', '5.0'))
    
    # Future: Firecrawl
    FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')
    FIRECRAWL_ENABLED = bool(FIRECRAWL_API_KEY)
    
    # Telegram Notifications (optional)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    
    # Validation
    if REQUEST_TIMEOUT <= 0:
        raise ValueError("REQUEST_TIMEOUT must be positive")
    if MIN_DELAY < 0 or MAX_DELAY < 0:
        raise ValueError("Delays must be positive")
    if MIN_DELAY > MAX_DELAY:
        raise ValueError("MIN_DELAY cannot be greater than MAX_DELAY")
    
    # Directories
    LOGS_DIR = Path('logs')
    BACKUPS_DIR = Path('backups')
    
    @classmethod
    def ensure_directories(cls):
        """Create required directories if they don't exist"""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.BACKUPS_DIR.mkdir(exist_ok=True)

# Ensure directories exist on import
Config.ensure_directories()
