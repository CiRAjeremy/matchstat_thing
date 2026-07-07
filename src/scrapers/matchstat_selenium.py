"""
Matchstat.com prediction scraper using Selenium
For JavaScript-rendered content
"""
import re
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config import Config
from src.utils import (
    smart_delay, clean_player_name, parse_rank,
    parse_match_date, validate_prediction_data, setup_logging,
    parse_odds_string
)
from src.database import save_prediction, save_odds_snapshot, log_scrape

logger = logging.getLogger(__name__)

BASE_URL = "https://matchstat.com"
HOMEPAGE_URL = "https://matchstat.com/"


def get_driver():
    """Create and configure Selenium WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument(f'user-agent={Config.USER_AGENT}')
    
    # Use ChromeDriverManager for automatic driver management
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except ImportError:
        # Fallback if webdriver-manager not available
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def scrape_matchstat_homepage_selenium() -> List[Dict[str, Any]]:
    """
    Scrape today's tennis predictions using Selenium
    
    Returns:
        List of dicts with match data
    """
    logger.info(f"Scraping Matchstat homepage with Selenium: {HOMEPAGE_URL}")
    
    driver = None
    try:
        driver = get_driver()
        driver.get(HOMEPAGE_URL)
        
        # Wait for page to load (wait for match cards to appear)
        logger.info("Waiting for page to render...")
        time.sleep(5)  # Give JavaScript time to render
        
        # Take screenshot for debugging
        driver.save_screenshot('logs/homepage_screenshot.png')
        logger.debug("Screenshot saved to logs/homepage_screenshot.png")
        
        # Find all H2H links
        h2h_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="h2h-odds-bets"]')
        logger.info(f"Found {len(h2h_elements)} H2H links")
        
        # Find match containers
        match_containers = driver.find_elements(By.CSS_SELECTOR, 'div.flex.w-full.justify-between.items-center')
        logger.info(f"Found {len(match_containers)} match containers")
        
        predictions = []
        
        for i, container in enumerate(match_containers, 1):
            try:
                # Find player links within this container
                player_links = container.find_elements(By.CSS_SELECTOR, 'a[href*="/tennis/player/"]')
                
                if len(player_links) < 2:
                    logger.debug(f"Container {i}: Not enough player links")
                    continue
                
                # Extract player 1
                player1_name = clean_player_name(player_links[0].text)
                player1_rank = parse_rank(player_links[0].text)
                
                # Extract player 2
                player2_name = clean_player_name(player_links[1].text)
                player2_rank = parse_rank(player_links[1].text)
                
                # Find H2H link
                h2h_link_elem = container.find_element(By.CSS_SELECTOR, 'a[href*="h2h-odds-bets"]')
                h2h_url = h2h_link_elem.get_attribute('href')
                
                # Check if prediction is ready
                container_text = container.text
                if 'Prediction Ready Soon' in container_text or 'REGISTER NOW' in container_text:
                    logger.debug(f"Container {i}: Prediction not ready or paywalled")
                    continue
                
                # Extract odds
                odds_divs = container.find_elements(By.CSS_SELECTOR, 'div.text-center.bg-gray-100')
                player1_odds = None
                player2_odds = None
                
                if len(odds_divs) >= 2:
                    try:
                        p1_odds_text = odds_divs[0].text.split('\n')[1]  # Second line has odds
                        p2_odds_text = odds_divs[1].text.split('\n')[1]
                        player1_odds = parse_odds_string(p1_odds_text)
                        player2_odds = parse_odds_string(p2_odds_text)
                    except Exception as e:
                        logger.debug(f"Could not parse odds: {e}")
                
                prediction = {
                    'player1': {
                        'name': player1_name,
                        'country': None,  # TODO: Extract from flag
                        'rank': player1_rank
                    },
                    'player2': {
                        'name': player2_name,
                        'country': None,
                        'rank': player2_rank
                    },
                    'homepage_odds': {
                        'player1': player1_odds,
                        'player2': player2_odds
                    },
                    'h2h_url': h2h_url
                }
                
                predictions.append(prediction)
                logger.info(f"✓ Container {i}: {player1_name} vs {player2_name}")
                
            except Exception as e:
                logger.error(f"Error parsing container {i}: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(predictions)} matches")
        return predictions
        
    except Exception as e:
        logger.error(f"Error scraping homepage: {e}", exc_info=True)
        return []
    finally:
        if driver:
            driver.quit()


def scrape_prediction_details(h2h_url: str, driver) -> Optional[Dict[str, Any]]:
    """
    Scrape prediction details from H2H page using Selenium
    
    Args:
        h2h_url: URL to H2H prediction page
        driver: Selenium WebDriver instance
    
    Returns:
        dict with prediction details or None if no prediction found/match finished
    """
    logger.info(f"Scraping prediction from: {h2h_url}")
    
    try:
        driver.get(h2h_url)
        time.sleep(3)  # Wait for page to render
        
        page_text = driver.page_source
        
        # Check if match already finished
        if 'Ended Score' in page_text or 'Final Score' in page_text:
            logger.info("⊘ Match already finished - skipping")
            return None
        
        # Look for prediction text: "Odds indicate [PLAYER] will win (XX% probability)"
        prediction_pattern = r'Odds indicate\s+([^(]+?)\s+will win\s*\((\d+(?:\.\d+)?)\s*%\s*probability\)'
        prediction_match = re.search(prediction_pattern, page_text, re.IGNORECASE)
        
        if not prediction_match:
            logger.debug("No 'Odds indicate' prediction found on page")
            return None
        
        predicted_winner_raw = prediction_match.group(1).strip()
        win_probability = float(prediction_match.group(2))
        
        logger.info(f"✓ Found prediction: {predicted_winner_raw} ({win_probability}%)")
        
        # Extract match details
        details = {
            'predicted_winner': clean_player_name(predicted_winner_raw),
            'win_probability': win_probability,
            'raw_prediction_text': prediction_match.group(0)
        }
        
        # Try to extract tournament name
        try:
            # Look for tournament name in breadcrumbs or header
            tournament_elem = driver.find_element(By.CSS_SELECTOR, 'h1, h2, .tournament-name, .breadcrumb')
            tournament_text = tournament_elem.text
            # Extract tournament name (before player names)
            if ' vs ' in tournament_text:
                details['tournament_name'] = tournament_text.split(' vs ')[0].split('\n')[0].strip()
            else:
                details['tournament_name'] = tournament_text.split('\n')[0].strip()
        except Exception as e:
            logger.debug(f"Could not extract tournament name: {e}")
            details['tournament_name'] = "Unknown Tournament"
        
        # Try to extract match datetime
        try:
            # Look for date/time elements
            datetime_elem = driver.find_element(By.CSS_SELECTOR, 'time, .match-time, .match-date')
            datetime_text = datetime_elem.text.strip()
            details['match_datetime'] = parse_match_date(datetime_text)
        except Exception as e:
            logger.debug(f"Could not extract match datetime: {e}")
            # Default to tomorrow at noon if can't find
            from datetime import timedelta
            details['match_datetime'] = datetime.now() + timedelta(days=1, hours=12)
        
        # Try to extract surface
        try:
            surface_match = re.search(r'\b(hard|clay|grass|carpet)\b', page_text, re.IGNORECASE)
            if surface_match:
                details['surface'] = surface_match.group(1).capitalize()
            else:
                details['surface'] = None
        except Exception:
            details['surface'] = None
        
        # Try to extract tour type
        try:
            tour_match = re.search(r'\b(ATP|WTA|ITF|Challenger)\b', page_text, re.IGNORECASE)
            if tour_match:
                details['tour_type'] = tour_match.group(1).upper()
            else:
                details['tour_type'] = 'ATP'  # Default to ATP
        except Exception:
            details['tour_type'] = 'ATP'
        
        return details
        
    except Exception as e:
        logger.error(f"Error scraping prediction details: {e}")
        return None


def main():
    """Main execution using Selenium"""
    setup_logging()
    logger.info("="*60)
    logger.info("STARTING MATCHSTAT PREDICTION SCRAPER (SELENIUM)")
    logger.info("="*60)
    
    start_time = time.time()
    
    stats = {
        'found': 0,
        'saved': 0,
        'failed': 0,
        'errors': []
    }
    
    driver = None
    
    try:
        # Step 1: Scrape homepage
        predictions = scrape_matchstat_homepage_selenium()
        stats['found'] = len(predictions)
        
        if not predictions:
            logger.warning("No predictions found")
            logger.info("💡 This could mean:")
            logger.info("   1. No tennis matches today")
            logger.info("   2. Predictions not released yet (try again in a few hours)")
            logger.info("   3. No tennis matches scheduled")
            
            log_scrape(
                scrape_type='predictions',
                matches_found=0,
                matches_saved=0,
                status='success',
                execution_time=time.time() - start_time,
                pages_scraped=1
            )
            return
        
        logger.info(f"\n✓ Found {len(predictions)} matches on homepage")
        
        # Quick check: if we've already scraped recently, check database first
        try:
            from src.database import get_connection, release_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM predictions WHERE prediction_date = CURRENT_DATE")
            todays_predictions = cur.fetchone()[0]
            cur.close()
            release_connection(conn)
            
            if todays_predictions > 0:
                logger.info(f"ℹ️ Already have {todays_predictions} predictions from today")
                logger.info("Checking for new matches not yet in database...")
        except Exception as e:
            logger.debug(f"Could not check existing predictions: {e}")
        
        logger.info("Now checking each match for predictions...\n")
        
        # Step 2: For each match, scrape details and save to database
        driver = get_driver()
        
        for i, match in enumerate(predictions, 1):
            try:
                logger.info(f"\n[{i}/{len(predictions)}] Processing: {match['player1']['name']} vs {match['player2']['name']}")
                
                # Scrape prediction details from H2H page
                details = scrape_prediction_details(match['h2h_url'], driver)
                
                if not details:
                    logger.info(f"⊘ No prediction available for this match")
                    stats['failed'] += 1
                    continue
                
                # Prepare data for database
                prediction_data = {
                    'player1_name': match['player1']['name'],
                    'player2_name': match['player2']['name'],
                    'predicted_winner': details['predicted_winner'],
                    'tournament_name': details.get('tournament_name', 'Unknown'),
                    'match_datetime': details['match_datetime'],
                    'matchstat_url': match['h2h_url'],
                    'player1_country': match['player1'].get('country'),
                    'player2_country': match['player2'].get('country'),
                    'player1_rank': match['player1'].get('rank'),
                    'player2_rank': match['player2'].get('rank'),
                    'surface': details.get('surface'),
                    'tour_type': details.get('tour_type', 'ATP'),
                    'raw_prediction_text': details.get('raw_prediction_text'),
                    'prediction_summary': {
                        'win_probability': details.get('win_probability'),
                        'homepage_odds': match.get('homepage_odds')
                    }
                }
                
                # Validate data
                if not validate_prediction_data(prediction_data):
                    logger.error(f"✗ Invalid prediction data - skipping")
                    stats['failed'] += 1
                    stats['errors'].append(f"Invalid data for {match['player1']['name']} vs {match['player2']['name']}")
                    continue
                
                # Save prediction to database
                prediction_id = save_prediction(
                    player1_name=prediction_data['player1_name'],
                    player2_name=prediction_data['player2_name'],
                    predicted_winner_name=prediction_data['predicted_winner'],
                    tournament_name=prediction_data['tournament_name'],
                    match_datetime=prediction_data['match_datetime'],
                    matchstat_url=prediction_data['matchstat_url'],
                    player1_country=prediction_data.get('player1_country'),
                    player2_country=prediction_data.get('player2_country'),
                    player1_rank=prediction_data.get('player1_rank'),
                    player2_rank=prediction_data.get('player2_rank'),
                    surface=prediction_data.get('surface'),
                    tour_type=prediction_data.get('tour_type'),
                    raw_prediction_text=prediction_data.get('raw_prediction_text'),
                    prediction_summary=prediction_data.get('prediction_summary')
                )
                
                if prediction_id:
                    stats['saved'] += 1
                    logger.info(f"💾 NEW prediction saved to database")
                    
                    # Save odds snapshot if we have odds data
                    odds = match.get('homepage_odds', {})
                    if odds.get('player1') and odds.get('player2'):
                        try:
                            save_odds_snapshot(
                                prediction_id=prediction_id,
                                bookmaker='Matchstat',
                                player1_odds=odds['player1'],
                                player2_odds=odds['player2'],
                                odds_type='prediction_time'
                            )
                        except Exception as e:
                            logger.warning(f"Could not save odds: {e}")
                
                else:
                    logger.info(f"⊘ Prediction already in database - skipping")
                
                # Polite delay between requests
                smart_delay(2, 4)
                
            except Exception as e:
                logger.error(f"Error processing match {i}: {e}", exc_info=True)
                stats['failed'] += 1
                stats['errors'].append(str(e))
        
        # Log results
        execution_time = time.time() - start_time
        
        logger.info("\n" + "="*60)
        logger.info("SCRAPING COMPLETE")
        logger.info("="*60)
        logger.info(f"Matches found: {stats['found']}")
        logger.info(f"Predictions saved: {stats['saved']}")
        logger.info(f"Failed/Skipped: {stats['failed']}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        
        # Determine status
        if stats['saved'] == 0 and stats['found'] > 0:
            status = 'partial'  # Found matches but no predictions
        elif stats['failed'] > stats['saved']:
            status = 'partial'
        else:
            status = 'success'
        
        # Log to database
        log_scrape(
            scrape_type='predictions',
            matches_found=stats['found'],
            matches_saved=stats['saved'],
            matches_failed=stats['failed'],
            errors='; '.join(stats['errors'][:5]) if stats['errors'] else None,
            status=status,
            execution_time=execution_time,
            pages_scraped=stats['found'] + 1  # Homepage + detail pages
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        
        log_scrape(
            scrape_type='predictions',
            matches_found=stats['found'],
            matches_saved=stats['saved'],
            matches_failed=stats['failed'],
            errors=str(e),
            status='failed',
            execution_time=time.time() - start_time,
            pages_scraped=1
        )
    
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    main()
