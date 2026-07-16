"""
Direct Selenium scraper for Matchstat.com
Falls back when Groq API doesn't have web access
"""
import logging
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

from src.config import Config
from src.utils import clean_player_name, validate_prediction_data, setup_logging
from src.database import save_prediction, log_scrape

logger = logging.getLogger(__name__)

MATCHSTAT_URL = "https://matchstat.com/tennis/"


def create_driver():
    """Create undetected Chrome driver for bypassing Cloudflare"""
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = uc.Chrome(options=options, version_main=131)
    return driver


def scrape_matchstat_predictions(driver) -> List[Dict[str, Any]]:
    """Scrape predictions from Matchstat using Selenium"""
    logger.info(f"Loading {MATCHSTAT_URL}")
    driver.get(MATCHSTAT_URL)
    
    # Wait for page to load
    time.sleep(5)
    
    predictions = []
    
    try:
        # Find all match rows with predictions
        matches = driver.find_elements(By.CSS_SELECTOR, "div[class*='match'], tr[class*='match']")
        
        logger.info(f"Found {len(matches)} potential match elements")
        
        for match_elem in matches:
            try:
                # Extract player names
                player_elems = match_elem.find_elements(By.CSS_SELECTOR, "[class*='player'], [class*='team']")
                if len(player_elems) < 2:
                    continue
                
                player1 = clean_player_name(player_elems[0].text)
                player2 = clean_player_name(player_elems[1].text)
                
                if not player1 or not player2:
                    continue
                
                # Look for probability percentage
                prob_match = re.search(r'(\d+(?:\.\d+)?)\s*%', match_elem.text)
                if not prob_match:
                    continue
                
                win_prob = float(prob_match.group(1))
                
                # Determine predicted winner (higher probability)
                predicted_winner = player1 if win_prob > 50 else player2
                
                # Extract tournament info if available
                tournament = "Unknown Tournament"
                try:
                    tourn_elem = match_elem.find_element(By.CSS_SELECTOR, "[class*='tournament'], [class*='league']")
                    tournament = tourn_elem.text.strip()
                except:
                    pass
                
                predictions.append({
                    'player1_name': player1,
                    'player2_name': player2,
                    'predicted_winner': predicted_winner,
                    'win_probability': win_prob,
                    'tournament_name': tournament,
                    'matchstat_url': MATCHSTAT_URL,
                    'match_datetime': datetime.now() + timedelta(days=1, hours=12)
                })
                
            except Exception as e:
                logger.debug(f"Error parsing match element: {e}")
                continue
        
        logger.info(f"Extracted {len(predictions)} predictions")
        return predictions
        
    except Exception as e:
        logger.error(f"Error scraping predictions: {e}")
        return []


def main():
    """Main execution"""
    setup_logging()
    logger.info("="*60)
    logger.info("MATCHSTAT SCRAPER - SELENIUM VERSION")
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
        driver = create_driver()
        logger.info("Chrome driver initialized")
        
        # Scrape predictions
        raw_predictions = scrape_matchstat_predictions(driver)
        stats['found'] = len(raw_predictions)
        
        if not raw_predictions:
            logger.warning("No predictions found")
            log_scrape(
                scrape_type='predictions',
                matches_found=0,
                matches_saved=0,
                status='success',
                execution_time=time.time() - start_time,
                pages_scraped=1
            )
            return
        
        # Save predictions
        for i, pred_data in enumerate(raw_predictions, 1):
            try:
                logger.info(f"[{i}/{len(raw_predictions)}] {pred_data['player1_name']} vs {pred_data['player2_name']}")
                
                if not validate_prediction_data(pred_data):
                    stats['failed'] += 1
                    continue
                
                prediction_id = save_prediction(
                    player1_name=pred_data['player1_name'],
                    player2_name=pred_data['player2_name'],
                    predicted_winner_name=pred_data['predicted_winner'],
                    tournament_name=pred_data['tournament_name'],
                    match_datetime=pred_data['match_datetime'],
                    matchstat_url=pred_data['matchstat_url'],
                    prediction_summary={'win_probability': pred_data.get('win_probability')}
                )
                
                if prediction_id:
                    stats['saved'] += 1
                    logger.info(f"  💾 Saved (ID: {prediction_id})")
                else:
                    logger.info(f"  ⊘ Already exists")
                    
            except Exception as e:
                logger.error(f"Error saving prediction {i}: {e}")
                stats['failed'] += 1
                stats['errors'].append(str(e))
        
        execution_time = time.time() - start_time
        
        logger.info("\n" + "="*60)
        logger.info("SCRAPING COMPLETE")
        logger.info("="*60)
        logger.info(f"Found: {stats['found']}")
        logger.info(f"Saved: {stats['saved']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Time: {execution_time:.2f}s")
        
        status = 'success' if stats['saved'] > 0 else 'partial'
        log_scrape(
            scrape_type='predictions',
            matches_found=stats['found'],
            matches_saved=stats['saved'],
            matches_failed=stats['failed'],
            errors='; '.join(stats['errors'][:5]) if stats['errors'] else None,
            status=status,
            execution_time=execution_time,
            pages_scraped=1
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        log_scrape(
            scrape_type='predictions',
            matches_found=stats['found'],
            matches_saved=stats['saved'],
            errors=str(e),
            status='failed',
            execution_time=time.time() - start_time,
            pages_scraped=1
        )
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver closed")


if __name__ == '__main__':
    main()
