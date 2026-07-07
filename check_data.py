"""
Quick script to check what data you have for the dashboard
"""
from src.database import get_connection, release_connection

conn = get_connection()
cur = conn.cursor()

print("="*60)
print("📊 DASHBOARD DATA CHECK")
print("="*60)

# Total predictions
cur.execute("SELECT COUNT(*) FROM predictions")
total = cur.fetchone()[0]
print(f"\n✓ Total Predictions: {total}")

# With results
cur.execute("SELECT COUNT(*) FROM predictions WHERE actual_winner_id IS NOT NULL")
with_results = cur.fetchone()[0]
print(f"✓ With Results: {with_results}")

# By date
cur.execute("""
    SELECT prediction_date, COUNT(*) as count
    FROM predictions
    GROUP BY prediction_date
    ORDER BY prediction_date DESC
    LIMIT 10
""")
print(f"\n📅 Predictions by Date:")
for row in cur.fetchall():
    date, count = row
    print(f"   {date}: {count} predictions")

# Recent predictions
cur.execute("""
    SELECT 
        p.prediction_date,
        p1.canonical_name as player1,
        p2.canonical_name as player2,
        pw.canonical_name as predicted_winner,
        CASE WHEN p.actual_winner_id IS NOT NULL THEN 'Has result' ELSE 'Pending' END as status
    FROM predictions p
    JOIN players p1 ON p.player1_id = p1.id
    JOIN players p2 ON p.player2_id = p2.id
    JOIN players pw ON p.predicted_winner_id = pw.id
    ORDER BY p.created_at DESC
    LIMIT 5
""")
print(f"\n🎾 Recent Predictions:")
for row in cur.fetchall():
    date, p1, p2, predicted, status = row
    print(f"   {date}: {p1} vs {p2} → {predicted} ({status})")

if total == 0:
    print("\n⚠️ No predictions in database yet!")
    print("   Run: python -m src.scrapers.matchstat_selenium")
elif total < 5:
    print(f"\n💡 Only {total} prediction(s) - dashboard will work but look sparse.")
    print("   Wait for GitHub Actions to collect more (or run scraper manually)")
else:
    print(f"\n✅ You have {total} predictions - dashboard will look good!")

cur.close()
release_connection(conn)

print("\n" + "="*60)
print("To run dashboard: python dashboard/api.py")
print("="*60)
