"""
Vercel Serverless Function to fetch dashboard stats from PostgreSQL
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2
from urllib.parse import urlparse


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET request for stats"""
        try:
            # Get database URL from environment
            database_url = os.environ.get('DATABASE_URL')
            
            if not database_url:
                self.send_error(500, "DATABASE_URL not configured")
                return
            
            # Parse connection string
            result = urlparse(database_url)
            
            # Connect to database
            conn = psycopg2.connect(
                host=result.hostname,
                port=result.port or 5432,
                user=result.username,
                password=result.password,
                database=result.path[1:],  # Remove leading slash
                sslmode='require'
            )
            cur = conn.cursor()
            
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
            
            # Build response
            data = {
                'total_predictions': total_predictions,
                'predictions_with_results': predictions_with_results,
                'correct_predictions': correct_predictions,
                'accuracy': accuracy,
                'avg_roi': avg_roi,
                'total_roi': total_roi,
                'by_surface': by_surface,
                'daily_predictions': daily_predictions,
                'recent_predictions': recent_predictions
            }
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
            cur.close()
            conn.close()
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
