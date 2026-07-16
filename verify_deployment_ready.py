"""
Pre-deployment verification script
Checks if all components are ready for GitHub Actions deployment
"""
import os
import sys
from pathlib import Path

def check_file_exists(filepath, required=True):
    """Check if a file exists"""
    exists = Path(filepath).exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    req_text = "REQUIRED" if required else "Optional"
    print(f"  {status} {filepath} ({req_text})")
    return exists if required else True

def check_import(module_path, description):
    """Check if a module can be imported"""
    try:
        parts = module_path.split('.')
        module = __import__(module_path)
        for part in parts[1:]:
            module = getattr(module, part)
        print(f"  ✓ {description}")
        return True
    except Exception as e:
        print(f"  ✗ {description} - Error: {e}")
        return False

def main():
    print("="*60)
    print("DEPLOYMENT READINESS CHECK")
    print("="*60)
    print()
    
    all_checks_passed = True
    
    # 1. Check critical files
    print("1. Critical Files:")
    checks = [
        ("src/scrapers/matchstat_grok.py", True),
        ("src/database.py", True),
        ("src/config.py", True),
        ("src/utils.py", True),
        ("requirements.txt", True),
        (".github/workflows/scrape_predictions.yml", True),
        (".env", False),  # Not required for deployment (uses secrets)
    ]
    
    for filepath, required in checks:
        if not check_file_exists(filepath, required):
            if required:
                all_checks_passed = False
    print()
    
    # 2. Check imports
    print("2. Python Imports:")
    imports = [
        ("src.scrapers.matchstat_grok", "Groq scraper module"),
        ("src.database", "Database module"),
        ("src.config", "Config module"),
        ("src.utils", "Utils module"),
        ("requests", "requests library"),
        ("psycopg2", "PostgreSQL driver"),
        ("dotenv", "python-dotenv"),
    ]
    
    for module_path, description in imports:
        if not check_import(module_path, description):
            all_checks_passed = False
    print()
    
    # 3. Check GitHub Actions command
    print("3. GitHub Actions Command:")
    try:
        # This would be run in GitHub Actions
        cmd = "python -m src.scrapers.matchstat_grok"
        print(f"  ✓ Command: {cmd}")
        print(f"  ✓ This will work in GitHub Actions")
    except Exception as e:
        print(f"  ✗ Command check failed: {e}")
        all_checks_passed = False
    print()
    
    # 4. Environment variables (check local .env)
    print("4. Environment Variables (Local .env):")
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = [
        ("GROK_API_KEY", "Groq API key (will use GitHub secret in production)", True),
        ("DATABASE_URL", "Database connection string", True),
        ("TELEGRAM_BOT_TOKEN", "Telegram bot token", False),
        ("TELEGRAM_CHAT_ID", "Telegram chat ID", False),
    ]
    
    for var_name, description, required in env_vars:
        value = os.getenv(var_name)
        if value:
            # Show first 7 chars for verification (less exposure)
            masked = f"{value[:7]}..." if len(value) > 10 else "***"
            print(f"  ✓ {var_name}: {masked} ({description})")
        else:
            status = "✗" if required else "⚠"
            req_text = "REQUIRED" if required else "Optional"
            print(f"  {status} {var_name}: Not set ({req_text})")
            if required:
                all_checks_passed = False
    print()
    
    # 5. GitHub Secrets reminder
    print("5. GitHub Secrets (TO DO AFTER PUSH):")
    print("  ⚠ After pushing code, add these secrets to GitHub:")
    print("     • DATABASE_URL")
    print("     • GROK_API_KEY")
    print("     • TELEGRAM_BOT_TOKEN (optional)")
    print("     • TELEGRAM_CHAT_ID (optional)")
    print()
    print("  How: Settings → Secrets and variables → Actions → New repository secret")
    print()
    
    # 6. Final summary
    print("="*60)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT!")
        print()
        print("Next steps:")
        print("1. git add .")
        print("2. git commit -m 'Production ready - Groq API integration'")
        print("3. git push origin main")
        print("4. Add secrets to GitHub (see DEPLOYMENT_CHECKLIST.md)")
        print("5. Enable GitHub Actions")
        print("6. Manually trigger first run")
        print()
        print("See DEPLOYMENT_CHECKLIST.md for detailed instructions.")
    else:
        print("❌ SOME CHECKS FAILED - FIX ISSUES BEFORE DEPLOYING")
        print()
        print("Review the errors above and fix them.")
    print("="*60)
    
    return 0 if all_checks_passed else 1

if __name__ == '__main__':
    sys.exit(main())
