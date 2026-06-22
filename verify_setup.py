#!/usr/bin/env python
"""
Setup verification script
Checks that everything is properly configured before running scrapers
"""
import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if all required packages are installed"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'requests',
        'beautifulsoup4',
        'psycopg2',
        'dotenv',
        'tabulate',
        'pandas',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed\n")
    return True


def check_env_file():
    """Check if .env file exists and has required variables"""
    print("🔧 Checking environment configuration...")
    
    env_file = Path('.env')
    
    if not env_file.exists():
        print("  ❌ .env file not found")
        print("  Create .env file and add DATABASE_URL")
        return False
    
    print("  ✅ .env file exists")
    
    # Load and check variables
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("  ❌ DATABASE_URL not set in .env")
        return False
    
    print("  ✅ DATABASE_URL configured")
    
    if 'neon' in database_url.lower():
        print("  ✅ Neon database detected")
    
    print("✅ Environment properly configured\n")
    return True


def check_directories():
    """Check if required directories exist"""
    print("📁 Checking directory structure...")
    
    required_dirs = [
        'src',
        'src/scrapers',
        'sql',
        'analysis',
        'tests',
        '.github/workflows',
        'logs',
        'backups'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ⚠️  {dir_path}/ - Creating...")
            path.mkdir(parents=True, exist_ok=True)
            all_exist = False
    
    print("✅ Directory structure ready\n")
    return True


def check_database_connection():
    """Test database connection"""
    print("🗄️  Checking database connection...")
    
    try:
        from src.database import test_connection
        
        if test_connection():
            print("✅ Database connection successful\n")
            return True
        else:
            print("❌ Database connection failed\n")
            return False
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}\n")
        return False


def check_schema():
    """Check if database schema is initialized"""
    print("🔍 Checking database schema...")
    
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Check for main tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('players', 'predictions', 'odds_snapshots', 'scrape_logs')
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        
        expected_tables = ['players', 'predictions', 'odds_snapshots', 'scrape_logs']
        
        if len(tables) == len(expected_tables):
            print(f"  ✅ All tables exist: {', '.join(tables)}")
            print("✅ Database schema initialized\n")
            cur.close()
            conn.close()
            return True
        elif len(tables) == 0:
            print("  ⚠️  No tables found - schema not initialized")
            print("  Run: python setup_database.py")
            cur.close()
            conn.close()
            return False
        else:
            print(f"  ⚠️  Found {len(tables)}/{len(expected_tables)} tables")
            print(f"  Missing: {set(expected_tables) - set(tables)}")
            cur.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking schema: {e}")
        return False


def print_next_steps(all_checks_passed):
    """Print next steps based on verification results"""
    print("\n" + "="*60)
    
    if all_checks_passed:
        print("✨ VERIFICATION COMPLETE - ALL CHECKS PASSED!")
        print("="*60)
        print("\n🚀 You're ready to start scraping!")
        print("\nNext steps:")
        print("  1. Run prediction scraper:")
        print("     python -m src.scrapers.matchstat")
        print()
        print("  2. After 2 days, run results scraper:")
        print("     python -m src.scrapers.flashscore")
        print()
        print("  3. Run analysis (after collecting results):")
        print("     python analysis/roi_calculator.py")
        print()
        print("  4. Set up GitHub Actions:")
        print("     - Push code to GitHub")
        print("     - Add DATABASE_URL secret")
        print("     - Enable workflows")
        
    else:
        print("⚠️  VERIFICATION INCOMPLETE")
        print("="*60)
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Create .env file with DATABASE_URL")
        print("  - Initialize schema: python setup_database.py")
        print()
        print("Then run this script again: python verify_setup.py")


def main():
    """Run all verification checks"""
    print("="*60)
    print("🎾 MATCHSTAT SETUP VERIFICATION")
    print("="*60)
    print()
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_env_file),
        ("Directories", check_directories),
        ("Database Connection", check_database_connection),
        ("Database Schema", check_schema),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Error in {check_name}: {e}\n")
            results.append(False)
    
    all_passed = all(results)
    
    print_next_steps(all_passed)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
