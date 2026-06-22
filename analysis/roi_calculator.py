"""
ROI Analysis and Reporting
Calculate profitability metrics for Matchstat predictions
"""
import logging
from typing import Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from tabulate import tabulate

from src.config import Config
from src.utils import setup_logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════

def get_connection():
    """Get database connection"""
    return psycopg2.connect(Config.DATABASE_URL)


# ═══════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════

def overall_performance():
    """Display overall prediction accuracy and ROI"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                COUNT(*) as total_predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct_predictions,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate_pct,
                
                -- Prediction-time odds ROI
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as total_roi_prediction,
                ROUND(AVG(COALESCE(roi_prediction_odds, 0)), 2) as avg_roi_prediction,
                
                -- Closing odds ROI
                ROUND(SUM(COALESCE(roi_closing_odds, 0)), 2) as total_roi_closing,
                ROUND(AVG(COALESCE(roi_closing_odds, 0)), 2) as avg_roi_closing
                
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
        """)
        
        result = cur.fetchone()
        
        if result['total_predictions'] == 0:
            print("\n⚠️  No completed predictions yet")
            return
        
        # Calculate ROI percentages
        total_staked = result['total_predictions'] * 10  # 10 KSH per bet
        roi_pct_prediction = (result['total_roi_prediction'] / total_staked * 100) if total_staked > 0 else 0
        roi_pct_closing = (result['total_roi_closing'] / total_staked * 100) if total_staked > 0 and result['total_roi_closing'] else 0
        
        print("\n" + "="*60)
        print("📊 OVERALL PERFORMANCE")
        print("="*60)
        print(f"Total Predictions: {result['total_predictions']}")
        print(f"Correct: {result['correct_predictions']}")
        print(f"Win Rate: {result['win_rate_pct']}%")
        print(f"Total Staked: {total_staked} KSH (10 KSH flat bet)")
        print()
        print("ROI (Prediction-Time Odds):")
        print(f"  Total: {result['total_roi_prediction']:+.2f} KSH")
        print(f"  Per Bet: {result['avg_roi_prediction']:+.2f} KSH")
        print(f"  ROI %: {roi_pct_prediction:+.2f}%")
        print()
        
        if result['total_roi_closing'] is not None:
            print("ROI (Closing Odds):")
            print(f"  Total: {result['total_roi_closing']:+.2f} KSH")
            print(f"  Per Bet: {result['avg_roi_closing']:+.2f} KSH")
            print(f"  ROI %: {roi_pct_closing:+.2f}%")
        
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


def performance_by_surface():
    """Break down performance by court surface"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                surface,
                COUNT(*) as predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as total_roi,
                ROUND(AVG(COALESCE(roi_prediction_odds, 0)), 2) as avg_roi
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
              AND surface IS NOT NULL
            GROUP BY surface
            ORDER BY total_roi DESC
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("\n⚠️  No surface data available yet")
            return
        
        print("\n" + "="*60)
        print("🎾 PERFORMANCE BY SURFACE")
        print("="*60)
        
        table_data = [
            [
                row['surface'],
                row['predictions'],
                row['correct'],
                f"{row['win_rate']}%",
                f"{row['total_roi']:+.2f}",
                f"{row['avg_roi']:+.2f}"
            ]
            for row in results
        ]
        
        print(tabulate(
            table_data,
            headers=['Surface', 'Predictions', 'Correct', 'Win Rate', 'Total ROI (KSH)', 'Avg ROI'],
            tablefmt='grid'
        ))
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


def performance_by_tour_type():
    """Break down by ATP/WTA/Challenger"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                tour_type,
                COUNT(*) as predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as total_roi,
                ROUND(AVG(COALESCE(roi_prediction_odds, 0)), 2) as avg_roi
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
              AND tour_type IS NOT NULL
            GROUP BY tour_type
            ORDER BY total_roi DESC
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("\n⚠️  No tour type data available yet")
            return
        
        print("\n" + "="*60)
        print("🏆 PERFORMANCE BY TOUR TYPE")
        print("="*60)
        
        table_data = [
            [
                row['tour_type'],
                row['predictions'],
                row['correct'],
                f"{row['win_rate']}%",
                f"{row['total_roi']:+.2f}",
                f"{row['avg_roi']:+.2f}"
            ]
            for row in results
        ]
        
        print(tabulate(
            table_data,
            headers=['Tour', 'Predictions', 'Correct', 'Win Rate', 'Total ROI (KSH)', 'Avg ROI'],
            tablefmt='grid'
        ))
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


def monthly_trend():
    """Show performance trend over time"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                DATE_TRUNC('month', prediction_date)::date as month,
                COUNT(*) as predictions,
                SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
                ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(COALESCE(roi_prediction_odds, 0)), 2) as monthly_roi
            FROM predictions
            WHERE actual_winner_id IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("\n⚠️  No monthly data available yet")
            return
        
        print("\n" + "="*60)
        print("📈 MONTHLY PERFORMANCE TREND")
        print("="*60)
        
        table_data = [
            [
                row['month'].strftime('%Y-%m'),
                row['predictions'],
                row['correct'],
                f"{row['win_rate']}%",
                f"{row['monthly_roi']:+.2f}"
            ]
            for row in results
        ]
        
        print(tabulate(
            table_data,
            headers=['Month', 'Predictions', 'Correct', 'Win Rate', 'ROI (KSH)'],
            tablefmt='grid'
        ))
        print("="*60)
        
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════

def main():
    """Run all analysis functions"""
    setup_logging()
    
    print("\n" + "🎾"*30)
    print(" "*20 + "MATCHSTAT ROI ANALYSIS")
    print("🎾"*30 + "\n")
    
    try:
        overall_performance()
        performance_by_surface()
        performance_by_tour_type()
        monthly_trend()
        
        print("\n✅ Analysis complete!\n")
        
    except Exception as e:
        logger.error(f"Error running analysis: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")


if __name__ == '__main__':
    main()
