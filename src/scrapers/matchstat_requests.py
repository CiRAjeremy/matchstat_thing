"""
Simple requests-based scraper for Matchstat.com
Works with GitHub Actions (no Selenium/Chrome needed)
"""
import logging
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

from src.config import Config
from src.utils import (
    clean_player_name, validate_prediction_data, setup_logging,
    get_headers, smart_delay
)
from src.database import save_prediction, log_scrape

logger = logging.getLogger(__name__)

MATCHSTAT_URL = "https://matchstat.com/tennis/"


def scrape_matchstat_predictions() -> List[Dict[str, Any]]:
    """Scrape predictions from Matchstat using requests"""
    logger.info(f"Fetching {MATCHSTAT_URL}")
    
    try:
        response = requests.get(
            MATCHSTAT_URL,
            headers=get_headers(),
            timeout=Config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        predictions = []
        
        # Find prediction tables/sections
        # Matchstat uses various classes - try multiple selectors
        match_containers = soup.find_all(['tr', 'div'], class_=re.compile(r'match|game|fixture', re.I))
        
        logger.info(f"Found {len(match_containers)} potential match containers")
        
        for container in match_containers:
            try:
                text = container.get_text()
                
                # Look for percentage probabilities (e.g., "75%" or "75.5%")
                prob_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
                if len(prob_matches) < 2:
                    continue
                
                # Extract player names - look for name-like patterns
                # Matchstat typically has names in specific elements
                player_elems = container.find_all(['a', 'span', 'div'], class_=re.compile(r'player|team|name', re.I))
                
                if len(player_elems) < 2:
                    # Fallback: extract from text
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    player_lines = [l for l in lines if len(l) > 5 and len(l) < 50 and not l.replace('.','').replace('%','').isdigit()]
                    if len(player_lines) >= 2:
                        player1 = clean_player_name(player_lines[0])
                        player2 = clean_player_name(player_lines[1])
                    else:
                        continue
                else:
                    player1 = clean_player_name(player_elems[0].get_text())
                    player2 = clean_player_name(player_elems[1].get_text())
                
                if not player1 or not player2 or player1 == player2:
                    continue
                
                # Parse probabilities
                prob1 = float(prob_matches[0])
                prob2 = float(prob_matches[1])
                
                # Higher probability wins
                if prob1 > prob2:
                    predicted_winner = player1
                    win_prob = prob1
                else:
                    predicted_winner = player2
                    win_prob = prob2
                
                # Extract tournament if available
                tournament = "Unknown Tournament"
                tourn_elem = container.find_previous(['h3', 'h2', 'div'], class_=re.compile(r'tournament|league|competition', re.I))
                if tourn_elem:
                    tournament = tourn_elem.get_text().strip()
                
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
                logger.debug(f"Error parsing container: {e}")
                continue
        
        logger.info(f"Extracted {len(predictions)} predictions")
        return predictions
        
    except requests.RequestException as e:
        logger.error(f"Error fetching Matchstat: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing Matchstat: {e}")
        return []


def main():
    """Main execution"""
    setup_logging()
    logger.info("="*60)
    logger.info("MATCHSTAT SCRAPER - REQUESTS VERSION")
    logger.info("="*60)
    
    start_time = time.time()
    
    stats = {
        'found': 0,
        'saved': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        # Scrape predictions
        raw_predictions = scrape_matchstat_predictions()
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


if __name__ == '__main__':
    main()
