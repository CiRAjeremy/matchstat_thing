#!/usr/bin/env python
"""
Database setup script
Initializes the Neon database with schema
"""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Initialize database schema"""
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env file")
        sys.exit(1)
    
    print("🔗 Connecting to Neon database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        print("✅ Connected successfully!")
        
        # Read schema file
        schema_path = Path('sql/schema.sql')
        if not schema_path.exists():
            print(f"❌ ERROR: Schema file not found: {schema_path}")
            sys.exit(1)
        
        print(f"📄 Reading schema from {schema_path}...")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("🔨 Creating database schema...")
        
        # Execute schema
        cur.execute(schema_sql)
        conn.commit()
        
        print("✅ Schema created successfully!")
        
        # Verify tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        
        print("\n📊 Created tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Get version
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"\n💾 PostgreSQL version: {version.split(',')[0]}")
        
        cur.close()
        conn.close()
        
        print("\n✨ Database setup complete!")
        print("\n📝 Next steps:")
        print("  1. Test connection: python -c \"from src.database import test_connection; test_connection()\"")
        print("  2. Run scraper: python -m src.scrapers.matchstat")
        print("  3. Check data: SELECT * FROM predictions_view;")
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    print("="*60)
    print("🎾 MATCHSTAT DATABASE SETUP")
    print("="*60)
    print()
    
    setup_database()
