"""
Utility functions for Matchstat scraper
"""
import re
import time
import random
import logging
from datetime import datetime
from urllib.robotparser import RobotFileParser
from typing import Optional

from src.config import Config

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# SCRAPING UTILITIES
# ═══════════════════════════════════════════════════════════

def get_headers() -> dict:
    """
    Return randomized HTTP headers to avoid detection
    
    Returns:
        dict: HTTP headers with randomized User-Agent
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }


def smart_delay(min_seconds: float = None, max_seconds: float = None) -> None:
    """
    Random delay to avoid detection and respect rate limits
    
    Args:
        min_seconds: Minimum delay (default from config)
        max_seconds: Maximum delay (default from config)
    """
    if min_seconds is None:
        min_seconds = Config.MIN_DELAY
    if max_seconds is None:
        max_seconds = Config.MAX_DELAY
    
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Waiting {delay:.2f} seconds...")
    time.sleep(delay)


def check_robots_txt(url: str) -> bool:
    """
    Check if scraping is allowed by robots.txt
    
    Args:
        url: URL to check
    
    Returns:
        bool: True if allowed, False if disallowed
    """
    try:
        rp = RobotFileParser()
        base_url = '/'.join(url.split('/')[:3])
        rp.set_url(f"{base_url}/robots.txt")
        rp.read()
        
        allowed = rp.can_fetch("*", url)
        
        if not allowed:
            logger.warning(f"⚠️ robots.txt disallows scraping: {url}")
        else:
            logger.debug(f"✓ robots.txt allows scraping: {url}")
        
        return allowed
        
    except Exception as e:
        logger.warning(f"Could not check robots.txt for {url}: {e}")
        return True  # Assume allowed if can't check


# ═══════════════════════════════════════════════════════════
# TEXT PROCESSING
# ═══════════════════════════════════════════════════════════

def clean_player_name(raw_name: str) -> str:
    """
    Remove rankings, badges, and normalize player names
    
    Examples:
        "Rafael Nadal 2" -> "Rafael Nadal"
        "R. Nadal WC" -> "R. Nadal"
        "Djokovic N. (1)" -> "Djokovic N."
    
    Args:
        raw_name: Raw player name from website
    
    Returns:
        str: Cleaned player name
    """
    if not raw_name:
        return ""
    
    # Remove trailing numbers (rankings in parentheses or not)
    name = re.sub(r'\s*\(\d+\)\s*$', '', raw_name)
    name = re.sub(r'\s*\d+\s*$', '', name)
    
    # Remove badges (WC, Q, ALT, LL, PR, SE, etc.)
    name = re.sub(r'\s*(ALT|WC|q|Q|LL|PR|SE|WR)\s*$', '', name, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    return name.strip()


def parse_rank(text: str) -> Optional[int]:
    """
    Extract player ranking from text
    
    Examples:
        "Rafael Nadal (2)" -> 2
        "Nadal 5" -> 5
        "Federer" -> None
    
    Args:
        text: Text containing ranking
    
    Returns:
        int or None: Ranking number if found
    """
    if not text:
        return None
    
    # Try parentheses first: (2)
    match = re.search(r'\((\d+)\)', text)
    if match:
        return int(match.group(1))
    
    # Try trailing number: Nadal 2
    match = re.search(r'\s+(\d+)\s*$', text)
    if match:
        return int(match.group(1))
    
    # Try leading number: 2 Nadal
    match = re.search(r'^(\d+)\s+', text)
    if match:
        return int(match.group(1))
    
    return None


def fuzzy_match_player(name1: str, name2: str) -> bool:
    """
    Check if two player names refer to the same person
    
    Examples:
        "Rafael Nadal" matches "R. Nadal" -> True
        "Nadal" matches "R Nadal" -> True
        "Nadal" matches "Federer" -> False
    
    Args:
        name1: First player name
        name2: Second player name
    
    Returns:
        bool: True if names likely match
    """
    if not name1 or not name2:
        return False
    
    # Exact match (case-insensitive)
    if name1.lower() == name2.lower():
        return True
    
    # Extract last names (assume last word is surname)
    last1 = name1.split()[-1].lower()
    last2 = name2.split()[-1].lower()
    
    # Last name match
    if last1 == last2:
        return True
    
    # Handle initials: R. Nadal vs Rafael Nadal
    # Extract first name/initial
    first1 = name1.split()[0].lower().replace('.', '')
    first2 = name2.split()[0].lower().replace('.', '')
    
    # If last names match and one first name is initial of other
    if last1 == last2:
        if first1[0] == first2[0]:  # First letter matches
            return True
    
    return False


# ═══════════════════════════════════════════════════════════
# DATE/TIME UTILITIES
# ═══════════════════════════════════════════════════════════

def parse_match_date(date_string: str, time_string: str = None) -> datetime:
    """
    Parse various date formats into datetime object
    
    Examples:
        "05 Jan 2024" -> datetime(2024, 1, 5)
        "2024-01-05" -> datetime(2024, 1, 5)
        "05.01.2024", "14:30" -> datetime(2024, 1, 5, 14, 30)
    
    Args:
        date_string: Date string in various formats
        time_string: Optional time string (e.g., "14:30")
    
    Returns:
        datetime: Parsed datetime object
    
    Raises:
        ValueError: If date cannot be parsed
    """
    if not date_string:
        raise ValueError("Date string is empty")
    
    # Clean up string
    date_string = date_string.strip()
    
    # Date format patterns to try
    date_formats = [
        '%d %b %Y',      # 05 Jan 2024
        '%d %B %Y',      # 05 January 2024
        '%Y-%m-%d',      # 2024-01-05
        '%d.%m.%Y',      # 05.01.2024
        '%d/%m/%Y',      # 05/01/2024
        '%m/%d/%Y',      # 01/05/2024 (US format)
    ]
    
    parsed_date = None
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_string, fmt)
            break
        except ValueError:
            continue
    
    if not parsed_date:
        raise ValueError(f"Could not parse date: {date_string}")
    
    # Add time if provided
    if time_string:
        time_string = time_string.strip()
        try:
            # Try HH:MM format
            time_obj = datetime.strptime(time_string, '%H:%M').time()
            parsed_date = parsed_date.replace(
                hour=time_obj.hour,
                minute=time_obj.minute
            )
        except ValueError:
            logger.warning(f"Could not parse time: {time_string}")
    
    return parsed_date


def calculate_hours_until(target_datetime: datetime) -> float:
    """
    Calculate hours from now until target datetime
    
    Args:
        target_datetime: Future datetime
    
    Returns:
        float: Hours until target (negative if in past)
    """
    if isinstance(target_datetime, str):
        target_datetime = parse_match_date(target_datetime)
    
    delta = target_datetime - datetime.now()
    hours = delta.total_seconds() / 3600
    
    return round(hours, 2)


# ═══════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════

def validate_odds(odds: float) -> bool:
    """
    Check if odds value is reasonable
    
    Args:
        odds: Decimal odds value
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        odds_float = float(odds)
        
        if odds_float < 1.01:
            logger.warning(f"Odds too low (< 1.01): {odds}")
            return False
        
        if odds_float > 100:
            logger.warning(f"Odds suspiciously high (> 100): {odds}")
            return False
        
        return True
        
    except (ValueError, TypeError):
        logger.warning(f"Invalid odds format: {odds}")
        return False


def validate_prediction_data(data: dict) -> bool:
    """
    Validate scraped prediction data before saving to database
    
    Args:
        data: Dictionary containing prediction fields
    
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = [
        'player1_name',
        'player2_name',
        'predicted_winner',
        'match_datetime',
        'matchstat_url'
    ]
    
    # Check required fields exist and are not empty
    for field in required_fields:
        if field not in data or not data[field]:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Check players are different
    if data['player1_name'] == data['player2_name']:
        logger.error(f"Same player listed twice: {data['player1_name']}")
        return False
    
    # Check predicted winner is one of the players
    winner = data['predicted_winner']
    p1 = data['player1_name']
    p2 = data['player2_name']
    
    if not (fuzzy_match_player(winner, p1) or fuzzy_match_player(winner, p2)):
        logger.error(f"Predicted winner '{winner}' not in match ({p1} vs {p2})")
        return False
    
    # Check odds if provided
    if 'player1_odds' in data and data['player1_odds']:
        if not validate_odds(data['player1_odds']):
            return False
    
    if 'player2_odds' in data and data['player2_odds']:
        if not validate_odds(data['player2_odds']):
            return False
    
    # Check match datetime is datetime object
    if not isinstance(data['match_datetime'], datetime):
        logger.error(f"match_datetime must be datetime object, got {type(data['match_datetime'])}")
        return False
    
    return True


# ═══════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════

def setup_logging(log_file: str = None, level: str = None) -> logging.Logger:
    """
    Setup application logging with file and console handlers
    
    Args:
        log_file: Path to log file (default from config)
        level: Log level (default from config)
    
    Returns:
        logging.Logger: Configured root logger
    """
    if log_file is None:
        log_file = Config.LOG_FILE
    
    if level is None:
        level = Config.LOG_LEVEL
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory if needed
    Config.ensure_directories()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)
    
    # Console handler
    try:
        # Try to use colored logging
        import colorlog
        console_handler = colorlog.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
    except ImportError:
        # Fallback to regular console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
    
    console_handler.setLevel(numeric_level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    
    return root_logger


# ═══════════════════════════════════════════════════════════
# HTML EXTRACTION HELPERS
# ═══════════════════════════════════════════════════════════

def extract_text_or_none(element, selector: str = None, attribute: str = None) -> Optional[str]:
    """
    Safely extract text from BeautifulSoup element
    
    Args:
        element: BeautifulSoup element or tag
        selector: Optional CSS selector to find child element
        attribute: Optional attribute to extract instead of text
    
    Returns:
        str or None: Extracted text/attribute or None if not found
    """
    if element is None:
        return None
    
    try:
        # Find child element if selector provided
        if selector:
            element = element.select_one(selector)
            if element is None:
                return None
        
        # Extract attribute if specified
        if attribute:
            return element.get(attribute)
        
        # Extract text
        text = element.get_text(strip=True)
        return text if text else None
        
    except (AttributeError, TypeError):
        return None


def parse_odds_string(odds_string: str) -> Optional[float]:
    """
    Parse odds from various string formats
    
    Examples:
        "2.50" -> 2.50
        "5/2" -> 3.50 (fractional to decimal)
        "+150" -> 2.50 (American to decimal)
    
    Args:
        odds_string: Odds in string format
    
    Returns:
        float or None: Decimal odds
    """
    if not odds_string:
        return None
    
    odds_string = odds_string.strip()
    
    # Decimal odds: "2.50"
    try:
        return float(odds_string)
    except ValueError:
        pass
    
    # Fractional odds: "5/2"
    if '/' in odds_string:
        try:
            numerator, denominator = odds_string.split('/')
            decimal = (float(numerator) / float(denominator)) + 1
            return round(decimal, 2)
        except (ValueError, ZeroDivisionError):
            pass
    
    # American odds: "+150" or "-200"
    if odds_string.startswith(('+', '-')):
        try:
            american = float(odds_string)
            if american > 0:
                decimal = (american / 100) + 1
            else:
                decimal = (100 / abs(american)) + 1
            return round(decimal, 2)
        except ValueError:
            pass
    
    logger.warning(f"Could not parse odds: {odds_string}")
    return None
