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

# CSS Selectors (updated for current site structure)
SELECTORS = {
    'prediction_cards': 'div.flex.w-full.justify-between.items-center',
    'player_links': 'a[href*="/tennis/player/"]',
    'h2h_link': 'a[href*="/tennis/h2h-odds-bets/"]',
    'all_h2h_links': 'a[href*="h2h-odds-bets"]',  # Broader search
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
        
        # Debug: Save raw HTML to inspect
        logger.debug(f"Homepage HTML length: {len(response.text)} characters")
        
        # Find all prediction cards
        cards = soup.select(SELECTORS['prediction_cards'])
        logger.info(f"Found {len(cards)} potential prediction cards")
        
        # Also check for H2H links to see how many matches exist
        h2h_links = soup.select(SELECTORS['all_h2h_links'])
        logger.info(f"Found {len(h2h_links)} H2H links (potential matches)")
        
        # Debug: Print first few links
        if len(h2h_links) > 0:
            logger.debug(f"Sample H2H links: {[link.get('href')[:50] for link in h2h_links[:3]]}")
        
        if len(h2h_links) > 0 and len(cards) == 0:
            logger.warning("⚠️ Found matches but no predictions - predictions may require login or aren't ready yet")
            logger.info("💡 Predictions may be released closer to match time, or require Matchstat account")
        
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
                
                # Check for "Prediction Ready Soon" or paywalled prediction text
                card_text = card.get_text()
                if 'Prediction Ready Soon' in card_text:
                    logger.debug(f"Card {i}: Prediction not ready yet")
                    continue
                
                # Check if prediction is behind paywall
                if 'REGISTER NOW' in card_text or 'Show Me Predictions' in card_text:
                    logger.debug(f"Card {i}: Prediction behind paywall/registration")
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
