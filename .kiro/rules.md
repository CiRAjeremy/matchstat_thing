# 🤖 LLM Instructions for This Project

## Core Principle: KEEP IT SIMPLE

This project should remain **lean and maintainable**. Follow these rules strictly.

---

## 📁 File Structure Rules

### ✅ ALLOWED Files

**Core Application:**
- `src/` - Source code only
- `analysis/` - Analysis scripts
- `sql/` - Database schemas
- `.github/workflows/` - CI/CD automation
- `dashboard/` - Dashboard files (max 2-3 files)
- `logs/` - Runtime logs (gitignored)

**Configuration:**
- `.env` (local, gitignored)
- `.env.example` (template)
- `requirements.txt`
- `.gitignore`

**Documentation (MAX 3 FILES):**
- `README.md` - Quick start, usage, commands
- `ARCHITECTURE.md` - System design & how it works
- `.kiro/rules.md` - This file

### ❌ FORBIDDEN Files

**No Multiple READMEs:**
- ❌ `QUICKSTART.md` - merge into README.md
- ❌ `START_HERE.md` - merge into README.md
- ❌ `GETTING_STARTED.md` - merge into README.md

**No Status/Summary Files:**
- ❌ `STATUS.md` - merge into README.md
- ❌ `SUMMARY.md` - merge into README.md
- ❌ `CHANGELOG.md` - use git commits

**No Planning Docs:**
- ❌ `PLAN1.md`, `PLAN2.md`, etc. - delete after implementation
- ❌ `TODO.md` - use GitHub issues or comments in code
- ❌ `NOTES.md` - temporary only, delete when done

**No Setup Guides:**
- ❌ `SETUP.md` - merge into README.md
- ❌ `INSTALLATION.md` - merge into README.md
- ❌ `DEPLOYMENT.md` - merge into README.md or ARCHITECTURE.md

**No Empty/Placeholder Folders:**
- ❌ `tests/` if no tests exist
- ❌ `backups/` if unused
- ❌ `tmp/`, `temp/`, `scratch/`

---

## 📝 Documentation Rules

### When User Says "Improve Documentation"

1. **Update existing files** - Don't create new ones!
2. **Consolidate** - Merge similar docs
3. **Delete** - Remove outdated docs

### Documentation Structure

**README.md should contain:**
- What the project does (2-3 sentences)
- Quick start (install, run, test)
- Common commands
- Troubleshooting
- Links to detailed docs

**ARCHITECTURE.md should contain:**
- System overview diagram (ASCII art is fine)
- How components interact
- Data flow
- Design decisions & why
- Critical code paths

**DO NOT create separate files for:**
- Setup instructions → README.md
- API documentation → Docstrings in code
- Configuration → Comments in config files
- Troubleshooting → README.md

---

## 🔧 Code Rules

### File Organization

```
src/
├── scrapers/          # One file per scraper
│   ├── matchstat_selenium.py
│   └── flashscore.py
├── database.py        # All database operations
├── config.py          # Configuration management
├── notifications.py   # Notification system
└── utils.py           # Shared utilities
```

**Rules:**
- ❌ Don't create `helpers/`, `lib/`, `common/` folders
- ❌ Don't split one feature across multiple files
- ✅ Keep related code together
- ✅ One file per clear responsibility

### When Adding Features

**BEFORE creating new files, ask:**
1. Can this go in an existing file?
2. Does this file have ONE clear purpose?
3. Will future-me understand why this file exists?

**If creating new file:**
- Add clear docstring explaining purpose
- Update ARCHITECTURE.md with how it fits

---

## 🧪 Testing Rules

**Tests are optional for this project!**

If adding tests:
- ✅ Put in `tests/` folder
- ✅ Name: `test_<module>.py`
- ❌ Don't create `tests/unit/`, `tests/integration/` unless >10 test files

---

## 📦 Dependencies Rules

**Keep dependencies minimal!**

**Before adding a new package:**
1. Can I do this with stdlib?
2. Is there a lighter alternative?
3. Does this justify the extra weight?

**Don't add:**
- ❌ Heavy frameworks when simple libraries work
- ❌ Type checkers (mypy, pyright) - overkill for this project
- ❌ Code formatters (black, prettier) - unnecessary complexity
- ❌ Linters (pylint, flake8) - keep it simple

---

## 🚫 What NOT to Do

### ❌ Don't Over-Engineer

**User says:** "Add error handling"
- ✅ Add try-catch where needed
- ❌ Don't create error classes, error handlers, error middleware

**User says:** "Add logging"
- ✅ Use Python's logging module
- ❌ Don't create logging framework, formatters, handlers

**User says:** "Make it configurable"
- ✅ Add config option to existing config.py
- ❌ Don't create config system, validators, schema

### ❌ Don't Create Abstractions Prematurely

**Bad:**
```python
class BaseScraperStrategy(ABC):
    @abstractmethod
    def scrape(self): pass

class MatchstatScraperStrategy(BaseScraperStrategy):
    def scrape(self): ...
```

**Good:**
```python
def scrape_matchstat():
    """Scrape predictions from Matchstat"""
    ...
```

**Rule:** Only abstract when you have 3+ similar implementations

### ❌ Don't Add "Best Practices" Unless Needed

- ❌ Don't add CI/CD testing if no tests
- ❌ Don't add code coverage tools
- ❌ Don't add pre-commit hooks
- ❌ Don't add docker unless specifically requested
- ❌ Don't add kubernetes config (seriously)

---

## ✅ What TO Do

### When User Asks to "Improve the Project"

**Priority order:**
1. **Fix bugs** in existing code
2. **Consolidate** duplicate functionality
3. **Delete** unused code/files
4. **Document** complex parts
5. **Add features** only if user explicitly wants them

### When User Asks "Make it Better"

**Ask specific questions:**
- "Better in what way? Performance? Usability? Features?"
- "What problem are you trying to solve?"
- "What's not working for you right now?"

**Don't assume:**
- User wants more features
- User wants more files
- User wants "enterprise" architecture

### Default Response

**User:** "Improve this"
**You:** "The code is working well. What specific problem are you facing?"

---

## 📊 Example: Good vs Bad File Structure

### ❌ BAD (Over-complicated)

```
project/
├── docs/
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── SETUP.md
│   ├── API.md
│   ├── TROUBLESHOOTING.md
│   └── CONTRIBUTING.md
├── src/
│   ├── core/
│   ├── utils/
│   ├── helpers/
│   ├── lib/
│   └── common/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
├── tools/
└── etc/
```

### ✅ GOOD (Simple & Clear)

```
project/
├── src/              # Source code
├── analysis/         # Analysis scripts
├── dashboard/        # Dashboard files
├── .github/          # CI/CD
├── README.md         # Start here
├── ARCHITECTURE.md   # How it works
└── requirements.txt  # Dependencies
```

---

## 🎯 Summary

**Golden Rules:**
1. **Maximum 3 documentation files**
2. **Consolidate, don't proliferate**
3. **Delete unused code/files**
4. **Simple > Complex**
5. **Working > Perfect**

**When in doubt:**
- Choose simplicity
- Ask before adding
- Delete before creating

**Remember:**
This is a **personal project**, not an enterprise system. Keep it maintainable for one person (the user) who might revisit it months later.

---

## 🚨 Enforcement

**If you (LLM) violate these rules:**
- User will delete your generated files
- User will revert your commits
- User will be frustrated

**If user says "you're creating too many files":**
- Stop immediately
- Apologize
- Ask which files to keep
- Delete the rest

---

**Last Updated:** June 2026
**Maintained By:** The actual human using this project
