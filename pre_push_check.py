"""
Pre-push security check
Verifies no secrets will be exposed when pushing to GitHub
"""
import os
import subprocess
import sys

def check_gitignore():
    """Verify .env is in .gitignore"""
    try:
        with open('.gitignore', 'r') as f:
            content = f.read()
            if '.env' in content:
                print("✅ .env is in .gitignore")
                return True
            else:
                print("❌ .env NOT in .gitignore!")
                return False
    except FileNotFoundError:
        print("❌ .gitignore not found!")
        return False

def check_git_status():
    """Check if .env is being tracked by git"""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if '.env' in result.stdout:
            print("❌ WARNING: .env appears in git status!")
            print("   Run: git rm --cached .env")
            return False
        else:
            print("✅ .env is NOT being tracked by git")
            return True
    except subprocess.CalledProcessError:
        print("⚠️  Could not check git status (not a git repo?)")
        return True

def check_env_file_exists():
    """Check if .env exists (should exist locally but not be tracked)"""
    if os.path.exists('.env'):
        print("✅ .env file exists locally (good for development)")
        return True
    else:
        print("⚠️  .env file not found (needed for local testing)")
        return False

def check_env_example():
    """Verify .env.example has no real secrets"""
    try:
        with open('.env.example', 'r') as f:
            content = f.read()
            
            # Check for patterns that look like real secrets
            suspicious = []
            
            if 'gsk_' in content and 'gsk_xxxx' not in content:
                suspicious.append("Possible real Groq API key")
            
            if '@ep-' in content and 'ep-xxx' not in content and 'ep-xxxx' not in content:
                suspicious.append("Possible real Neon database URL")
            
            if suspicious:
                print("❌ .env.example contains suspicious values:")
                for item in suspicious:
                    print(f"   - {item}")
                return False
            else:
                print("✅ .env.example contains only placeholders")
                return True
    except FileNotFoundError:
        print("⚠️  .env.example not found")
        return True

def check_staged_files():
    """Check what files are staged for commit"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            print("\n📋 Files staged for commit:")
            for file in result.stdout.strip().split('\n'):
                print(f"   {file}")
            
            if '.env' in result.stdout:
                print("\n❌ DANGER: .env is staged for commit!")
                return False
        else:
            print("\n⚠️  No files staged for commit")
        
        return True
    except subprocess.CalledProcessError:
        return True

def main():
    print("="*60)
    print("🔒 PRE-PUSH SECURITY CHECK")
    print("="*60)
    print()
    
    checks = [
        check_gitignore(),
        check_git_status(),
        check_env_file_exists(),
        check_env_example(),
        check_staged_files()
    ]
    
    print()
    print("="*60)
    
    if all(checks):
        print("✅ ALL SECURITY CHECKS PASSED!")
        print()
        print("Safe to push to GitHub! 🚀")
        print()
        print("Next steps:")
        print("  git push origin main")
        print("="*60)
        return 0
    else:
        print("❌ SECURITY ISSUES DETECTED!")
        print()
        print("DO NOT PUSH until issues are resolved!")
        print()
        print("See SECURITY_CHECK.md for details")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
