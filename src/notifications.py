"""
Telegram notifications for predictions and results
"""
import requests
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram Bot"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Bot token from @BotFather
            chat_id: Your Telegram chat ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a message to Telegram
        
        Args:
            text: Message text (supports HTML formatting)
            parse_mode: 'HTML' or 'Markdown'
        
        Returns:
            bool: True if sent successfully
        """
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info("✓ Telegram notification sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def notify_new_predictions(self, predictions: list) -> bool:
        """
        Notify about new predictions scraped
        
        Args:
            predictions: List of prediction dicts
        
        Returns:
            bool: True if sent successfully
        """
        if not predictions:
            return False
        
        count = len(predictions)
        
        message = f"🎾 <b>{count} New Prediction{'s' if count > 1 else ''}</b>\n\n"
        
        for i, pred in enumerate(predictions[:5], 1):  # Limit to 5 to avoid long messages
            player1 = pred.get('player1_name', 'Unknown')
            player2 = pred.get('player2_name', 'Unknown')
            winner = pred.get('predicted_winner_name', 'Unknown')
            tournament = pred.get('tournament_name', 'Unknown')
            surface = pred.get('surface', 'Unknown')
            
            # Calculate implied probability from odds if available
            summary = pred.get('prediction_summary', {})
            probability = summary.get('win_probability')
            
            message += f"<b>{i}. {player1} vs {player2}</b>\n"
            message += f"   📍 {tournament} ({surface})\n"
            message += f"   🎯 Predicted: <b>{winner}</b>"
            
            if probability:
                message += f" ({probability}%)"
            
            message += "\n\n"
        
        if count > 5:
            message += f"<i>... and {count - 5} more</i>\n\n"
        
        message += f"⏰ {datetime.now().strftime('%H:%M %p')}"
        
        return self.send_message(message)
    
    def notify_results(self, results: list) -> bool:
        """
        Notify about prediction results
        
        Args:
            results: List of result dicts with prediction_correct, roi, etc.
        
        Returns:
            bool: True if sent successfully
        """
        if not results:
            return False
        
        correct = sum(1 for r in results if r.get('prediction_correct'))
        total = len(results)
        accuracy = round((correct / total) * 100, 1) if total > 0 else 0
        total_roi = sum(r.get('roi', 0) for r in results)
        
        message = f"📊 <b>Results Update</b>\n\n"
        message += f"✅ Correct: {correct}/{total} ({accuracy}%)\n"
        message += f"💰 ROI: "
        
        if total_roi >= 0:
            message += f"+{total_roi} KSH ✅\n\n"
        else:
            message += f"{total_roi} KSH ❌\n\n"
        
        # Show individual results
        for r in results[:5]:
            player1 = r.get('player1_name', 'Unknown')
            player2 = r.get('player2_name', 'Unknown')
            predicted = r.get('predicted_winner_name', 'Unknown')
            actual = r.get('actual_winner_name', 'Unknown')
            correct = r.get('prediction_correct', False)
            roi = r.get('roi', 0)
            
            icon = "✅" if correct else "❌"
            message += f"{icon} {player1} vs {player2}\n"
            message += f"   Predicted: {predicted}\n"
            message += f"   Winner: {actual}\n"
            message += f"   ROI: {'+' if roi >= 0 else ''}{roi} KSH\n\n"
        
        if len(results) > 5:
            message += f"<i>... and {len(results) - 5} more</i>\n\n"
        
        message += f"⏰ {datetime.now().strftime('%H:%M %p')}"
        
        return self.send_message(message)
    
    def notify_daily_summary(self, stats: dict) -> bool:
        """
        Send daily performance summary
        
        Args:
            stats: Dictionary with performance metrics
        
        Returns:
            bool: True if sent successfully
        """
        message = f"📈 <b>Daily Summary</b>\n\n"
        message += f"📊 Total Predictions: {stats.get('total', 0)}\n"
        message += f"✅ Win Rate: {stats.get('accuracy', 0)}%\n"
        message += f"💰 Total ROI: "
        
        total_roi = stats.get('total_roi', 0)
        if total_roi >= 0:
            message += f"+{total_roi} KSH ✅\n"
        else:
            message += f"{total_roi} KSH ❌\n"
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """Test if Telegram bot is configured correctly"""
        return self.send_message("🎾 <b>Tennis Tracker Connected!</b>\n\nYou'll receive notifications here.")


def get_notifier() -> Optional[TelegramNotifier]:
    """
    Get configured Telegram notifier from environment
    
    Returns:
        TelegramNotifier instance or None if not configured
    """
    from src.config import Config
    
    bot_token = getattr(Config, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(Config, 'TELEGRAM_CHAT_ID', None)
    
    if bot_token and chat_id:
        return TelegramNotifier(bot_token, chat_id)
    else:
        logger.debug("Telegram notifications not configured")
        return None
