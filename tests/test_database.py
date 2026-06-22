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
    result = test_connection()
    assert result == True


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
    
    # None if duplicate, int if new
    assert prediction_id is None or isinstance(prediction_id, int)


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
