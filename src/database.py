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
            print("Initializing database connection pool...", flush=True)
            
            # Get database URL and clean it
            db_url = Config.DATABASE_URL.strip()
            
            # Remove sslmode from URL if present (we'll add it separately)
            if '?sslmode=' in db_url or '&sslmode=' in db_url:
                # Split URL and query parameters
                if '?' in db_url:
                    base_url, query = db_url.split('?', 1)
                    # Remove sslmode parameter
                    params = [p for p in query.split('&') if not p.startswith('sslmode=')]
                    if params:
                        db_url = base_url + '?' + '&'.join(params)
                    else:
                        db_url = base_url
            
            # Create pool with SSL mode as parameter
            _pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=db_url,
                sslmode='require'
            )
            print("✓ Database connection pool created successfully", flush=True)
            logger.info("✓ Database connection pool created")
        except Exception as e:
            error_msg = f"Failed to create database connection pool: {e}"
            print(f"FATAL DATABASE ERROR: {error_msg}", flush=True)
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
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
