"""
Matchstat.com prediction scraper using Selenium
For JavaScript-rendered content
"""
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
    chrome_options.add_argument(f'user-agent={Config.USER_AGENT}')
    
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
    
    try:
        # Step 1: Scrape homepage
        predictions = scrape_matchstat_homepage_selenium()
        stats['found'] = len(predictions)
        
        if not predictions:
            logger.warning("No predictions found")
            logger.info("💡 This could mean:")
            logger.info("   1. No tennis matches today")
            logger.info("   2. Predictions not released yet (try later)")
            logger.info("   3. Predictions require Matchstat account/login")
            
            log_scrape(
                scrape_type='predictions',
                matches_found=0,
                matches_saved=0,
                status='success',
                execution_time=time.time() - start_time,
                pages_scraped=1
            )
            return
        
        # Step 2: For each match, get details and save
        logger.info(f"\n⚠️ Found {len(predictions)} matches")
        logger.info("⚠️ NOTE: These may not have predictions yet (just match listings)")
        logger.info("⚠️ Real predictions usually come closer to match time\n")
        
        # For now, just log what we found
        for i, pred in enumerate(predictions, 1):
            logger.info(f"{i}. {pred['player1']['name']} vs {pred['player2']['name']} - {pred['h2h_url']}")
        
        logger.info(f"\nExecution time: {time.time() - start_time:.2f} seconds")
        logger.info("\n💡 To actually scrape and save predictions:")
        logger.info("   1. Visit one of the H2H URLs above")
        logger.info("   2. Check if there's a clear prediction (who will win)")
        logger.info("   3. If yes, the scraper needs to be updated to extract that")
        logger.info("   4. If no, predictions come later (check back in a few hours)")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == '__main__':
    main()
