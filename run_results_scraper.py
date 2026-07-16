#!/usr/bin/env python3
"""
Wrapper script for results scraper with proper error handling
Used by GitHub Actions to provide better error reporting
"""
import sys
import traceback
from src.scrapers import flashscore

if __name__ == '__main__':
    try:
        print("Starting results scraper...", flush=True)
        flashscore.main()
        print("Results scraper completed successfully", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"FATAL ERROR in results scraper:", flush=True)
        print(f"Error type: {type(e).__name__}", flush=True)
        print(f"Error message: {str(e)}", flush=True)
        print("\nFull traceback:", flush=True)
        traceback.print_exc()
        sys.exit(1)
