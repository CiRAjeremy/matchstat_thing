#!/usr/bin/env python3
"""
Test script to verify scraper configuration and connections
Run this before deploying to GitHub Actions
"""
import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_environment_variables():
    """Check all required environment variables"""
    print("\n" + "="*60)
    print("TESTING ENVIRONMENT VARIABLES")
    print("="*60)
    
    required = {
        'DATABASE_URL': 'Database connection string',
        'GROK_API_KEY': 'Groq API key for predictions',
    }
    
    optional = {
        'TELEGRAM_BOT_TOKEN': 'Telegram bot token',
        'TELEGRAM_CHAT_ID': 'Telegram chat ID',
        'LOG_LEVEL': 'Logging level',
    }
    
    missing = []
    
    print("\nRequired variables:")
    for var, desc in required.items():
        value = os.getenv(var)
        if value:
            # Show partial value for security
            display = f"{value[:15]}...{value[-10:]}" if len(value) > 30 else value[:20] + "..."
            print(f"  ✓ {var}: {display}")
        else:
            print(f"  ✗ {var}: NOT SET ({desc})")
            missing.append(var)
    
    print("\nOptional variables:")
    for var, desc in optional.items():
        value = os.getenv(var)
        if value:
            display = f"{value[:10]}..." if len(value) > 10 else value
            print(f"  ✓ {var}: {display}")
        else:
            print(f"  - {var}: not set ({desc})")
    
    if missing:
        print(f"\n✗ Missing {len(missing)} required variable(s)")
        return False
    
    print("\n✓ All required variables set")
    return True


def test_database_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("TESTING DATABASE CONNECTION")
    print("="*60)
    
    try:
        from src.database import test_connection
        result = test_connection()
        if result:
            print("\n✓ Database connection successful")
            return True
        else:
            print("\n✗ Database connection failed")
            return False
    except Exception as e:
        print(f"\n✗ Database connection error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_groq_api():
    """Test Groq API key"""
    print("\n" + "="*60)
    print("TESTING GROQ API")
    print("="*60)
    
    try:
        import requests
        
        api_key = os.getenv('GROK_API_KEY') or os.getenv('GROQ_API_KEY')
        if not api_key:
            print("✗ No Groq API key found")
            return False
        
        print(f"API key: {api_key[:10]}...{api_key[-4:]}")
        
        # Test simple API call
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "groq/compound-mini",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        
        print("Sending test request to Groq API...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✓ Groq API key valid")
            return True
        else:
            print(f"✗ Groq API returned {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ Groq API test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test that all required modules can be imported"""
    print("\n" + "="*60)
    print("TESTING PYTHON IMPORTS")
    print("="*60)
    
    modules = [
        'requests',
        'bs4',
        'psycopg2',
        'dotenv',
        'src.config',
        'src.database',
        'src.scrapers.matchstat_grok',
        'src.scrapers.flashscore',
    ]
    
    failed = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n✗ Failed to import {len(failed)} module(s)")
        return False
    
    print("\n✓ All modules imported successfully")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SCRAPER SETUP VERIFICATION")
    print("="*60)
    
    results = {
        'Environment Variables': test_environment_variables(),
        'Python Imports': test_imports(),
        'Database Connection': test_database_connection(),
        'Groq API': test_groq_api(),
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Ready for deployment!")
    else:
        print("✗ SOME TESTS FAILED - Fix issues before deploying")
    print("="*60 + "\n")
    
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
