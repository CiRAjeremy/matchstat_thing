"""
Matchstat.com prediction scraper using Groq AI (groq/compound)

OPTIMIZATION: Makes exactly ONE API call to get ALL predictions
- Single request to Groq API with compound model
- Model automatically uses visit_website tool to fetch the page
- AI extracts ALL matches in one response as JSON array
- No per-prediction API calls - everything in one shot

Rate Limiting Strategy:
- Try groq/compound-mini first (lower limits, faster)
- Fall back to groq/compound if needed
- Implement exponential backoff on 429 errors
- Skip to next model if wait time > 10 seconds

Uses Groq's built-in visit_website tool to bypass Cloudflare and extract predictions
"""
import os
import json
import logging
import time
from datetime import datetime, timedelta
from time import sleep
from typing import List, Dict, Optional, Any

import requests

from src.config import Config
from src.utils import (
    clean_player_name, validate_prediction_data, setup_logging
)
from src.database import save_prediction, log_scrape

logger = logging.getLogger(__name__)

# Groq API configuration (NOTE: key prefix is gsk_, endpoint is api.groq.com)
GROK_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MATCHSTAT_URL = "https://matchstat.com/"


def get_grok_api_key() -> Optional[str]:
    """Get Groq API key from environment (stored as GROK_API_KEY, starts with gsk_)"""
    api_key = os.getenv('GROK_API_KEY') or os.getenv('GROQ_API_KEY')
    if not api_key:
        logger.error("GROK_API_KEY or GROQ_API_KEY not found in environment")
    return api_key


# Models to try in order - compound-mini has more generous rate limits
# Try mini first, then full compound if needed
GROQ_MODELS = ["groq/compound-mini", "groq/compound"]

# If rate-limit wait exceeds this, skip to next model rather than sleeping  
MAX_WAIT_SECONDS = 10  # Reduced to skip faster on long waits


def _parse_retry_after(value: str) -> float:
    """
    Parse Groq's Retry-After header which can be:
      - plain seconds:  '60'
      - duration str:   '17m16.8s', '1h2m3.5s', '45.2s', '1m'
    Returns wait time in seconds.
    """
    import re
    value = value.strip()
    # Try plain float first
    try:
        return float(value)
    except ValueError:
        pass
    # Parse h/m/s duration e.g. "1h2m3.5s", "17m16.8s", "45s"
    total = 0.0
    for match in re.finditer(r'(\d+(?:\.\d+)?)([hms])', value):
        num, unit = float(match.group(1)), match.group(2)
        if unit == 'h':
            total += num * 3600
        elif unit == 'm':
            total += num * 60
        elif unit == 's':
            total += num
    return total if total > 0 else 60.0  # fallback to 60s if unparseable


def _parse_wait_from_body(body: str) -> float:
    """
    Extract wait time from Groq error body, e.g.:
      "Please try again in 7.476s"
      "try again in 1m30s"
    Returns seconds, or 0.0 if not found.
    """
    import re
    # Match patterns like "try again in 7.476s" or "try again in 1m30s"
    match = re.search(r'try again in ([\d.]+m[\d.]+s|[\d.]+[hms]|[\d.]+)', body, re.IGNORECASE)
    if match:
        return _parse_retry_after(match.group(1))
    return 0.0


def extract_predictions_with_grok(api_key: str) -> List[Dict[str, Any]]:
    """
    Use Groq AI to browse Matchstat and extract tennis predictions
    ONE API CALL extracts ALL predictions in a single response
    
    Args:
        api_key: Groq API key
    
    Returns:
        List of prediction dictionaries
    """
    logger.info("Using Groq AI to extract ALL predictions from Matchstat in ONE call")
    
    # Ultra-concise prompt - compound models auto-select tools
    # Asking for JSON array ensures we get all predictions in one response
    prompt = """Visit https://matchstat.com/tennis/ and extract ALL tennis predictions for today.

Return JSON array with ALL matches that have probability predictions. Fields per match:
- player1_name, player2_name, predicted_winner
- win_probability (number only)
- tournament_name, surface, tour_type (if available)

Skip: matches without predictions, finished matches.

Format: [{"player1_name":"A","player2_name":"B","predicted_winner":"A","win_probability":75.5,"tournament_name":"US Open","surface":"Hard","tour_type":"ATP"}]

Return ONLY the JSON array with ALL predictions."""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Try compound-mini first (lower rate limits), then compound
    for model in GROQ_MODELS:
        logger.info(f"Trying model: {model}")
        result = _call_groq_with_retry(api_key, headers, prompt, model)
        if result is not None:
            logger.info(f"✓ Got ALL predictions in ONE API call using {model}")
            return result
        logger.warning(f"Model {model} failed, trying next...")
    
    logger.error("All Groq models exhausted")
    return []


def _call_groq_with_retry(
    api_key: str,
    headers: dict,
    prompt: str,
    model: str,
    max_retries: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """
    Call Groq API with exponential backoff on 429 rate-limit errors.
    Returns the parsed list on success, or None if all retries fail.
    """
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4000
    }

    content = ""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Sending request to Groq API (attempt {attempt}/{max_retries})...")
            response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=120)

            if response.status_code == 429:
                body_text = response.text
                # Parse wait from header AND body; use the shorter one
                retry_header = (response.headers.get('retry-after')
                                or response.headers.get('x-ratelimit-reset-requests', ''))
                header_wait = _parse_retry_after(retry_header) if retry_header else 2 ** attempt
                body_wait   = _parse_wait_from_body(body_text)
                wait = min(header_wait, body_wait) if body_wait > 0 else header_wait
                logger.warning(
                    f"Rate limited (429) on {model}. "
                    f"header={retry_header!r}({header_wait:.1f}s) "
                    f"body={body_wait:.1f}s -> using {wait:.1f}s"
                )
                logger.debug(f"429 body: {body_text[:300]}")
                if wait > MAX_WAIT_SECONDS:
                    logger.warning(f"Wait {wait:.0f}s > {MAX_WAIT_SECONDS}s limit — skipping to next model")
                    return None
                if attempt < max_retries:
                    logger.info(f"Waiting {wait:.1f}s then retrying {model}...")
                    sleep(wait)
                    continue
                else:
                    logger.error(f"Exhausted retries for {model} due to rate limiting")
                    return None

            response.raise_for_status()
            result = response.json()

            if 'choices' not in result or len(result['choices']) == 0:
                logger.error("No choices in Groq API response")
                return None

            content = result['choices'][0]['message']['content']
            logger.info(f"Received response from Groq/{model} (length: {len(content)} chars)")

            # Parse JSON — model may wrap it in markdown code blocks
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content.strip()

            # Save raw response for every run (helps debug site structure changes)
            with open('logs/grok_response.txt', 'w', encoding='utf-8') as f:
                f.write(f"=== Model: {model} | {datetime.now()} ===\n{content}")

            try:
                predictions = json.loads(json_str)
            except json.JSONDecodeError:
                # Model returned explanatory text instead of JSON
                # (e.g. "I couldn't find match data on this page")
                logger.warning(f"Groq/{model} returned non-JSON text. Treating as 0 predictions.")
                logger.warning(f"Model said: {content[:300]}")
                return []  # Return empty list (not None) so we log but don't hard-fail

            if not isinstance(predictions, list):
                logger.error("Groq response is not a JSON list")
                return None

            if len(predictions) == 0:
                logger.warning(f"Groq/{model} returned empty list — site may have no predictions yet today.")

            logger.info(f"Groq/{model} extracted {len(predictions)} predictions")
            return predictions

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 'unknown'
            body = e.response.text[:300] if e.response is not None else 'no body'
            logger.error(f"HTTP {status} error on {model}: {e}")
            logger.error(f"Response body: {body}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Groq/{model} response: {e}")
            logger.error(f"Response content: {content[:500]}")
            with open('logs/grok_response.txt', 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("Saved raw response to logs/grok_response.txt for debugging")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Groq/{model}: {e}", exc_info=True)
            return None

    return None


def parse_grok_prediction(pred_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse and validate prediction data from Grok
    
    Args:
        pred_data: Raw prediction data from Grok
    
    Returns:
        Validated prediction dict or None
    """
    try:
        # Clean and validate data
        player1 = clean_player_name(pred_data.get('player1_name', ''))
        player2 = clean_player_name(pred_data.get('player2_name', ''))
        predicted_winner = clean_player_name(pred_data.get('predicted_winner', ''))
        
        if not player1 or not player2 or not predicted_winner:
            logger.warning(f"Missing required fields in prediction: {pred_data}")
            return None
        
        # Parse win probability
        try:
            win_prob = float(pred_data.get('win_probability', 0))
            if win_prob <= 0 or win_prob > 100:
                logger.warning(f"Invalid win probability: {win_prob}")
                win_prob = None
        except (ValueError, TypeError):
            win_prob = None
        
        # Parse match datetime
        match_datetime = None
        if 'match_datetime' in pred_data and pred_data['match_datetime']:
            try:
                # Try parsing different formats
                dt_str = str(pred_data['match_datetime'])
                for fmt in ['%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        match_datetime = datetime.strptime(dt_str, fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Default to tomorrow at noon if no datetime
        if not match_datetime:
            match_datetime = datetime.now() + timedelta(days=1, hours=12)
        
        return {
            'player1_name': player1,
            'player2_name': player2,
            'predicted_winner': predicted_winner,
            'tournament_name': pred_data.get('tournament_name', 'Unknown Tournament'),
            'match_datetime': match_datetime,
            'matchstat_url': pred_data.get('matchstat_url', ''),
            'surface': pred_data.get('surface'),
            'tour_type': pred_data.get('tour_type', 'ATP'),
            'raw_prediction_text': f"Grok extraction: {predicted_winner} ({win_prob}%)" if win_prob else f"Grok extraction: {predicted_winner}",
            'prediction_summary': {
                'win_probability': win_prob,
                'source': 'grok_ai'
            }
        }
        
    except Exception as e:
        logger.error(f"Error parsing Grok prediction: {e}")
        return None


def main():
    """Main execution using Grok AI"""
    try:
        setup_logging()
    except Exception as e:
        print(f"FATAL: Failed to setup logging: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    logger.info("="*60)
    logger.info("MATCHSTAT SCRAPER - GROK AI VERSION")
    logger.info("="*60)
    
    start_time = time.time()
    
    stats = {
        'found': 0,
        'saved': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        # Get API key
        api_key = get_grok_api_key()
        if not api_key:
            logger.error("Cannot proceed without Grok API key")
            logger.info("Please set GROK_API_KEY or XAI_API_KEY in your .env file")
            return
        
        # Extract predictions using Grok
        raw_predictions = extract_predictions_with_grok(api_key)
        stats['found'] = len(raw_predictions)
        
        if not raw_predictions:
            logger.warning("No predictions extracted by Grok")
            log_scrape(
                scrape_type='predictions',
                matches_found=0,
                matches_saved=0,
                status='success',
                execution_time=time.time() - start_time,
                pages_scraped=1
            )
            return
        
        logger.info(f"\n✓ Grok found {len(raw_predictions)} predictions")
        logger.info("Processing and saving to database...\n")
        
        # Process each prediction
        for i, raw_pred in enumerate(raw_predictions, 1):
            try:
                logger.info(f"[{i}/{len(raw_predictions)}] Processing...")
                
                # Parse and validate
                prediction_data = parse_grok_prediction(raw_pred)
                
                if not prediction_data:
                    logger.warning(f"✗ Invalid prediction data - skipping")
                    stats['failed'] += 1
                    continue
                
                logger.info(f"  {prediction_data['player1_name']} vs {prediction_data['player2_name']}")
                logger.info(f"  → Predicted: {prediction_data['predicted_winner']}")
                
                # Validate data
                if not validate_prediction_data(prediction_data):
                    logger.error(f"✗ Failed validation - skipping")
                    stats['failed'] += 1
                    stats['errors'].append(f"Validation failed: {prediction_data.get('player1_name')} vs {prediction_data.get('player2_name')}")
                    continue
                
                # Save to database
                prediction_id = save_prediction(
                    player1_name=prediction_data['player1_name'],
                    player2_name=prediction_data['player2_name'],
                    predicted_winner_name=prediction_data['predicted_winner'],
                    tournament_name=prediction_data['tournament_name'],
                    match_datetime=prediction_data['match_datetime'],
                    matchstat_url=prediction_data['matchstat_url'],
                    surface=prediction_data.get('surface'),
                    tour_type=prediction_data.get('tour_type'),
                    raw_prediction_text=prediction_data.get('raw_prediction_text'),
                    prediction_summary=prediction_data.get('prediction_summary')
                )
                
                if prediction_id:
                    stats['saved'] += 1
                    logger.info(f"  💾 NEW - Saved to database (ID: {prediction_id})")
                else:
                    logger.info(f"  ⊘ Already in database")
                
            except Exception as e:
                logger.error(f"Error processing prediction {i}: {e}")
                stats['failed'] += 1
                stats['errors'].append(str(e))
        
        # Summary
        execution_time = time.time() - start_time
        
        logger.info("\n" + "="*60)
        logger.info("SCRAPING COMPLETE")
        logger.info("="*60)
        logger.info(f"Predictions found: {stats['found']}")
        logger.info(f"New predictions saved: {stats['saved']}")
        logger.info(f"Failed/Skipped: {stats['failed']}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        
        # Send Telegram notification if predictions saved
        if stats['saved'] > 0:
            try:
                from src.notifications import get_notifier
                notifier = get_notifier()
                if notifier:
                    message = f"🎾 <b>{stats['saved']} New Prediction{'s' if stats['saved'] > 1 else ''}</b>\n\n"
                    message += f"✓ Found {stats['found']} total predictions\n"
                    message += f"💾 Saved {stats['saved']} new to database\n"
                    message += f"🤖 Source: Grok AI\n"
                    message += f"⏰ {datetime.now().strftime('%H:%M %p')}"
                    notifier.send_message(message)
                    logger.info("✓ Telegram notification sent")
            except Exception as e:
                logger.warning(f"Could not send Telegram notification: {e}")
        
        # Log to database
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


if __name__ == '__main__':
    main()
