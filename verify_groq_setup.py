"""
Quick verification script for Groq API setup
Checks all prerequisites before running the scraper
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_groq_api():
    """Check if Groq API key is configured"""
    api_key = os.getenv('GROK_API_KEY') or os.getenv('GROQ_API_KEY')
    
    if not api_key:
        return False, "❌ No API key found"
    
    if not api_key.startswith('gsk_'):
        return False, f"⚠️ API key should start with 'gsk_' (found: {api_key[:4]}...)"
    
    return True, f"✅ API key found: {api_key[:10]}...{api_key[-4:]}"


def check_database():
    """Check if database is configured"""
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        return False, "❌ DATABASE_URL not found in .env"
    
    if 'postgresql://' not in db_url:
        return False, "⚠️ DATABASE_URL doesn't look like PostgreSQL"
    
    if 'sslmode=require' not in db_url:
        return False, "⚠️ DATABASE_URL should end with ?sslmode=require"
    
    return True, "✅ DATABASE_URL configured"


def check_telegram():
    """Check if Telegram is configured (optional)"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token and not chat_id:
        return None, "ℹ️ Telegram not configured (optional)"
    
    if not bot_token:
        return False, "⚠️ TELEGRAM_CHAT_ID found but TELEGRAM_BOT_TOKEN missing"
    
    if not chat_id:
        return False, "⚠️ TELEGRAM_BOT_TOKEN found but TELEGRAM_CHAT_ID missing"
    
    return True, "✅ Telegram configured"


def main():
    print("="*60)
    print("GROQ API SETUP VERIFICATION")
    print("="*60)
    print()
    
    checks = [
        ("Groq API Key", check_groq_api),
        ("Database", check_database),
        ("Telegram (Optional)", check_telegram),
    ]
    
    results = []
    all_required_pass = True
    
    for name, check_func in checks:
        status, message = check_func()
        results.append((name, status, message))
        
        print(f"{name}:")
        print(f"  {message}")
        print()
        
        # Only Groq API and Database are required
        if name in ["Groq API Key", "Database"] and not status:
            all_required_pass = False
    
    print("="*60)
    
    if all_required_pass:
        print("✅ ALL REQUIRED CHECKS PASSED!")
        print()
        print("Next steps:")
        print("  1. Test API: python test_grok_api.py")
        print("  2. Run scraper: python run_scraper.py")
        print("="*60)
        return 0
    else:
        print("❌ SETUP INCOMPLETE")
        print()
        print("Required fixes:")
        for name, status, message in results:
            if name in ["Groq API Key", "Database"] and not status:
                print(f"  • {message}")
        print()
        print("Setup guide: README.md")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
