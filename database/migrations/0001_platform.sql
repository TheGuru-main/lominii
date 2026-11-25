-- LOMINII Platform – Initial Database Migration
-- Run once on your PostgreSQL instance (Neon, Supabase, etc.)

-- Schemas
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS search;
CREATE SCHEMA IF NOT EXISTS game;
CREATE SCHEMA IF NOT EXISTS ads;
CREATE SCHEMA IF NOT EXISTS admin;
CREATE SCHEMA IF NOT EXISTS crawler;

-- ==================== PUBLIC (Shared) ====================
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    google_id VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    occupation VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    news_preferences JSONB,
    subscription_status VARCHAR(20) DEFAULT 'free',
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== SEARCH ====================
CREATE TABLE search.searches (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    gsp_cell VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE search.trending (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE search.corrections (
    id SERIAL PRIMARY KEY,
    misspelled TEXT NOT NULL,
    corrected TEXT NOT NULL,
    gsp_cell VARCHAR(10),
    confidence FLOAT DEFAULT 0.0
);

CREATE TABLE search.news_articles (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source VARCHAR(255),
    published_at TIMESTAMPTZ,
    inserted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE search.news_cache (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) UNIQUE NOT NULL,
    articles JSONB NOT NULL,
    cached_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE search.dictionary_cache (
    id SERIAL PRIMARY KEY,
    word VARCHAR(255) UNIQUE NOT NULL,
    definition TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    cached_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE search.search_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(64) UNIQUE NOT NULL,
    result JSONB NOT NULL,
    cached_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE search.video_cache (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    videos JSONB NOT NULL,
    cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== GAMES ====================
CREATE TABLE game.game_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id VARCHAR(20) NOT NULL,
    room_id VARCHAR(20) UNIQUE NOT NULL,
    players JSONB NOT NULL,
    game_state JSONB,
    status VARCHAR(20) DEFAULT 'waiting',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE game.leaderboards (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    draws INT DEFAULT 0,
    points INT DEFAULT 1000,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== ADS ====================
CREATE TABLE ads.premium_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    payment_reference TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ads.sponsored_cells (
    id SERIAL PRIMARY KEY,
    advertiser_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    col INT NOT NULL,
    row INT NOT NULL,
    ad_content JSONB,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    active BOOLEAN DEFAULT true
);

-- ==================== ADMIN ====================
CREATE TABLE admin.occupancy (
    col INT NOT NULL,
    row INT NOT NULL,
    searches INT DEFAULT 0,
    games INT DEFAULT 0,
    users INT DEFAULT 0,
    messages INT DEFAULT 0,
    api_calls INT DEFAULT 0,
    cache_hits INT DEFAULT 0,
    PRIMARY KEY (col, row)
);

CREATE TABLE admin.username_cells (
    col INT NOT NULL,
    row INT NOT NULL,
    username VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES public.users(id),
    PRIMARY KEY (col, row, user_id)
);

-- ==================== CRAWLER ====================
CREATE TABLE crawler.pages (
    url_hash VARCHAR(64) PRIMARY KEY,
    url TEXT NOT NULL,
    gsp_cell VARCHAR(10),
    title TEXT,
    content TEXT,
    out_links JSONB DEFAULT '[]',
    pagerank FLOAT DEFAULT 0.0,
    last_crawled TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_searches_user ON search.searches(user_id);
CREATE INDEX idx_trending_count ON search.trending(count DESC);
CREATE INDEX idx_news_category ON search.news_articles(category, inserted_at DESC);
CREATE INDEX idx_occupancy_col_row ON admin.occupancy(col, row);