# 🎾 MATCHSTAT TENNIS PREDICTION PROFITABILITY ANALYSIS
## COMPLETE IMPLEMENTATION PLAN - PART 2 OF 3

---

## 💻 COMPLETE CODE IMPLEMENTATIONS

### **File: src/config.py**

```python
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
    DATABASE_URL = os.getenv('NEON_DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("NEON_DATABASE_URL not set in environment variables")
    
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
```

---

### **File: src/utils.py**

```python
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
```

---

### **File: src/database.py**

```python
"""
Database operations for Matchstat scraper
Uses connection pooling for efficiency
"""
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from src.config import Config
from src.utils import clean_player_name, fuzzy_match_player

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CONNECTION POOL
# ═══════════════════════════════════════════════════════════

_pool = None

def get_pool():
    """Get or create connection pool"""
    global _pool
    if _pool is None:
        try:
            _pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=Config.DATABASE_URL
            )
            logger.info("✓ Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    return _pool


def get_connection():
    """Get connection from pool"""
    try:
        pool = get_pool()
        conn = pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Failed to get connection: {e}")
        raise


def release_connection(conn):
    """Return connection to pool"""
    try:
        pool = get_pool()
        pool.putconn(conn)
    except Exception as e:
        logger.error(f"Failed to release connection: {e}")


# ═══════════════════════════════════════════════════════════
# PLAYER OPERATIONS
# ═══════════════════════════════════════════════════════════

def get_or_create_player(name: str, country: str = None) -> int:
    """
    Get player ID, creating player if doesn't exist
    
    Args:
        name: Player name (will be cleaned)
        country: ISO country code (optional)
    
    Returns:
        int: player_id
    
    Raises:
        Exception: Database errors
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Clean name
        canonical_name = clean_player_name(name)
        
        if not canonical_name:
            raise ValueError(f"Empty player name after cleaning: {name}")
        
        # Check if player exists (exact match or in alternate names)
        cur.execute("""
            SELECT id, canonical_name, alternate_names
            FROM players
            WHERE canonical_name = %s
               OR %s = ANY(alternate_names)
        """, (canonical_name, canonical_name))
        
        result = cur.fetchone()
        
        if result:
            player_id = result[0]
            logger.debug(f"Found existing player: {canonical_name} (ID: {player_id})")
            return player_id
        
        # Check for fuzzy matches (same last name)
        last_name = canonical_name.split()[-1]
        cur.execute("""
            SELECT id, canonical_name, alternate_names
            FROM players
            WHERE canonical_name ILIKE %s
        """, (f'%{last_name}',))
        
        fuzzy_results = cur.fetchall()
        for row in fuzzy_results:
            existing_id, existing_name, alternates = row
            if fuzzy_match_player(canonical_name, existing_name):
                # Add this name as alternate
                cur.execute("""
                    UPDATE players
                    SET alternate_names = array_append(alternate_names, %s)
                    WHERE id = %s
                      AND NOT (%s = ANY(alternate_names))
                """, (canonical_name, existing_id, canonical_name))
                conn.commit()
                logger.info(f"Added '{canonical_name}' as alternate for '{existing_name}' (ID: {existing_id})")
                return existing_id
        
        # Create new player
        cur.execute("""
            INSERT INTO players (canonical_name, alternate_names, country)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (canonical_name, [name], country))
        
        player_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"✓ Created player: {canonical_name} (ID: {player_id})")
        return player_id
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating player '{name}': {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


# ═══════════════════════════════════════════════════════════
# PREDICTION OPERATIONS
# ═══════════════════════════════════════════════════════════

def save_prediction(
    player1_name: str,
    player2_name: str,
    predicted_winner_name: str,
    tournament_name: str,
    match_datetime: datetime,
    matchstat_url: str,
    player1_country: str = None,
    player2_country: str = None,
    player1_rank: int = None,
    player2_rank: int = None,
    tournament_round: str = None,
    surface: str = None,
    tour_type: str = None,
    raw_prediction_text: str = None,
    prediction_summary: dict = None
) -> Optional[int]:
    """
    Save prediction to database
    
    Returns:
        int: prediction_id if saved
        None: if duplicate (already exists)
    
    Raises:
        Exception: Database errors
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get/create player IDs
        player1_id = get_or_create_player(player1_name, player1_country)
        player2_id = get_or_create_player(player2_name, player2_country)
        predicted_winner_id = get_or_create_player(predicted_winner_name)
        
        # Validate winner is one of the players
        if predicted_winner_id not in [player1_id, player2_id]:
            # Try to match by name
            if fuzzy_match_player(predicted_winner_name, player1_name):
                predicted_winner_id = player1_id
            elif fuzzy_match_player(predicted_winner_name, player2_name):
                predicted_winner_id = player2_id
            else:
                raise ValueError(
                    f"Predicted winner '{predicted_winner_name}' (ID: {predicted_winner_id}) "
                    f"not in match: '{player1_name}' (ID: {player1_id}) vs "
                    f"'{player2_name}' (ID: {player2_id})"
                )
        
        # Insert prediction
        cur.execute("""
            INSERT INTO predictions (
                prediction_date, player1_id, player2_id,
                player1_rank, player2_rank,
                tournament_name, tournament_round, surface, tour_type,
                match_datetime, predicted_winner_id, matchstat_url,
                raw_prediction_text, prediction_summary
            ) VALUES (
                CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (matchstat_url) DO NOTHING
            RETURNING id
        """, (
            player1_id, player2_id, player1_rank, player2_rank,
            tournament_name, tournament_round, surface, tour_type,
            match_datetime, predicted_winner_id, matchstat_url,
            raw_prediction_text,
            Json(prediction_summary) if prediction_summary else None
        ))
        
        result = cur.fetchone()
        conn.commit()
        
        if result:
            prediction_id = result[0]
            logger.info(
                f"✓ Saved prediction {prediction_id}: "
                f"{player1_name} vs {player2_name} → {predicted_winner_name}"
            )
            return prediction_id
        else:
            logger.info(f"⊘ Prediction already exists: {matchstat_url}")
            return None
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving prediction: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


# ═══════════════════════════════════════════════════════════
# ODDS OPERATIONS
# ═══════════════════════════════════════════════════════════

def save_odds_snapshot(
    prediction_id: int,
    bookmaker: str,
    player1_odds: float,
    player2_odds: float,
    odds_type: str = 'prediction_time',
    hours_before_match: float = None
) -> None:
    """
    Save odds snapshot for a prediction
    
    Args:
        prediction_id: Reference to prediction
        bookmaker: Bookmaker name (e.g., "Pinnacle", "Bet365")
        player1_odds: Decimal odds for player 1
        player2_odds: Decimal odds for player 2
        odds_type: 'prediction_time', 'closing', or 'live_update'
        hours_before_match: Hours until match starts
    
    Raises:
        Exception: Database errors
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO odds_snapshots (
                prediction_id, bookmaker, player1_odds, player2_odds,
                odds_type, hours_before_match
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (prediction_id, bookmaker, odds_type) DO UPDATE
            SET player1_odds = EXCLUDED.player1_odds,
                player2_odds = EXCLUDED.player2_odds,
                captured_at = NOW(),
                hours_before_match = EXCLUDED.hours_before_match
        """, (
            prediction_id, bookmaker, player1_odds, player2_odds,
            odds_type, hours_before_match
        ))
        
        conn.commit()
        logger.info(
            f"✓ Saved {odds_type} odds for prediction {prediction_id}: "
            f"{player1_odds} / {player2_odds} ({bookmaker})"
        )
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving odds: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


# ═══════════════════════════════════════════════════════════
# RESULTS OPERATIONS
# ═══════════════════════════════════════════════════════════

def get_matches_needing_results(days_ago: int = 2) -> List[Dict[str, Any]]:
    """
    Get matches from N days ago that need results
    
    Args:
        days_ago: How many days ago to check (default: 2)
    
    Returns:
        List of dicts with match info:
            - id: prediction_id
            - player1_name: str
            - player2_name: str
            - match_datetime: datetime
            - matchstat_url: str
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                p.id,
                p1.canonical_name as player1_name,
                p2.canonical_name as player2_name,
                p.match_datetime,
                p.matchstat_url,
                p.tournament_name
            FROM predictions p
            JOIN players p1 ON p.player1_id = p1.id
            JOIN players p2 ON p.player2_id = p2.id
            WHERE DATE(p.match_datetime) = CURRENT_DATE - INTERVAL '%s days'
              AND p.actual_winner_id IS NULL
              AND p.match_status = 'scheduled'
            ORDER BY p.match_datetime
        """, (days_ago,))
        
        matches = cur.fetchall()
        logger.info(f"Found {len(matches)} matches from {days_ago} days ago needing results")
        return matches
        
    finally:
        cur.close()
        release_connection(conn)


def update_match_result(
    prediction_id: int,
    actual_winner_name: str,
    match_score: str,
    match_status: str = 'completed'
) -> None:
    """
    Update prediction with match result and calculate ROI
    
    Args:
        prediction_id: Prediction to update
        actual_winner_name: Name of actual winner
        match_score: Match score (e.g., "6-4, 6-3")
        match_status: 'completed', 'walkover', or 'retired'
    
    Raises:
        Exception: Database errors
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get prediction details
        cur.execute("""
            SELECT 
                p.predicted_winner_id,
                p1.canonical_name as player1_name,
                p.player1_id,
                p.player2_id
            FROM predictions p
            JOIN players p1 ON p.player1_id = p1.id
            WHERE p.id = %s
        """, (prediction_id,))
        
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Prediction {prediction_id} not found")
        
        predicted_winner_id, player1_name, player1_id, player2_id = result
        
        # Get/create actual winner ID
        actual_winner_id = get_or_create_player(actual_winner_name)
        
        # Validate winner is one of the players
        if actual_winner_id not in [player1_id, player2_id]:
            # Try fuzzy match
            cur.execute("""
                SELECT p1.canonical_name, p2.canonical_name
                FROM predictions p
                JOIN players p1 ON p.player1_id = p1.id
                JOIN players p2 ON p.player2_id = p2.id
                WHERE p.id = %s
            """, (prediction_id,))
            
            p1_name, p2_name = cur.fetchone()
            
            if fuzzy_match_player(actual_winner_name, p1_name):
                actual_winner_id = player1_id
            elif fuzzy_match_player(actual_winner_name, p2_name):
                actual_winner_id = player2_id
            else:
                logger.warning(
                    f"Winner '{actual_winner_name}' doesn't match players "
                    f"in prediction {prediction_id}: {p1_name} vs {p2_name}"
                )
        
        # Check if prediction correct
        prediction_correct = (predicted_winner_id == actual_winner_id)
        
        # Calculate ROI using prediction-time odds
        roi_prediction = calculate_roi(
            prediction_id, predicted_winner_id, actual_winner_id,
            odds_type='prediction_time'
        )
        
        # Calculate ROI using closing odds (if available)
        roi_closing = calculate_roi(
            prediction_id, predicted_winner_id, actual_winner_id,
            odds_type='closing'
        )
        
        # Update prediction
        cur.execute("""
            UPDATE predictions
            SET actual_winner_id = %s,
                match_score = %s,
                match_status = %s,
                prediction_correct = %s,
                roi_prediction_odds = %s,
                roi_closing_odds = %s,
                result_scraped_at = NOW()
            WHERE id = %s
        """, (
            actual_winner_id, match_score, match_status,
            prediction_correct, roi_prediction, roi_closing,
            prediction_id
        ))
        
        conn.commit()
        
        status_emoji = "✓" if prediction_correct else "✗"
        logger.info(
            f"{status_emoji} Updated result for prediction {prediction_id}: "
            f"{'CORRECT' if prediction_correct else 'WRONG'} "
            f"(ROI: {roi_prediction:.2f} KSH)"
        )
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating result for prediction {prediction_id}: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


def calculate_roi(
    prediction_id: int,
    predicted_winner_id: int,
    actual_winner_id: int,
    odds_type: str = 'prediction_time'
) -> Optional[float]:
    """
    Calculate ROI for a prediction
    
    Args:
        prediction_id: Prediction ID
        predicted_winner_id: ID of predicted winner
        actual_winner_id: ID of actual winner
        odds_type: 'prediction_time' or 'closing'
    
    Returns:
        float: ROI in KSH (profit/loss for 10 KSH bet)
        None: If no odds found
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get odds
        cur.execute("""
            SELECT player1_odds, player2_odds
            FROM odds_snapshots
            WHERE prediction_id = %s AND odds_type = %s
            ORDER BY captured_at DESC
            LIMIT 1
        """, (prediction_id, odds_type))
        
        odds_row = cur.fetchone()
        
        if not odds_row:
            logger.debug(f"No {odds_type} odds found for prediction {prediction_id}")
            return None
        
        player1_odds, player2_odds = odds_row
        
        # Get player IDs
        cur.execute("""
            SELECT player1_id, player2_id
            FROM predictions
            WHERE id = %s
        """, (prediction_id,))
        
        player1_id, player2_id = cur.fetchone()
        
        # Determine predicted odds
        if predicted_winner_id == player1_id:
            predicted_odds = player1_odds
        elif predicted_winner_id == player2_id:
            predicted_odds = player2_odds
        else:
            logger.error(f"Predicted winner {predicted_winner_id} not in match")
            return None
        
        # Calculate ROI
        BET_AMOUNT = 10.0  # KSH
        
        if predicted_winner_id == actual_winner_id:
            # Win: profit = (odds * bet) - bet
            roi = (predicted_odds * BET_AMOUNT) - BET_AMOUNT
        else:
            # Loss: lose entire bet
            roi = -BET_AMOUNT
        
        return round(roi, 2)
        
    finally:
        cur.close()
        release_connection(conn)


# ═══════════════════════════════════════════════════════════
# LOGGING OPERATIONS
# ═══════════════════════════════════════════════════════════

def log_scrape(
    scrape_type: str,
    matches_found: int = 0,
    matches_saved: int = 0,
    matches_failed: int = 0,
    errors: str = None,
    status: str = 'success',
    execution_time: float = None,
    pages_scraped: int = 0
) -> None:
    """
    Log scrape execution to database
    
    Args:
        scrape_type: 'predictions', 'results', 'closing_odds'
        matches_found: Total matches found
        matches_saved: Successfully saved
        matches_failed: Failed to save
        errors: Error messages (concatenated)
        status: 'success', 'partial', 'failed'
        execution_time: Seconds taken
        pages_scraped: Number of pages scraped
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO scrape_logs (
                scrape_type, matches_found, matches_saved, matches_failed,
                errors, status, execution_time_seconds, pages_scraped
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            scrape_type, matches_found, matches_saved, matches_failed,
            errors, status, execution_time, pages_scraped
        ))
        conn.commit()
        logger.debug(f"Logged {scrape_type} scrape: {status}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to log scrape: {e}")
        # Don't raise - logging failure shouldn't crash scraper
        
    finally:
        cur.close()
        release_connection(conn)


# ═══════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════

def test_connection() -> bool:
    """
    Test database connection
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ Database connected!")
        print(f"PostgreSQL version: {version}")
        
        cur.execute("SELECT COUNT(*) FROM predictions")
        count = cur.fetchone()[0]
        print(f"Total predictions in database: {count}")
        
        cur.close()
        release_connection(conn)
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def get_statistics() -> Dict[str, Any]:
    """
    Get database statistics
    
    Returns:
        dict: Statistics about scraped data
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        stats = {}
        
        # Total predictions
        cur.execute("SELECT COUNT(*) as total FROM predictions")
        stats['total_predictions'] = cur.fetchone()['total']
        
        # Predictions with results
        cur.execute("SELECT COUNT(*) as total FROM predictions WHERE actual_winner_id IS NOT NULL")
        stats['predictions_with_results'] = cur.fetchone()['total']
        
        # Prediction accuracy
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
        """)
        result = cur.fetchone()
        if result['total'] > 0:
            stats['accuracy'] = round((result['correct'] / result['total']) * 100, 2)
        else:
            stats['accuracy'] = 0
        
        # Total players
        cur.execute("SELECT COUNT(*) as total FROM players")
        stats['total_players'] = cur.fetchone()['total']
        
        # Recent scrapes
        cur.execute("""
            SELECT scrape_type, status, scrape_timestamp
            FROM scrape_logs
            ORDER BY scrape_timestamp DESC
            LIMIT 5
        """)
        stats['recent_scrapes'] = cur.fetchall()
        
        return stats
        
    finally:
        cur.close()
        release_connection(conn)
```

---

### **File: src/scrapers/__init__.py**

```python
"""
Scraper modules for Matchstat tennis prediction system
"""
```

---

**This completes the database and utility modules. The file is getting long, so I'll continue with the scraper implementations in PART 3.**

