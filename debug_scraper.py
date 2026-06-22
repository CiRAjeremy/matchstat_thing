#!/usr/bin/env python
"""
Debug script to inspect Matchstat homepage HTML
"""
import requests
from bs4 import BeautifulSoup
from src.utils import get_headers

print("🔍 Debugging Matchstat Homepage Structure\n")

# Fetch the page
url = "https://matchstat.com/"
print(f"Fetching: {url}")

response = requests.get(url, headers=get_headers(), timeout=10)
print(f"Status code: {response.status_code}")
print(f"Page size: {len(response.text)} characters\n")

soup = BeautifulSoup(response.text, 'html.parser')

# Check for various selectors
selectors_to_test = {
    'prediction_cards': 'div.flex.w-full.justify-between.items-center',
    'player_links': 'a[href*="/tennis/player/"]',
    'h2h_links': 'a[href*="h2h-odds-bets"]',
    'any_divs_with_flex': 'div[class*="flex"]',
    'any_links': 'a',
}

print("Testing CSS Selectors:")
print("=" * 60)

for name, selector in selectors_to_test.items():
    elements = soup.select(selector)
    print(f"{name:30} → Found {len(elements)} elements")
    
    if len(elements) > 0 and len(elements) < 5:
        # Show sample
        for i, elem in enumerate(elements[:2], 1):
            text = elem.get_text(strip=True)[:80]
            href = elem.get('href', 'N/A')[:50]
            print(f"  Sample {i}: text='{text}' href='{href}'")
    print()

# Check if page requires JavaScript
if 'nextjs' in response.text.lower() or 'react' in response.text.lower():
    print("⚠️ WARNING: Page appears to use JavaScript rendering (Next.js/React)")
    print("   The scraper may need Selenium or Playwright to render the page properly")
    print()

# Look for any text that indicates predictions
prediction_keywords = ['prediction', 'will win', 'will play', 'expert predictions']
print("Searching for prediction-related text:")
print("=" * 60)

for keyword in prediction_keywords:
    if keyword.lower() in response.text.lower():
        # Find context around keyword
        idx = response.text.lower().find(keyword.lower())
        context = response.text[max(0, idx-50):idx+100]
        print(f"✓ Found '{keyword}': ...{context}...")
        print()

# Check for login/paywall indicators
paywall_keywords = ['register', 'login', 'sign in', 'sign up', 'subscribe']
print("\nChecking for paywall/login requirements:")
print("=" * 60)

for keyword in paywall_keywords:
    count = response.text.lower().count(keyword.lower())
    if count > 0:
        print(f"✓ Found '{keyword}' {count} times")

# Save a sample of the HTML for inspection
sample_file = 'logs/homepage_sample.html'
with open(sample_file, 'w', encoding='utf-8') as f:
    f.write(response.text)
print(f"\n💾 Full HTML saved to: {sample_file}")
print("   Open this file in a browser to see what the scraper sees")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
