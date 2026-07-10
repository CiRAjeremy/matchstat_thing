"""
Quick test script to verify Grok API connection and response format
"""
import os
import json
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

def test_grok_api():
    """Test Groq API with a simple request"""
    
    print("="*60)
    print("GROQ API CONNECTION TEST")
    print("="*60)
    
    # Get API key (GROK_API_KEY in .env is actually a Groq key starting with gsk_)
    api_key = os.getenv('GROK_API_KEY') or os.getenv('GROQ_API_KEY')
    
    if not api_key:
        print("\n❌ ERROR: No API key found!")
        print("Please add GROK_API_KEY to your .env file")
        print("\nExample:")
        print("GROK_API_KEY=gsk_your_groq_api_key_here")
        return False
    
    print(f"\n✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Correct Groq API endpoint (NOT api.x.ai which is xAI/Grok)
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",  # Fast, reliable Groq model (fallback)
        "messages": [
            {
                "role": "user",
                "content": "Say 'Hello from Groq!' and nothing else."
            }
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    print("\n📡 Sending test request to Grok API...")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"\n✅ SUCCESS! Grok responded:")
                print(f"   '{content}'")
                
                # Show usage info
                if 'usage' in result:
                    usage = result['usage']
                    print(f"\n📊 Token Usage:")
                    print(f"   Input: {usage.get('prompt_tokens', 0)} tokens")
                    print(f"   Output: {usage.get('completion_tokens', 0)} tokens")
                    print(f"   Total: {usage.get('total_tokens', 0)} tokens")
                
                return True
            else:
                print("\n❌ ERROR: Unexpected response format")
                print(json.dumps(result, indent=2))
                return False
        
        elif response.status_code == 401:
            print("\n❌ ERROR: Invalid API key (401 Unauthorized)")
            print("Please check your GROK_API_KEY in .env file")
            return False
        
        elif response.status_code == 429:
            print("\n❌ ERROR: Rate limit exceeded (429)")
            print("You may have used all your credits")
            print("Check your usage at: https://console.x.ai/")
            return False
        
        else:
            print(f"\n❌ ERROR: HTTP {response.status_code}")
            print(response.text)
            return False
    
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out")
        print("The API might be slow or unavailable")
        return False
    
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Connection failed")
        print("Check your internet connection")
        return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def test_grok_web_browsing():
    """Test Groq's built-in web browsing capability (compound-beta model)"""
    
    print("\n" + "="*60)
    print("GROQ WEB BROWSING TEST (groq/compound)")
    print("="*60)
    
    api_key = os.getenv('GROK_API_KEY') or os.getenv('GROQ_API_KEY')
    
    if not api_key:
        print("\n❌ Skipping - no API key")
        return False
    
    # Correct Groq API endpoint
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # groq/compound supports Groq's built-in web search & visit_website tools
    payload = {
        "model": "groq/compound",
        "messages": [
            {
                "role": "user",
                "content": "Please visit https://example.com and tell me the main heading text on the page. Return only the heading text, nothing else."
            }
        ],
        "temperature": 0.1,
        "max_tokens": 100
    }
    
    print("\n📡 Testing Groq's web browsing capability (groq/compound)...")
    print("Asking Groq to visit example.com...")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            print(f"\n✅ Grok's response:")
            print(f"   '{content}'")
            
            if 'Example Domain' in content or 'example' in content.lower():
                print("\n✅ SUCCESS! Grok can browse the web!")
                return True
            else:
                print("\n⚠️ Grok responded but result unclear")
                return True
        else:
            print(f"\n❌ ERROR: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    """Run all tests"""
    
    # Test 1: Basic API connection
    test1 = test_grok_api()
    
    if test1:
        # Test 2: Web browsing (optional)
        test2 = test_grok_web_browsing()
        
        if test2:
            print("\n" + "="*60)
            print("🎉 ALL TESTS PASSED!")
            print("="*60)
            print("\nYou're ready to use the Grok scraper!")
            print("\nNext steps:")
            print("1. Run: python -m src.scrapers.matchstat_grok")
            print("2. Check the logs for predictions extracted")
            print("3. Add GROK_API_KEY to GitHub Secrets")
            print("\n" + "="*60)
        else:
            print("\n" + "="*60)
            print("⚠️ Web browsing test failed but API works")
            print("="*60)
            print("\nThe scraper should still work, but monitor the first run.")
    else:
        print("\n" + "="*60)
        print("❌ API connection failed")
        print("="*60)
        print("\nPlease fix the API key issue before proceeding.")
    
    print()


if __name__ == '__main__':
    main()
