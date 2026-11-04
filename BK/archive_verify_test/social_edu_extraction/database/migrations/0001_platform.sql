-- LOMINII Platform – Initial Database Migration
-- Run once on your PostgreSQL instance (Neon, Supabase, etc.)

-- Schemas
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS search;
CREATE SCHEMA IF NOT EXISTS social;
CREATE SCHEMA IF NOT EXISTS curriculum;
CREATE SCHEMA IF NOT EXISTS classroom;
CREATE SCHEMA IF NOT EXISTS assessment;
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

-- ==================== SOCIAL ====================
CREATE TABLE social.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    core_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    social_uid VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    location GEOGRAPHY(Point, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE social.follows (
    follower_id UUID NOT NULL REFERENCES social.profiles(id),
    followee_id UUID NOT NULL REFERENCES social.profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, followee_id)
);

CREATE TABLE social.posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES social.profiles(id),
    content TEXT NOT NULL,
    media_urls JSONB,
    visibility VARCHAR(20) DEFAULT 'public',
    location GEOGRAPHY(Point, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE social.comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES social.posts(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES social.profiles(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE social.reactions (
    post_id UUID NOT NULL REFERENCES social.posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES social.profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE social.communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES social.profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE social.community_members (
    community_id UUID NOT NULL REFERENCES social.communities(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES social.profiles(id),
    role VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (community_id, user_id)
);

-- Privacy tables (social)
CREATE TABLE social.privacy_settings (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    profile_visibility VARCHAR(20) DEFAULT 'public',
    search_visibility VARCHAR(20) DEFAULT 'public',
    friend_request_permission VARCHAR(20) DEFAULT 'everyone',
    last_seen_visibility VARCHAR(20) DEFAULT 'friends',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE social.friend_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sender_id, receiver_id)
);

CREATE TABLE social.blocked_users (
    blocker_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (blocker_id, blocked_id)
);

CREATE TABLE social.muted_users (
    muter_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    muted_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (muter_id, muted_id)
);

-- ==================== CURRICULUM (EDU) ====================
CREATE TABLE curriculum.subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE curriculum.topics (
    id SERIAL PRIMARY KEY,
    subject_id INT NOT NULL REFERENCES curriculum.subjects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE curriculum.subtopics (
    id SERIAL PRIMARY KEY,
    topic_id INT NOT NULL REFERENCES curriculum.topics(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE curriculum.concepts (
    id SERIAL PRIMARY KEY,
    subtopic_id INT NOT NULL REFERENCES curriculum.subtopics(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE curriculum.questions (
    id SERIAL PRIMARY KEY,
    concept_id INT NOT NULL REFERENCES curriculum.concepts(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    options JSONB,
    correct_answer TEXT,
    difficulty VARCHAR(20),
    exam_type VARCHAR(20),
    year INT,
    tags JSONB
);

CREATE TABLE curriculum.knowledge_links (
    id SERIAL PRIMARY KEY,
    concept_id_1 INT NOT NULL REFERENCES curriculum.concepts(id) ON DELETE CASCADE,
    concept_id_2 INT NOT NULL REFERENCES curriculum.concepts(id) ON DELETE CASCADE,
    relationship VARCHAR(50)
);

-- ==================== CLASSROOM (EDU) ====================
CREATE TABLE classroom.classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id INT NOT NULL REFERENCES curriculum.subjects(id),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE classroom.class_enrollments (
    class_id UUID NOT NULL REFERENCES classroom.classes(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (class_id, student_id)
);

CREATE TABLE classroom.lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classroom.classes(id) ON DELETE CASCADE,
    concept_id INT NOT NULL REFERENCES curriculum.concepts(id),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE classroom.assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID NOT NULL REFERENCES classroom.lessons(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE classroom.submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES classroom.assignments(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    content TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== ASSESSMENT (EDU) ====================
CREATE TABLE assessment.concept_mastery (
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    concept_id INT NOT NULL REFERENCES curriculum.concepts(id) ON DELETE CASCADE,
    mastery FLOAT DEFAULT 0.0,
    last_practiced TIMESTAMPTZ,
    PRIMARY KEY (student_id, concept_id)
);

CREATE TABLE assessment.question_logs (
    id SERIAL PRIMARY KEY,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    question_id INT NOT NULL REFERENCES curriculum.questions(id) ON DELETE CASCADE,
    chosen_answer TEXT,
    is_correct BOOLEAN,
    answered_at TIMESTAMPTZ DEFAULT NOW()
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
CREATE INDEX idx_social_posts_location ON social.posts USING GIST (location);
CREATE INDEX idx_social_profiles_location ON social.profiles USING GIST (location);
CREATE INDEX idx_occupancy_col_row ON admin.occupancy(col, row);