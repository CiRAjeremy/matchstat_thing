"""
Matchstat Scraper - Groq API Only
Uses Groq's built-in visit_website tool to extract predictions without manual scraping
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    """Run the Groq AI scraper"""
    
    print("="*60)
    print("MATCHSTAT SCRAPER - GROQ API")
    print("="*60)
    
    # Check for Groq API key
    api_key = os.getenv('GROK_API_KEY') or os.getenv('GROQ_API_KEY')
    
    if not api_key:
        print("\n[X] ERROR: Groq API key not found!")
        print("\n[*] Setup Instructions:")
        print("1. Get your API key from: https://console.groq.com/keys")
        print("2. Add to .env file: GROK_API_KEY=gsk_your_api_key_here")
        print("3. Run: python test_grok_api.py (to verify)")
        print("4. Run: python run_scraper.py (this script)")
        print("\n[!] Note: The API key starts with 'gsk_' (Groq, not xAI)")
        print("="*60)
        sys.exit(1)
    
    print(f"\n[OK] API Key found: {api_key[:10]}...{api_key[-4:]}")
    print("\n[*] Starting Groq AI scraper...")
    print("   * Uses groq/compound model with built-in web browsing")
    print("   * Bypasses Cloudflare automatically")
    print("   * No headless browser needed")
    print("="*60 + "\n")
    
    # Run Groq scraper
    from src.scrapers import matchstat_grok
    matchstat_grok.main()


if __name__ == '__main__':
    main()
