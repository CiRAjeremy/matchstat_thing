# 📊 Matchstat Dashboard

Web interface to view your tennis prediction analysis.

## Quick Setup

### Option A: Next.js Dashboard (Recommended)

```bash
# Create Next.js app
cd dashboard
npx create-next-app@latest . --typescript --tailwind --app

# Install dependencies
npm install @neondatabase/serverless

# Set environment variable
# Create .env.local with:
DATABASE_URL=your_neon_connection_string

# Run dev server
npm run dev
```

### Option B: Simple HTML + JavaScript

Use the example in `dashboard/simple/index.html` - just open in browser after connecting to Neon via API.

## Features to Build

1. **Overview Stats** - Total predictions, win rate, ROI
2. **Charts** - Win rate over time (Chart.js or Recharts)
3. **Surface Breakdown** - Performance by court surface
4. **Recent Predictions** - Latest 10 predictions with results
5. **Profit/Loss Graph** - Cumulative ROI over time

## API Endpoints to Create

```typescript
// app/api/stats/route.ts
import { neon } from '@neondatabase/serverless';

export async function GET() {
  const sql = neon(process.env.DATABASE_URL!);
  
  const stats = await sql`
    SELECT 
      COUNT(*) as total,
      SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as wins,
      ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
      SUM(roi_prediction_odds) as total_roi
    FROM predictions 
    WHERE actual_winner_id IS NOT NULL
  `;
  
  return Response.json(stats[0]);
}
```

## Components to Build

- **StatsCard** - Display key metrics
- **LineChart** - Win rate over time
- **PredictionsTable** - Recent predictions
- **SurfaceBreakdown** - Pie chart or bar chart
- **ROIGraph** - Cumulative profit/loss

Would you like me to create a full Next.js dashboard template?
