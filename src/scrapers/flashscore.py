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
    try:
        setup_logging()
    except Exception as e:
        print(f"FATAL: Failed to setup logging: {e}")
        import traceback
        traceback.print_exc()
        raise
    
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
