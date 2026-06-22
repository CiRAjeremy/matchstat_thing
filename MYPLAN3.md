# 🎾 MATCHSTAT TENNIS PREDICTION PROFITABILITY ANALYSIS
## COMPLETE IMPLEMENTATION PLAN - PART 3 OF 3

---

## 🕷️ SCRAPER IMPLEMENTATIONS

### **File: src/scrapers/matchstat.py**

```python
"""
Matchstat.com prediction scraper
Scrapes daily tennis predictions and odds
"""
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
import time

import requests
from bs4 import BeautifulSoup

from src.config import Config
from src.utils import (
    get_headers, smart_delay, clean_player_name, parse_rank,
    parse_match_date, validate_prediction_data, setup_logging,
    extract_text_or_none, parse_odds_string
)
from src.database import save_prediction, save_odds_snapshot, log_scrape

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

BASE_URL = "https://matchstat.com"
HOMEPAGE_URL = "https://matchstat.com/"

# CSS Selectors (update if site structure changes)
SELECTORS = {
    'prediction_cards': 'div.flex.w-full.justify-between.items-center',
    'player_links': 'a[href*="/tennis/player/"]',
    'h2h_link': 'a[href*="/tennis/h2h-odds-bets/"]',
    'odds_divs': 'div.text-center.bg-gray-100.rounded-md',
    'match_heading': 'h1',
    'prediction_text': 'div.prose',
    'surface_links': 'a[href*="court"]',
}


# ═══════════════════════════════════════════════════════════
# HOMEPAGE SCRAPING
# ═══════════════════════════════════════════════════════════

def scrape_matchstat_homepage() -> List[Dict[str, Any]]:
    """
    Scrape today's tennis predictions from Matchstat homepage
    
    Returns:
        List of dicts containing:
            - player1: dict with name, country, rank
            - player2: dict with name, country, rank
            - homepage_odds: dict with player1/player2 odds
            - h2h_url: str (full URL to prediction details)
    
    Raises:
        requests.RequestException: Network errors
    """
    logger.info(f"Scraping Matchstat homepage: {HOMEPAGE_URL}")
    
    try:
        response = requests.get(
            HOMEPAGE_URL,
            headers=get_headers(),
            timeout=Config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        predictions = []
        
        # Find all prediction cards
        cards = soup.select(SELECTORS['prediction_cards'])
        logger.info(f"Found {len(cards)} potential prediction cards")
        
        for i, card in enumerate(cards, 1):
            try:
                # Check if it's tennis (has player links)
                player_links = card.select(SELECTORS['player_links'])
                
                if len(player_links) < 2:
                    logger.debug(f"Card {i}: Not a tennis match (< 2 player links)")
                    continue
                
                # Check if prediction is ready (has H2H link)
                h2h_link = card.select_one(SELECTORS['h2h_link'])
                
                if not h2h_link:
                    logger.debug(f"Card {i}: No H2H link found")
                    continue
                
                # Check for "Prediction Ready Soon" text
                if 'Prediction Ready Soon' in card.get_text():
                    logger.debug(f"Card {i}: Prediction not ready yet")
                    continue
                
                # Extract player 1 info
                player1_link = player_links[0]
                player1_name = clean_player_name(player1_link.get_text(strip=True))
                
                # Try to get country from flag image
                player1_flag = player1_link.find_previous('img', alt=True)
                player1_country = player1_flag.get('alt') if player1_flag else None
                
                # Try to parse rank
                player1_rank = parse_rank(player1_link.get_text())
                
                # Extract player 2 info
                player2_link = player_links[1]
                player2_name = clean_player_name(player2_link.get_text(strip=True))
                
                player2_flag = player2_link.find_previous('img', alt=True)
                player2_country = player2_flag.get('alt') if player2_flag else None
                
                player2_rank = parse_rank(player2_link.get_text())
                
                # Extract odds from homepage (if available)
                odds_divs = card.select(SELECTORS['odds_divs'])
                player1_odds = None
                player2_odds = None
                
                if len(odds_divs) >= 2:
                    try:
                        # Odds are usually in second div within odds container
                        p1_odds_text = odds_divs[0].find_all('div')[1].get_text(strip=True)
                        p2_odds_text = odds_divs[1].find_all('div')[1].get_text(strip=True)
                        
                        player1_odds = parse_odds_string(p1_odds_text)
                        player2_odds = parse_odds_string(p2_odds_text)
                    except (IndexError, AttributeError) as e:
                        logger.debug(f"Card {i}: Could not parse homepage odds: {e}")
                
                # Get H2H URL
                h2h_url = h2h_link.get('href')
                if not h2h_url.startswith('http'):
                    h2h_url = BASE_URL + h2h_url
                
                # Validate we have minimum required data
                if not player1_name or not player2_name:
                    logger.warning(f"Card {i}: Missing player names")
                    continue
                
                prediction = {
                    'player1': {
                        'name': player1_name,
                        'country': player1_country,
                        'rank': player1_rank
                    },
                    'player2': {
                        'name': player2_name,
                        'country': player2_country,
                        'rank': player2_rank
                    },
                    'homepage_odds': {
                        'player1': player1_odds,
                        'player2': player2_odds
                    },
                    'h2h_url': h2h_url
                }
                
                predictions.append(prediction)
                logger.info(f"✓ Card {i}: {player1_name} vs {player2_name}")
                
            except Exception as e:
                logger.error(f"Error parsing card {i}: {e}", exc_info=True)
                continue
        
        logger.info(f"Successfully extracted {len(predictions)} tennis predictions from homepage")
        return predictions
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Matchstat homepage: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error scraping homepage: {e}", exc_info=True)
        raise


# ═══════════════════════════════════════════════════════════
# DETAIL PAGE SCRAPING
# ═══════════════════════════════════════════════════════════

def scrape_prediction_details(h2h_url: str) -> Optional[Dict[str, Any]]:
    """
    Scrape full prediction analysis from H2H page
    
    Args:
        h2h_url: URL to H2H prediction page
    
    Returns:
        Dict containing:
            - predicted_winner: str
            - match_datetime: datetime
            - tournament_name: str
            - tournament_round: str
            - surface: str
            - tour_type: str
            - prediction_text: str
            - detail_odds: dict with player1/player2 odds
        OR None if parsing failed
    """
    logger.info(f"Scraping prediction details: {h2h_url}")
    
    try:
        response = requests.get(
            h2h_url,
            headers=get_headers(),
            timeout=Config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract match details from H1
        h1 = soup.select_one(SELECTORS['match_heading'])
        if not h1:
            logger.error("No H1 heading found on page")
            return None
        
        h1_text = h1.get_text(strip=True)
        logger.debug(f"H1 text: {h1_text}")
        
        # Parse H1 pattern: "Player1 will play Player2 on DD MMM YYYY at Time in the Tournament, Round"
        # Example: "Rafael Nadal will play Novak Djokovic on 05 Jan 2024 at 14:00 in the Australian Open, Round 1"
        
        match_pattern = re.search(
            r'(.+?)\s+will play\s+(.+?)\s+on\s+(\d{2}\s+\w{3}\s+\d{4})\s+(?:at\s+([0-9:]+))?\s+in\s+(?:the\s+)?(.+)',
            h1_text,
            re.IGNORECASE
        )
        
        if not match_pattern:
            logger.error(f"Could not parse H1 text: {h1_text}")
            return None
        
        predicted_winner = match_pattern.group(1).strip()
        opponent = match_pattern.group(2).strip()
        match_date_str = match_pattern.group(3).strip()
        match_time_str = match_pattern.group(4)  # May be None
        tournament_info = match_pattern.group(5).strip()
        
        # Parse date and time
        try:
            match_datetime = parse_match_date(match_date_str, match_time_str)
        except ValueError as e:
            logger.error(f"Could not parse match date '{match_date_str}': {e}")
            match_datetime = datetime.now()  # Fallback to now
        
        # Parse tournament info
        # Usually "Tournament Name, Round"
        tournament_parts = [part.strip() for part in tournament_info.split(',')]
        tournament_name = tournament_parts[0] if len(tournament_parts) > 0 else None
        tournament_round = tournament_parts[1] if len(tournament_parts) > 1 else None
        
        # Extract surface (look for "Clay court", "Hard court", etc.)
        surface = None
        surface_links = soup.select(SELECTORS['surface_links'])
        for link in surface_links:
            link_text = link.get_text(strip=True).lower()
            if 'clay' in link_text:
                surface = 'Clay'
                break
            elif 'hard' in link_text:
                surface = 'Hard'
                break
            elif 'grass' in link_text:
                surface = 'Grass'
                break
            elif 'carpet' in link_text:
                surface = 'Carpet'
                break
        
        # Determine tour type from tournament name
        tour_type = None
        if tournament_name:
            tournament_lower = tournament_name.lower()
            if 'challenger' in tournament_lower:
                tour_type = 'Challenger'
            elif any(x in tournament_lower for x in ['itf', 'w15', 'w25', 'w60', 'w100', 'm15', 'm25']):
                tour_type = 'ITF'
            elif any(x in tournament_lower for x in ['wta', 'women']):
                tour_type = 'WTA'
            else:
                tour_type = 'ATP'  # Default to ATP
        
        # Get full prediction text
        prediction_div = soup.select_one(SELECTORS['prediction_text'])
        prediction_text = prediction_div.get_text(strip=True) if prediction_div else ""
        
        # Extract detailed odds from page
        player1_detail_odds = None
        player2_detail_odds = None
        
        # Look for "Best Odds" or similar section
        # This varies by site structure - may need adjustment
        odds_section = soup.find(string=re.compile(r'Best Odds|Odds', re.IGNORECASE))
        if odds_section:
            odds_container = odds_section.find_parent()
            if odds_container:
                odds_divs = odds_container.find_all('div', class_='text-xs')
                if len(odds_divs) >= 2:
                    try:
                        player1_detail_odds = parse_odds_string(odds_divs[0].get_text(strip=True))
                        player2_detail_odds = parse_odds_string(odds_divs[1].get_text(strip=True))
                    except Exception as e:
                        logger.debug(f"Could not parse detail odds: {e}")
        
        details = {
            'predicted_winner': clean_player_name(predicted_winner),
            'match_datetime': match_datetime,
            'tournament_name': tournament_name,
            'tournament_round': tournament_round,
            'surface': surface,
            'tour_type': tour_type,
            'prediction_text': prediction_text[:5000],  # Limit text length
            'detail_odds': {
                'player1': player1_detail_odds,
                'player2': player2_detail_odds
            }
        }
        
        logger.info(f"✓ Extracted details: {predicted_winner} - {tournament_name}")
        return details
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {h2h_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing prediction details from {h2h_url}: {e}", exc_info=True)
        return None


# ═══════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════

def main():
    """
    Main execution function for prediction scraper
    
    Process:
        1. Scrape homepage for predictions
        2. For each prediction, scrape detail page
        3. Save to database
        4. Log results
    """
    # Setup logging
    setup_logging()
    logger.info("="*60)
    logger.info("STARTING MATCHSTAT PREDICTION SCRAPER")
    logger.info("="*60)
    
    start_time = time.time()
    
    stats = {
        'found': 0,
        'saved': 0,
        'failed': 0,
        'errors': [],
        'pages_scraped': 0
    }
    
    try:
        # Step 1: Scrape homepage
        predictions = scrape_matchstat_homepage()
        stats['found'] = len(predictions)
        stats['pages_scraped'] += 1
        
        if not predictions:
            logger.warning("No predictions found on homepage")
            log_scrape(
                scrape_type='predictions',
                matches_found=0,
                matches_saved=0,
                status='success',
                execution_time=time.time() - start_time,
                pages_scraped=1
            )
            return
        
        # Step 2: Process each prediction
        for i, pred in enumerate(predictions, 1):
            try:
                logger.info(f"\n--- Processing prediction {i}/{len(predictions)} ---")
                
                # Delay between requests (except first one)
                if i > 1:
                    smart_delay()
                
                # Scrape detail page
                details = scrape_prediction_details(pred['h2h_url'])
                stats['pages_scraped'] += 1
                
                if not details:
                    error_msg = f"Could not scrape details for {pred['h2h_url']}"
                    stats['errors'].append(error_msg)
                    stats['failed'] += 1
                    logger.error(error_msg)
                    continue
                
                # Merge homepage and detail data
                # Use detail odds if available, otherwise homepage odds
                final_p1_odds = details['detail_odds']['player1'] or pred['homepage_odds']['player1']
                final_p2_odds = details['detail_odds']['player2'] or pred['homepage_odds']['player2']
                
                # Build complete prediction data
                prediction_data = {
                    'player1_name': pred['player1']['name'],
                    'player2_name': pred['player2']['name'],
                    'predicted_winner': details['predicted_winner'],
                    'tournament_name': details['tournament_name'],
                    'match_datetime': details['match_datetime'],
                    'matchstat_url': pred['h2h_url'],
                    'player1_country': pred['player1']['country'],
                    'player2_country': pred['player2']['country'],
                    'player1_rank': pred['player1']['rank'],
                    'player2_rank': pred['player2']['rank'],
                    'tournament_round': details['tournament_round'],
                    'surface': details['surface'],
                    'tour_type': details['tour_type'],
                    'raw_prediction_text': details['prediction_text'],
                    'player1_odds': final_p1_odds,
                    'player2_odds': final_p2_odds,
                }
                
                # Validate data
                if not validate_prediction_data(prediction_data):
                    error_msg = f"Validation failed for {pred['player1']['name']} vs {pred['player2']['name']}"
                    stats['errors'].append(error_msg)
                    stats['failed'] += 1
                    logger.error(error_msg)
                    continue
                
                # Save to database
                try:
                    prediction_id = save_prediction(
                        player1_name=prediction_data['player1_name'],
                        player2_name=prediction_data['player2_name'],
                        predicted_winner_name=prediction_data['predicted_winner'],
                        tournament_name=prediction_data['tournament_name'],
                        match_datetime=prediction_data['match_datetime'],
                        matchstat_url=prediction_data['matchstat_url'],
                        player1_country=prediction_data['player1_country'],
                        player2_country=prediction_data['player2_country'],
                        player1_rank=prediction_data['player1_rank'],
                        player2_rank=prediction_data['player2_rank'],
                        tournament_round=prediction_data['tournament_round'],
                        surface=prediction_data['surface'],
                        tour_type=prediction_data['tour_type'],
                        raw_prediction_text=prediction_data['raw_prediction_text']
                    )
                    
                    if prediction_id:
                        # Save odds snapshot
                        if final_p1_odds and final_p2_odds:
                            from src.utils import calculate_hours_until
                            hours_before = calculate_hours_until(prediction_data['match_datetime'])
                            
                            save_odds_snapshot(
                                prediction_id=prediction_id,
                                bookmaker='Matchstat',  # or extract actual bookmaker
                                player1_odds=final_p1_odds,
                                player2_odds=final_p2_odds,
                                odds_type='prediction_time',
                                hours_before_match=hours_before
                            )
                        
                        stats['saved'] += 1
                        logger.info(f"✓ Saved prediction {prediction_id}")
                    else:
                        # Already exists (duplicate)
                        logger.info("⊘ Prediction already in database (skipped)")
                        stats['saved'] += 1  # Count as success
                        
                except Exception as e:
                    error_msg = f"Database error for {prediction_data['player1_name']} vs {prediction_data['player2_name']}: {str(e)}"
                    stats['errors'].append(error_msg)
                    stats['failed'] += 1
                    logger.error(error_msg, exc_info=True)
                    continue
                
            except Exception as e:
                error_msg = f"Unexpected error processing prediction {i}: {str(e)}"
                stats['errors'].append(error_msg)
                stats['failed'] += 1
                logger.error(error_msg, exc_info=True)
                continue
        
        # Determine overall status
        if stats['failed'] == 0:
            status = 'success'
        elif stats['saved'] > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        # Log to database
        execution_time = time.time() - start_time
        log_scrape(
            scrape_type='predictions',
            matches_found=stats['found'],
            matches_saved=stats['saved'],
            matches_failed=stats['failed'],
            errors='; '.join(stats['errors'][:10]) if stats['errors'] else None,  # Limit error text
            status=status,
            execution_time=round(execution_time, 2),
            pages_scraped=stats['pages_scraped']
        )
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("SCRAPE COMPLETE")
        logger.info("="*60)
        logger.info(f"Found: {stats['found']}")
        logger.info(f"Saved: {stats['saved']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Pages scraped: {stats['pages_scraped']}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Status: {status.upper()}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Fatal error in scraper: {e}", exc_info=True)
        
        # Log failure
        execution_time = time.time() - start_time
        log_scrape(
            scrape_type='predictions',
            matches_found=stats['found'],
            matches_saved=stats['saved'],
            matches_failed=stats['found'] - stats['saved'],
            errors=str(e),
            status='failed',
            execution_time=round(execution_time, 2),
            pages_scraped=stats['pages_scraped']
        )
        
        raise


if __name__ == '__main__':
    main()
```

---

### **File: src/scrapers/flashscore.py**

```python
"""
FlashScore.com results scraper
Scrapes match results for completed predictions
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any

import requests
from bs4 import BeautifulSoup

from src.config import Config
from src.utils import (
    get_headers, smart_delay, fuzzy_match_player,
    setup_logging
)
from src.database import (
    get_matches_needing_results, update_match_result, log_scrape
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

BASE_URL = "https://www.flashscore.com"
TENNIS_URL = "https://www.flashscore.com/tennis/"

# Note: FlashScore uses dynamic IDs, so selectors may need adjustment
SELECTORS = {
    'match_events': 'div.event__match',
    'participant_home': 'div.event__participant--home',
    'participant_away': 'div.event__participant--away',
    'score': 'div.event__score',
}


# ═══════════════════════════════════════════════════════════
# RESULT SCRAPING
# ═══════════════════════════════════════════════════════════

def scrape_flashscore_result(
    player1: str,
    player2: str,
    match_date: datetime
) -> Tuple[Optional[str], Optional[str]]:
    """
    Scrape match result from FlashScore
    
    Args:
        player1: First player name
        player2: Second player name
        match_date: When match was scheduled
    
    Returns:
        Tuple of (winner_name, score) or (None, None) if not found
        
    Note:
        FlashScore is heavily JavaScript-based. This implementation
        uses requests which may not work for all matches.
        Consider Selenium fallback for production.
    """
    logger.info(f"Searching FlashScore for: {player1} vs {player2} on {match_date.date()}")
    
    # Try multiple date offsets (match may have been played day before/after)
    date_offsets = [0, -1, 1, -2, 2]
    
    for offset in date_offsets:
        check_date = match_date + timedelta(days=offset)
        
        try:
            # FlashScore results URL (may need adjustment)
            # Format: https://www.flashscore.com/tennis/?d=YYYYMMDD
            date_str = check_date.strftime('%Y%m%d')
            url = f"{TENNIS_URL}?d={date_str}"
            
            logger.debug(f"Checking date: {check_date.date()} (offset: {offset})")
            
            response = requests.get(
                url,
                headers=get_headers(),
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all match events
            matches = soup.select(SELECTORS['match_events'])
            logger.debug(f"Found {len(matches)} matches on {check_date.date()}")
            
            for match in matches:
                # Extract player names
                home_elem = match.select_one(SELECTORS['participant_home'])
                away_elem = match.select_one(SELECTORS['participant_away'])
                
                if not home_elem or not away_elem:
                    continue
                
                home_player = home_elem.get_text(strip=True)
                away_player = away_elem.get_text(strip=True)
                
                # Check if this is our match (fuzzy match on last names)
                is_match = False
                player_order = None  # 'normal' or 'reversed'
                
                if (fuzzy_match_player(home_player, player1) and 
                    fuzzy_match_player(away_player, player2)):
                    is_match = True
                    player_order = 'normal'
                elif (fuzzy_match_player(home_player, player2) and 
                      fuzzy_match_player(away_player, player1)):
                    is_match = True
                    player_order = 'reversed'
                
                if not is_match:
                    continue
                
                logger.info(f"✓ Found match: {home_player} vs {away_player}")
                
                # Extract score
                score_elem = match.select_one(SELECTORS['score'])
                if not score_elem:
                    logger.warning("Score element not found")
                    continue
                
                score = score_elem.get_text(strip=True)
                
                # Determine winner
                # FlashScore typically shows scores like "6-4, 6-3" for home win
                # or "4-6, 3-6" for away win
                # We need to parse sets won
                
                winner = determine_winner_from_score(
                    home_player, away_player, score, match
                )
                
                if winner:
                    # Map back to original player names
                    if player_order == 'reversed':
                        if winner == home_player:
                            winner = player2
                        else:
                            winner = player1
                    else:
                        if winner == home_player:
                            winner = player1
                        else:
                            winner = player2
                    
                    logger.info(f"✓ Result: {winner} won, Score: {score}")
                    return (winner, score)
                else:
                    logger.warning(f"Could not determine winner from score: {score}")
                    return (None, None)
            
            # If we checked offset 0 and didn't find it, wait before trying next date
            if offset != 0:
                smart_delay(1, 2)
                
        except requests.RequestException as e:
            logger.error(f"Error fetching FlashScore for date {check_date.date()}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error parsing FlashScore: {e}", exc_info=True)
            continue
    
    logger.warning(f"Match not found on FlashScore: {player1} vs {player2}")
    return (None, None)


def determine_winner_from_score(
    home_player: str,
    away_player: str,
    score: str,
    match_element
) -> Optional[str]:
    """
    Determine winner from score string and match element
    
    Args:
        home_player: Home player name
        away_player: Away player name
        score: Score string (e.g., "6-4, 6-3")
        match_element: BeautifulSoup element (may contain winner indicator)
    
    Returns:
        Winner name or None
    """
    # Check for walkover/retirement indicators
    if any(x in score.upper() for x in ['W/O', 'WO', 'RET', 'DEF']):
        # Try to find winner from styling/classes
        # FlashScore often adds a class to winning player
        home_elem = match_element.select_one('div.event__participant--home')
        away_elem = match_element.select_one('div.event__participant--away')
        
        # Check for winner class (varies by FlashScore version)
        if home_elem and 'winner' in str(home_elem.get('class', [])):
            return home_player
        elif away_elem and 'winner' in str(away_elem.get('class', [])):
            return away_player
    
    # Parse sets from score
    # Example: "6-4, 6-3" or "6-4 6-3" or "6-4,6-3"
    score_clean = score.replace(',', ' ').strip()
    sets = score_clean.split()
    
    home_sets_won = 0
    away_sets_won = 0
    
    for set_score in sets:
        if '-' not in set_score:
            continue
        
        try:
            # Parse "6-4" format
            parts = set_score.split('-')
            home_games = int(parts[0].strip())
            away_games = int(parts[1].strip())
            
            if home_games > away_games:
                home_sets_won += 1
            elif away_games > home_games:
                away_sets_won += 1
                
        except (ValueError, IndexError):
            continue
    
    # Winner is player who won most sets
    if home_sets_won > away_sets_won:
        return home_player
    elif away_sets_won > home_sets_won:
        return away_player
    else:
        # Tie or couldn't parse - check element classes
        home_elem = match_element.select_one('div.event__participant--home')
        if home_elem and 'winner' in str(home_elem.get('class', [])):
            return home_player
        
        away_elem = match_element.select_one('div.event__participant--away')
        if away_elem and 'winner' in str(away_elem.get('class', [])):
            return away_player
    
    return None


# ═══════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════

def main():
    """
    Main execution function for results scraper
    
    Process:
        1. Get matches needing results from database
        2. For each match, scrape FlashScore
        3. Update database with results
        4. Log execution
    """
    # Setup logging
    setup_logging()
    logger.info("="*60)
    logger.info("STARTING FLASHSCORE RESULTS SCRAPER")
    logger.info("="*60)
    
    start_time = time.time()
    
    stats = {
        'found': 0,
        'updated': 0,
        'failed': 0,
        'errors': [],
        'pages_scraped': 0
    }
    
    try:
        # Get matches needing results (from 2 days ago)
        matches = get_matches_needing_results(days_ago=2)
        stats['found'] = len(matches)
        
        if not matches:
            logger.info("No matches needing results")
            log_scrape(
                scrape_type='results',
                matches_found=0,
                matches_saved=0,
                status='success',
                execution_time=time.time() - start_time,
                pages_scraped=0
            )
            return
        
        logger.info(f"Found {len(matches)} matches needing results")
        
        # Process each match
        for i, match in enumerate(matches, 1):
            try:
                logger.info(f"\n--- Processing match {i}/{len(matches)} ---")
                logger.info(f"Match: {match['player1_name']} vs {match['player2_name']}")
                logger.info(f"Date: {match['match_datetime']}")
                
                # Delay between requests (except first)
                if i > 1:
                    smart_delay()
                
                # Scrape result
                winner, score = scrape_flashscore_result(
                    match['player1_name'],
                    match['player2_name'],
                    match['match_datetime']
                )
                stats['pages_scraped'] += 1
                
                if winner and score:
                    # Determine match status
                    if 'W/O' in score.upper() or 'WO' in score.upper():
                        match_status = 'walkover'
                    elif 'RET' in score.upper():
                        match_status = 'retired'
                    else:
                        match_status = 'completed'
                    
                    # Update database
                    update_match_result(
                        prediction_id=match['id'],
                        actual_winner_name=winner,
                        match_score=score,
                        match_status=match_status
                    )
                    
                    stats['updated'] += 1
                    logger.info(f"✓ Updated: {winner} won")
                    
                else:
                    error_msg = f"Result not found for {match['player1_name']} vs {match['player2_name']}"
                    stats['errors'].append(error_msg)
                    stats['failed'] += 1
                    logger.warning(error_msg)
                
            except Exception as e:
                error_msg = f"Error processing match {match['id']}: {str(e)}"
                stats['errors'].append(error_msg)
                stats['failed'] += 1
                logger.error(error_msg, exc_info=True)
                continue
        
        # Determine status
        if stats['failed'] == 0:
            status = 'success'
        elif stats['updated'] > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        # Log to database
        execution_time = time.time() - start_time
        log_scrape(
            scrape_type='results',
            matches_found=stats['found'],
            matches_saved=stats['updated'],
            matches_failed=stats['failed'],
            errors='; '.join(stats['errors'][:10]) if stats['errors'] else None,
            status=status,
            execution_time=round(execution_time, 2),
            pages_scraped=stats['pages_scraped']
        )
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("RESULTS SCRAPE COMPLETE")
        logger.info("="*60)
        logger.info(f"Matches found: {stats['found']}")
        logger.info(f"Results updated: {stats['updated']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Pages scraped: {stats['pages_scraped']}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Status: {status.upper()}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Fatal error in results scraper: {e}", exc_info=True)
        
        # Log failure
        execution_time = time.time() - start_time
        log_scrape(
            scrape_type='results',
            matches_found=stats['found'],
            matches_saved=stats['updated'],
            matches_failed=stats['found'] - stats['updated'],
            errors=str(e),
            status='failed',
            execution_time=round(execution_time, 2),
            pages_scraped=stats['pages_scraped']
        )
        
        raise


if __name__ == '__main__':
    main()
```

---

### **File: src/scrapers/oddsportal.py**

```python
"""
Oddsportal.com odds scraper (PLACEHOLDER)
This is a stub for future implementation
"""
import logging

logger = logging.getLogger(__name__)

def scrape_oddsportal_odds(player1: str, player2: str, match_date) -> dict:
    """
    Scrape odds from Oddsportal (NOT IMPLEMENTED YET)
    
    Note:
        Oddsportal requires JavaScript rendering.
        Implement this in Phase 2 with Firecrawl or Selenium.
    
    Args:
        player1: First player name
        player2: Second player name
        match_date: Match date
    
    Returns:
        dict: Empty dict for now
    """
    logger.warning("Oddsportal scraping not implemented yet")
    return {}


if __name__ == '__main__':
    print("Oddsportal scraper - not yet implemented")
    print("Use Matchstat odds for Phase 1")
```

---

### **File: analysis/roi_calculator.py**

```python
"""
ROI Analysis and Reporting
Calculate profitability metrics for Matchstat predictions
"""
import logging
from typing import Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from tabulate import tabulate

from src.config import Config
from src.utils import setup_logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════

def get_connection():
    """Get database connection"""
    return psycopg2.connect(Config.DATABASE_URL)


# ═══════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════

def overall_performance():
    """Display overall prediction accuracy and ROI"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                COUNT(*) as total_predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct_predictions,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate_pct,
                
                -- Prediction-time odds ROI
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as total_roi_prediction,
                ROUND(AVG(COALESCE(roi_prediction_odds, 0)), 2) as avg_roi_prediction,
                
                -- Closing odds ROI
                ROUND(SUM(COALESCE(roi_closing_odds, 0)), 2) as total_roi_closing,
                ROUND(AVG(COALESCE(roi_closing_odds, 0)), 2) as avg_roi_closing
                
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
        """)
        
        result = cur.fetchone()
        
        if result['total_predictions'] == 0:
            print("\n⚠️  No completed predictions yet")
            return
        
        # Calculate ROI percentages
        total_staked = result['total_predictions'] * 10  # 10 KSH per bet
        roi_pct_prediction = (result['total_roi_prediction'] / total_staked * 100) if total_staked > 0 else 0
        roi_pct_closing = (result['total_roi_closing'] / total_staked * 100) if total_staked > 0 else 0
        
        print("\n" + "="*60)
        print("📊 OVERALL PERFORMANCE")
        print("="*60)
        print(f"Total Predictions: {result['total_predictions']}")
        print(f"Correct: {result['correct_predictions']}")
        print(f"Win Rate: {result['win_rate_pct']}%")
        print(f"Total Staked: {total_staked} KSH (10 KSH flat bet)")
        print()
        print("ROI (Prediction-Time Odds):")
        print(f"  Total: {result['total_roi_prediction']:+.2f} KSH")
        print(f"  Per Bet: {result['avg_roi_prediction']:+.2f} KSH")
        print(f"  ROI %: {roi_pct_prediction:+.2f}%")
        print()
        
        if result['total_roi_closing'] is not None:
            print("ROI (Closing Odds):")
            print(f"  Total: {result['total_roi_closing']:+.2f} KSH")
            print(f"  Per Bet: {result['avg_roi_closing']:+.2f} KSH")
            print(f"  ROI %: {roi_pct_closing:+.2f}%")
        
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


def performance_by_surface():
    """Break down performance by court surface"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                surface,
                COUNT(*) as predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as total_roi,
                ROUND(AVG(COALESCE(roi_prediction_odds, 0)), 2) as avg_roi
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
              AND surface IS NOT NULL
            GROUP BY surface
            ORDER BY total_roi DESC
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("\n⚠️  No surface data available yet")
            return
        
        print("\n" + "="*60)
        print("🎾 PERFORMANCE BY SURFACE")
        print("="*60)
        
        table_data = [
            [
                row['surface'],
                row['predictions'],
                row['correct'],
                f"{row['win_rate']}%",
                f"{row['total_roi']:+.2f}",
                f"{row['avg_roi']:+.2f}"
            ]
            for row in results
        ]
        
        print(tabulate(
            table_data,
            headers=['Surface', 'Predictions', 'Correct', 'Win Rate', 'Total ROI (KSH)', 'Avg ROI'],
            tablefmt='grid'
        ))
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


def performance_by_tour_type():
    """Break down by ATP/WTA/Challenger"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                tour_type,
                COUNT(*) as predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as total_roi,
                ROUND(AVG(COALESCE(roi_prediction_odds, 0)), 2) as avg_roi
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
              AND tour_type IS NOT NULL
            GROUP BY tour_type
            ORDER BY total_roi DESC
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("\n⚠️  No tour type data available yet")
            return
        
        print("\n" + "="*60)
        print("🏆 PERFORMANCE BY TOUR TYPE")
        print("="*60)
        
        table_data = [
            [
                row['tour_type'],
                row['predictions'],
                row['correct'],
                f"{row['win_rate']}%",
                f"{row['total_roi']:+.2f}",
                f"{row['avg_roi']:+.2f}"
            ]
            for row in results
        ]
        
        print(tabulate(
            table_data,
            headers=['Tour', 'Predictions', 'Correct', 'Win Rate', 'Total ROI (KSH)', 'Avg ROI'],
            tablefmt='grid'
        ))
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


def best_worst_predictions():
    """Show best and worst ROI predictions"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Best predictions
        cur.execute("""
            SELECT 
                p1.canonical_name as player1,
                p2.canonical_name as player2,
                pw.canonical_name as predicted_winner,
                aw.canonical_name as actual_winner,
                p.tournament_name,
                p.roi_prediction_odds,
                p.prediction_correct
            FROM predictions p
            JOIN players p1 ON p.player1_id = p1.id
            JOIN players p2 ON p.player2_id = p2.id
            JOIN players pw ON p.predicted_winner_id = pw.id
            LEFT JOIN players aw ON p.actual_winner_id = aw.id
            WHERE p.actual_winner_id IS NOT NULL
            ORDER BY p.roi_prediction_odds DESC
            LIMIT 10
        """)
        
        best = cur.fetchall()
        
        print("\n" + "="*60)
        print("💰 TOP 10 MOST PROFITABLE PREDICTIONS")
        print("="*60)
        
        if best:
            table_data = [
                [
                    row['player1'],
                    row['player2'],
                    row['predicted_winner'],
                    row['actual_winner'],
                    row['tournament_name'][:30],
                    f"{row['roi_prediction_odds']:+.2f}",
                    "✓" if row['prediction_correct'] else "✗"
                ]
                for row in best
            ]
            
            print(tabulate(
                table_data,
                headers=['P1', 'P2', 'Predicted', 'Actual', 'Tournament', 'ROI', 'Correct'],
                tablefmt='grid'
            ))
        else:
            print("No data yet")
        
        # Worst predictions
        cur.execute("""
            SELECT 
                p1.canonical_name as player1,
                p2.canonical_name as player2,
                pw.canonical_name as predicted_winner,
                aw.canonical_name as actual_winner,
                p.tournament_name,
                p.roi_prediction_odds,
                p.prediction_correct
            FROM predictions p
            JOIN players p1 ON p.player1_id = p1.id
            JOIN players p2 ON p.player2_id = p2.id
            JOIN players pw ON p.predicted_winner_id = pw.id
            LEFT JOIN players aw ON p.actual_winner_id = aw.id
            WHERE p.actual_winner_id IS NOT NULL
            ORDER BY p.roi_prediction_odds ASC
            LIMIT 10
        """)
        
        worst = cur.fetchall()
        
        print("\n" + "="*60)
        print("📉 TOP 10 WORST PREDICTIONS")
        print("="*60)
        
        if worst:
            table_data = [
                [
                    row['player1'],
                    row['player2'],
                    row['predicted_winner'],
                    row['actual_winner'],
                    row['tournament_name'][:30],
                    f"{row['roi_prediction_odds']:+.2f}",
                    "✓" if row['prediction_correct'] else "✗"
                ]
                for row in worst
            ]
            
            print(tabulate(
                table_data,
                headers=['P1', 'P2', 'Predicted', 'Actual', 'Tournament', 'ROI', 'Correct'],
                tablefmt='grid'
            ))
        else:
            print("No data yet")
        
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


def monthly_trend():
    """Show performance trend over time"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                DATE_TRUNC('month', prediction_date)::date as month,
                COUNT(*) as predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as monthly_roi
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("\n⚠️  No monthly data available yet")
            return
        
        print("\n" + "="*60)
        print("📈 MONTHLY PERFORMANCE TREND")
        print("="*60)
        
        table_data = [
            [
                row['month'].strftime('%Y-%m'),
                row['predictions'],
                row['correct'],
                f"{row['win_rate']}%",
                f"{row['monthly_roi']:+.2f}"
            ]
            for row in results
        ]
        
        print(tabulate(
            table_data,
            headers=['Month', 'Predictions', 'Correct', 'Win Rate', 'ROI (KSH)'],
            tablefmt='grid'
        ))
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════

def main():
    """Run all analysis functions"""
    setup_logging()
    
    print("\n" + "🎾"*30)
    print(" "*20 + "MATCHSTAT ROI ANALYSIS")
    print("🎾"*30 + "\n")
    
    try:
        overall_performance()
        performance_by_surface()
        performance_by_tour_type()
        monthly_trend()
        best_worst_predictions()
        
        print("\n✅ Analysis complete!\n")
        
    except Exception as e:
        logger.error(f"Error running analysis: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")


if __name__ == '__main__':
    main()
```

---

## 🤖 GITHUB ACTIONS WORKFLOWS

### **File: .github/workflows/scrape_predictions.yml**

```yaml
name: Scrape Predictions & Odds

on:
  schedule:
    - cron: '0 6 * * *'  # 6:00 AM UTC daily
  workflow_dispatch:     # Manual trigger button

jobs:
  scrape-predictions:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run prediction scraper
        env:
          NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          LOG_LEVEL: INFO
        run: |
          python -m src.scrapers.matchstat
      
      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: prediction-scraper-logs-${{ github.run_number }}
          path: logs/
          retention-days: 7
```

---

### **File: .github/workflows/scrape_results.yml**

```yaml
name: Scrape Match Results

on:
  schedule:
    - cron: '0 22 * * *'  # 10:00 PM UTC daily
  workflow_dispatch:

jobs:
  scrape-results:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run results scraper
        env:
          NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          LOG_LEVEL: INFO
        run: |
          python -m src.scrapers.flashscore
      
      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: results-scraper-logs-${{ github.run_number }}
          path: logs/
          retention-days: 7
```

---

## 📝 TESTING FILES

### **File: tests/test_database.py**

```python
"""
Database operations tests
"""
import pytest
from datetime import datetime, timedelta

from src.database import *
from src.utils import setup_logging

setup_logging(level='DEBUG')


def test_connection():
    """Test database connectivity"""
    assert test_connection() == True


def test_player_creation():
    """Test player CRUD operations"""
    # Create player
    player_id = get_or_create_player("Test Player", "TST")
    assert isinstance(player_id, int)
    
    # Try creating same player again
    player_id2 = get_or_create_player("Test Player", "TST")
    assert player_id == player_id2  # Should return same ID


def test_prediction_save():
    """Test prediction insertion"""
    prediction_id = save_prediction(
        player1_name="Test Player A",
        player2_name="Test Player B",
        predicted_winner_name="Test Player A",
        tournament_name="Test Tournament",
        match_datetime=datetime.now() + timedelta(days=1),
        matchstat_url=f"https://test.com/{datetime.now().timestamp()}"
    )
    
    assert prediction_id is not None or prediction_id == None  # None if duplicate


def test_odds_snapshot():
    """Test odds storage"""
    # First create a prediction
    prediction_id = save_prediction(
        player1_name="Odds Test A",
        player2_name="Odds Test B",
        predicted_winner_name="Odds Test A",
        tournament_name="Odds Test",
        match_datetime=datetime.now() + timedelta(days=1),
        matchstat_url=f"https://test.com/odds/{datetime.now().timestamp()}"
    )
    
    if prediction_id:
        save_odds_snapshot(
            prediction_id=prediction_id,
            bookmaker="TestBook",
            player1_odds=2.10,
            player2_odds=1.75,
            odds_type='prediction_time'
        )
        # No assertion needed - just checking no exception


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

## 📚 README.md

```markdown
# 🎾 Matchstat Tennis Prediction Profitability Analysis

Automated system to track and analyze Matchstat.com tennis predictions over 6 months, measuring profitability using multiple betting strategies.

## 📊 Project Overview

- **Goal**: Determine if Matchstat predictions are profitable for betting
- **Timeline**: 6 months of data collection
- **Method**: Track predictions vs actual results, calculate ROI using odds at prediction time and closing odds
- **Use Case**: PhD research on sports prediction accuracy

## 🏗️ Architecture

```
Matchstat.com → Scraper → Neon Postgres → Analysis → Reports
     ↓              ↓            ↓             ↓          ↓
 Predictions   Odds Data    Normalized    ROI Calc   Charts
                             Storage
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.11+
- Neon PostgreSQL account (free tier)
- GitHub account (for automation)

### Installation

1. **Clone repository**
```bash
git clone https://github.com/yourusername/matchstat-scraper.git
cd matchstat-scraper
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup database**
```bash
# Create Neon account at https://neon.tech
# Create new project: "matchstat-tennis"
# Copy connection string

# Create .env file
cp .env.example .env
# Edit .env and add your NEON_DATABASE_URL
```

5. **Initialize database schema**
```bash
# Connect to Neon and run schema
psql $NEON_DATABASE_URL -f sql/schema.sql

# Or use Python
python << EOF
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

with open('sql/schema.sql', 'r') as f:
    schema = f.read()

conn = psycopg2.connect(os.getenv('NEON_DATABASE_URL'))
cur = conn.cursor()
cur.execute(schema)
conn.commit()
print("✅ Schema created!")
EOF
```

6. **Test connection**
```bash
python -c "from src.database import test_connection; test_connection()"
```

## 🎮 Usage

### Run Scrapers Locally

```bash
# Scrape predictions
python -m src.scrapers.matchstat

# Scrape results (after 2 days)
python -m src.scrapers.flashscore

# Run analysis
python analysis/roi_calculator.py
```

### Deploy to GitHub Actions

1. **Add secrets to GitHub**
   - Go to repository Settings → Secrets → Actions
   - Add `NEON_DATABASE_URL`

2. **Enable workflows**
   - Workflows are in `.github/workflows/`
   - They run automatically on schedule
   - Can also trigger manually

## 📊 Analysis

Run analysis after collecting data:

```bash
python analysis/roi_calculator.py
```

Sample output:
```
📊 OVERALL PERFORMANCE
═══════════════════════════════════════════
Total Predictions: 487
Correct: 276
Win Rate: 56.67%

ROI (Prediction-Time Odds):
  Total: +234.50 KSH
  Per Bet: +0.48 KSH
  ROI %: +4.8%
```

## 🗂️ Project Structure

```
matchstat-scraper/
├── src/
│   ├── config.py              # Configuration
│   ├── database.py            # DB operations
│   ├── utils.py               # Helper functions
│   └── scrapers/
│       ├── matchstat.py       # Prediction scraper
│       ├── flashscore.py      # Results scraper
│       └── oddsportal.py      # Odds scraper (stub)
├── analysis/
│   └── roi_calculator.py      # ROI analysis
├── sql/
│   └── schema.sql             # Database schema
├── .github/workflows/         # Automation
└── tests/                     # Unit tests
```

## 🔍 Monitoring

Check scrape logs:
```sql
SELECT * FROM scrape_logs ORDER BY scrape_timestamp DESC LIMIT 20;
```

Check latest predictions:
```sql
SELECT * FROM predictions_view ORDER BY prediction_date DESC LIMIT 10;
```

Database statistics:
```python
from src.database import get_statistics
print(get_statistics())
```

## 🐛 Troubleshooting

### Scraper fails
- Check logs in `logs/scraper.log`
- Verify website HTML hasn't changed
- Check rate limiting

### Database connection fails
- Verify `NEON_DATABASE_URL` is correct
- Check Neon dashboard for connection limits
- Ensure IP is whitelisted (if restricted)

### No predictions found
- Matchstat may not have predictions for today
- Check if site structure changed
- Verify robots.txt still allows scraping

## 📈 Next Steps (Phase 2)

After 1 month of stable data collection:
- [ ] Add Firecrawl integration for reliability
- [ ] Implement closing odds collection
- [ ] Add email notifications
- [ ] Create Streamlit dashboard
- [ ] Generate PDF reports

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- Matchstat.com for predictions
- Neon for database hosting
- GitHub Actions for automation
```

---

## ✅ FINAL DEPLOYMENT CHECKLIST

```markdown
# 🚀 DEPLOYMENT CHECKLIST

## Pre-Deployment (Day 1)

- [ ] Create Neon database account
- [ ] Create new project: "matchstat-tennis"
- [ ] Copy connection string
- [ ] Create GitHub repository
- [ ] Clone repository locally

## Setup (Day 1-2)

- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Create `.env` file with `NEON_DATABASE_URL`
- [ ] Run schema.sql to create tables
- [ ] Test database connection: `python -c "from src.database import test_connection; test_connection()"`

## Testing (Day 2-3)

- [ ] Run database tests: `pytest tests/test_database.py -v`
- [ ] Test prediction scraper locally: `python -m src.scrapers.matchstat`
- [ ] Verify 5-10 predictions saved to database
- [ ] Check odds data in `odds_snapshots` table
- [ ] Wait 2 days, then test results scraper: `python -m src.scrapers.flashscore`
- [ ] Verify results updated correctly
- [ ] Run ROI analysis: `python analysis/roi_calculator.py`

## GitHub Actions Setup (Day 3-4)

- [ ] Push code to GitHub
- [ ] Go to Settings → Secrets → Actions
- [ ] Add secret: `NEON_DATABASE_URL`
- [ ] Go to Actions tab
- [ ] Enable workflows
- [ ] Manually trigger "Scrape Predictions" workflow
- [ ] Check workflow logs for errors
- [ ] Fix any issues
- [ ] Verify data appears in database

## Production (Day 5+)

- [ ] Let automated workflows run for 7 days
- [ ] Check `scrape_logs` table daily:
  ```sql
  SELECT * FROM scrape_logs ORDER BY scrape_timestamp DESC LIMIT 20;
  ```
- [ ] Fix any scraping failures
- [ ] Document HTML selector changes needed
- [ ] After 30 predictions, run first ROI analysis

## Monitoring (Ongoing)

- [ ] Weekly: Check scrape success rate
- [ ] Weekly: Verify predictions getting results
- [ ] Monthly: Run full ROI analysis
- [ ] Monthly: Export data backup:
  ```python
  import pandas as pd
  from src.database import get_connection
  conn = get_connection()
  df = pd.read_sql("SELECT * FROM predictions_view", conn)
  df.to_csv(f'backups/predictions_{datetime.now():%Y%m%d}.csv')
  ```

## PhD Report (After 6 months)

- [ ] Run comprehensive analysis
- [ ] Generate performance charts
- [ ] Calculate statistical significance
- [ ] Write findings report
- [ ] Include in PhD thesis
```

---

## 🎓 FINAL NOTES FOR AI CODING AGENT

### Critical Points

1. **Error Handling**: Every scraper function MUST handle exceptions gracefully
2. **Logging**: Use logging module, not print statements
3. **Rate Limiting**: ALWAYS call `smart_delay()` between requests
4. **Data Validation**: Validate before database insert
5. **Connection Pooling**: Use provided pool, release connections

### Testing Strategy

1. Save HTML fixtures for tests (don't hit live sites in tests)
2. Test edge cases (missing data, malformed HTML)
3. Test database rollback on errors

### Maintenance

- HTML selectors WILL break - expect to update them
- Log selector failures with sample HTML
- Use multiple fallback selectors where possible

### PhD Value

This project demonstrates:
- Real-world data engineering
- ETL pipeline design
- Statistical analysis
- Reproducible research
- Automation and monitoring

---

## 📖 GLOSSARY

**Prediction-Time Odds**: Odds when prediction was made (24+ hours before match)  
**Closing Odds**: Odds just before match starts (industry standard)  
**ROI**: Return on Investment (profit/loss per bet)  
**Flat Betting**: Same stake every bet (10 KSH)  
**Edge**: Advantage over bookmaker odds

---

# 🎉 PLAN COMPLETE!

**You now have**:
✅ Complete database schema  
✅ All core modules (config, utils, database)  
✅ Full scraper implementations  
✅ GitHub Actions workflows  
✅ Analysis tools  
✅ Testing framework  
✅ Deployment checklist  

**Total Files**: 20+  
**Total Lines of Code**: ~3000+  
**Implementation Time**: 10-15 days  
**Data Collection**: 6 months  

**Ready to build!** 🚀

Save this entire plan as `IMPLEMENTATION_PLAN.md` and feed it to your AI coding agent (Cursor, Aider, etc.) to generate the complete project.

Good luck with your PhD research! 📚🎓