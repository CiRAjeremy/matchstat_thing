#!/usr/bin/env python3
"""
Wrapper script for predictions scraper with proper error handling
Used by GitHub Actions to provide better error reporting
"""
import sys
import traceback

if __name__ == '__main__':
    try:
        print("Starting predictions scraper...", flush=True)
        
        # Try Selenium scraper directly (Groq doesn't have web access)
        from src.scrapers import matchstat_selenium
        matchstat_selenium.main()
        
        print("Predictions scraper completed successfully", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"FATAL ERROR in predictions scraper:", flush=True)
        print(f"Error type: {type(e).__name__}", flush=True)
        print(f"Error message: {str(e)}", flush=True)
        print("\nFull traceback:", flush=True)
        traceback.print_exc()
        sys.exit(1)
