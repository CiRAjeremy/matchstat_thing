-- ═══════════════════════════════════════════════════════════
-- MATCHSTAT TENNIS PREDICTION TRACKING SYSTEM
-- Database Schema for Neon PostgreSQL
-- ═══════════════════════════════════════════════════════════

-- Table 1: Players
-- Normalized player data to avoid duplicate names
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(255) UNIQUE NOT NULL,
    alternate_names TEXT[],
    country VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_players_name ON players(canonical_name);
CREATE INDEX IF NOT EXISTS idx_players_country ON players(country);

-- Table 2: Predictions
-- Main table storing all prediction data
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    
    -- Scraping metadata
    prediction_date DATE NOT NULL,
    prediction_scraped_at TIMESTAMP DEFAULT NOW(),
    
    -- Player references
    player1_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
    player2_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
    player1_rank INTEGER,
    player2_rank INTEGER,
    
    -- Match details
    tournament_name VARCHAR(255),
    tournament_round VARCHAR(50),  -- R1, R2, QF, SF, F
    surface VARCHAR(20),           -- Clay, Hard, Grass, Carpet
    tour_type VARCHAR(20),         -- ATP, WTA, Challenger, ITF
    match_datetime TIMESTAMP,
    
    -- Time until match (auto-calculated)
    hours_before_match DECIMAL(5,2) GENERATED ALWAYS AS 
        (EXTRACT(EPOCH FROM (match_datetime - prediction_scraped_at))/3600) STORED,
    
    -- Prediction data
    predicted_winner_id INTEGER REFERENCES players(id),
    matchstat_url TEXT UNIQUE NOT NULL,
    raw_prediction_text TEXT,
    prediction_summary JSONB,
    
    -- Match status
    match_status VARCHAR(20) DEFAULT 'scheduled',
    
    -- Results (filled by results scraper)
    actual_winner_id INTEGER REFERENCES players(id),
    match_score VARCHAR(100),
    result_scraped_at TIMESTAMP,
    
    -- Analysis
    prediction_correct BOOLEAN,
    
    -- Multiple ROI calculations
    roi_prediction_odds DECIMAL(10,2),  -- Using odds at prediction time
    roi_closing_odds DECIMAL(10,2),     -- Using odds just before match
    roi_best_odds DECIMAL(10,2),        -- Using best available odds
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_players CHECK (player1_id != player2_id),
    CONSTRAINT valid_winner CHECK (
        predicted_winner_id IN (player1_id, player2_id)
    ),
    CONSTRAINT valid_actual_winner CHECK (
        actual_winner_id IS NULL OR 
        actual_winner_id IN (player1_id, player2_id)
    )
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_prediction_date ON predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_match_datetime ON predictions(match_datetime);
CREATE INDEX IF NOT EXISTS idx_tournament ON predictions(tournament_name);
CREATE INDEX IF NOT EXISTS idx_surface ON predictions(surface);
CREATE INDEX IF NOT EXISTS idx_tour_type ON predictions(tour_type);
CREATE INDEX IF NOT EXISTS idx_match_status ON predictions(match_status);
CREATE INDEX IF NOT EXISTS idx_player1 ON predictions(player1_id);
CREATE INDEX IF NOT EXISTS idx_player2 ON predictions(player2_id);

-- Table 3: Odds Snapshots
-- Tracks odds at different points in time
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER REFERENCES predictions(id) ON DELETE CASCADE,
    
    bookmaker VARCHAR(100) NOT NULL,
    player1_odds DECIMAL(5,2) NOT NULL,
    player2_odds DECIMAL(5,2) NOT NULL,
    
    -- When were these odds captured?
    odds_type VARCHAR(50) NOT NULL,  -- 'prediction_time', 'closing', 'live_update'
    captured_at TIMESTAMP DEFAULT NOW(),
    
    -- How long before match?
    hours_before_match DECIMAL(5,2),
    
    -- Prevent duplicate odds
    CONSTRAINT unique_odds UNIQUE (prediction_id, bookmaker, odds_type),
    
    -- Validate odds are reasonable
    CONSTRAINT valid_odds CHECK (
        player1_odds > 1.0 AND 
        player2_odds > 1.0
    )
);

CREATE INDEX IF NOT EXISTS idx_odds_prediction ON odds_snapshots(prediction_id);
CREATE INDEX IF NOT EXISTS idx_odds_type ON odds_snapshots(odds_type);
CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds_snapshots(bookmaker);

-- Table 4: Scrape Logs
-- Monitoring and debugging table
CREATE TABLE IF NOT EXISTS scrape_logs (
    id SERIAL PRIMARY KEY,
    scrape_type VARCHAR(50) NOT NULL,  -- 'predictions', 'results', 'closing_odds'
    scrape_timestamp TIMESTAMP DEFAULT NOW(),
    
    matches_found INTEGER DEFAULT 0,
    matches_saved INTEGER DEFAULT 0,
    matches_failed INTEGER DEFAULT 0,
    
    errors TEXT,
    status VARCHAR(20) NOT NULL,  -- 'success', 'partial', 'failed'
    execution_time_seconds DECIMAL(10,2),
    
    pages_scraped INTEGER DEFAULT 0,
    firecrawl_credits_used INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_scrape_type ON scrape_logs(scrape_type);
CREATE INDEX IF NOT EXISTS idx_scrape_timestamp ON scrape_logs(scrape_timestamp);

-- Helper Views
-- View: Get predictions with player names (easier querying)
CREATE OR REPLACE VIEW predictions_view AS
SELECT 
    p.id,
    p.prediction_date,
    p1.canonical_name AS player1_name,
    p2.canonical_name AS player2_name,
    pw.canonical_name AS predicted_winner,
    aw.canonical_name AS actual_winner,
    p.tournament_name,
    p.surface,
    p.tour_type,
    p.match_datetime,
    p.hours_before_match,
    p.prediction_correct,
    p.roi_prediction_odds,
    p.roi_closing_odds,
    p.match_status,
    p.matchstat_url
FROM predictions p
LEFT JOIN players p1 ON p.player1_id = p1.id
LEFT JOIN players p2 ON p.player2_id = p2.id
LEFT JOIN players pw ON p.predicted_winner_id = pw.id
LEFT JOIN players aw ON p.actual_winner_id = aw.id;

-- View: Get latest odds for each prediction
CREATE OR REPLACE VIEW latest_odds AS
SELECT DISTINCT ON (prediction_id, odds_type)
    prediction_id,
    odds_type,
    bookmaker,
    player1_odds,
    player2_odds,
    captured_at,
    hours_before_match
FROM odds_snapshots
ORDER BY prediction_id, odds_type, captured_at DESC;

-- Database Functions
-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_predictions_updated_at BEFORE UPDATE ON predictions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
