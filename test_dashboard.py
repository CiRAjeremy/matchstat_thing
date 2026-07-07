"""
Test if dashboard API works
"""
import json
from dashboard.api import app

with app.test_client() as client:
    print("🧪 Testing Dashboard API...\n")
    
    # Test API endpoint
    response = client.get('/api/stats')
    
    if response.status_code == 200:
        data = response.get_json()
        
        print("✅ API is working!")
        print("\n📊 Dashboard Data Preview:")
        print(f"   Total Predictions: {data['total_predictions']}")
        print(f"   With Results: {data['predictions_with_results']}")
        print(f"   Win Rate: {data['accuracy']}%")
        print(f"   Total ROI: {data['total_roi']} KSH")
        print(f"   Recent Predictions: {len(data['recent_predictions'])}")
        
        if data['total_predictions'] == 0:
            print("\n⚠️ No predictions yet - dashboard will be empty")
            print("   Run: python -m src.scrapers.matchstat_selenium")
        elif data['total_predictions'] < 5:
            print(f"\n💡 Only {data['total_predictions']} predictions - dashboard will work but look sparse")
        else:
            print(f"\n✅ {data['total_predictions']} predictions - dashboard will look great!")
        
        print("\n🚀 Ready to start dashboard server!")
        print("   Run: python dashboard/api.py")
        print("   Then open: http://localhost:5000")
    else:
        print(f"❌ API test failed: {response.status_code}")
        print(response.data)
