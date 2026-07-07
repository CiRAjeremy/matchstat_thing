"""
Simple API server for dashboard
Run with: python dashboard/api.py
"""
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_connection, release_connection

app = Flask(__name__, static_folder='.')
CORS(app)  # Allow cross-origin requests

@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return send_from_directory('.', 'index.html')

@app.route('/api/stats')
def get_stats():
    """Get all dashboard statistics"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Overall stats
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(actual_winner_id) as with_results,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
                ROUND(AVG(roi_prediction_odds), 2) as avg_roi,
                SUM(roi_prediction_odds) as total_roi
            FROM predictions
        """)
        overall = cur.fetchone()
        
        total_predictions = overall[0] or 0
        predictions_with_results = overall[1] or 0
        correct_predictions = overall[2] or 0
        avg_roi = float(overall[3] or 0)
        total_roi = float(overall[4] or 0)
        
        accuracy = round((correct_predictions / predictions_with_results * 100), 1) if predictions_with_results > 0 else 0
        
        # Performance by surface
        cur.execute("""
            SELECT 
                surface,
                COUNT(*) as total,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct
            FROM predictions
            WHERE actual_winner_id IS NOT NULL AND surface IS NOT NULL
            GROUP BY surface
            ORDER BY total DESC
        """)
        by_surface = []
        for row in cur.fetchall():
            surface, total, correct = row
            accuracy_pct = round((correct / total * 100), 1) if total > 0 else 0
            by_surface.append({
                'surface': surface,
                'total': total,
                'correct': correct,
                'accuracy': accuracy_pct
            })
        
        # Daily predictions (last 30 days)
        cur.execute("""
            SELECT 
                prediction_date,
                COUNT(*) as count
            FROM predictions
            WHERE prediction_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY prediction_date
            ORDER BY prediction_date DESC
            LIMIT 30
        """)
        daily_predictions = []
        for row in cur.fetchall():
            date, count = row
            daily_predictions.append({
                'date': date.strftime('%b %d'),
                'count': count
            })
        daily_predictions.reverse()  # Oldest first for chart
        
        # Recent predictions
        cur.execute("""
            SELECT 
                p.prediction_date,
                p1.canonical_name as player1,
                p2.canonical_name as player2,
                pw.canonical_name as predicted_winner,
                aw.canonical_name as actual_winner,
                p.prediction_correct,
                p.roi_prediction_odds,
                p.match_status
            FROM predictions p
            JOIN players p1 ON p.player1_id = p1.id
            JOIN players p2 ON p.player2_id = p2.id
            JOIN players pw ON p.predicted_winner_id = pw.id
            LEFT JOIN players aw ON p.actual_winner_id = aw.id
            ORDER BY p.prediction_date DESC, p.created_at DESC
            LIMIT 20
        """)
        recent_predictions = []
        for row in cur.fetchall():
            date, player1, player2, predicted, actual, correct, roi, status = row
            
            if actual:
                status_text = '✓ Correct' if correct else '✗ Wrong'
                status_class = 'correct' if correct else 'wrong'
            else:
                status_text = '⏳ Pending'
                status_class = 'pending'
            
            recent_predictions.append({
                'date': date.strftime('%Y-%m-%d'),
                'player1': player1,
                'player2': player2,
                'predicted_winner': predicted,
                'actual_winner': actual or '-',
                'status_text': status_text,
                'status': status_class,
                'roi': float(roi) if roi is not None else None
            })
        
        return jsonify({
            'total_predictions': total_predictions,
            'predictions_with_results': predictions_with_results,
            'correct_predictions': correct_predictions,
            'accuracy': accuracy,
            'avg_roi': avg_roi,
            'total_roi': total_roi,
            'by_surface': by_surface,
            'daily_predictions': daily_predictions,
            'recent_predictions': recent_predictions,
            'last_updated': datetime.now().isoformat()
        })
        
    finally:
        cur.close()
        release_connection(conn)

if __name__ == '__main__':
    print("🎾 Starting dashboard server...")
    print("📊 Dashboard: http://localhost:8080")
    print("🔌 API: http://localhost:8080/api/stats")
    print()
    app.run(debug=True, host='0.0.0.0', port=8080)
