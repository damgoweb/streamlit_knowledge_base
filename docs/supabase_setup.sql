-- Supabase Database Setup Script
-- Run this in Supabase SQL Editor to initialize your database

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create tables
CREATE TABLE IF NOT EXISTS snippets (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    tags TEXT,
    description TEXT,
    language TEXT DEFAULT 'text',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    usage_count INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    icon TEXT DEFAULT '📁',
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    result_count INTEGER DEFAULT 0
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_snippets_category ON snippets(category);
CREATE INDEX IF NOT EXISTS idx_snippets_updated ON snippets(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_snippets_usage ON snippets(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_snippets_favorite ON snippets(is_favorite);

-- Create update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_snippets_updated_at ON snippets;
CREATE TRIGGER update_snippets_updated_at 
    BEFORE UPDATE ON snippets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create search function
CREATE OR REPLACE FUNCTION search_snippets_simple(keyword text)
RETURNS TABLE (
    id integer,
    title text,
    content text,
    category text,
    tags text,
    description text,
    language text,
    created_at timestamptz,
    updated_at timestamptz,
    usage_count integer,
    is_favorite boolean
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF keyword IS NULL OR trim(keyword) = '' THEN
        RETURN QUERY
        SELECT 
            s.id::integer,
            s.title,
            s.content,
            s.category,
            s.tags,
            s.description,
            s.language,
            s.created_at,
            s.updated_at,
            s.usage_count,
            s.is_favorite
        FROM snippets s
        ORDER BY s.updated_at DESC
        LIMIT 100;
    ELSE
        RETURN QUERY
        SELECT 
            s.id::integer,
            s.title,
            s.content,
            s.category,
            s.tags,
            s.description,
            s.language,
            s.created_at,
            s.updated_at,
            s.usage_count,
            s.is_favorite
        FROM snippets s
        WHERE 
            s.title ILIKE '%' || keyword || '%'
            OR s.content ILIKE '%' || keyword || '%'
            OR s.tags ILIKE '%' || keyword || '%'
            OR s.description ILIKE '%' || keyword || '%'
        ORDER BY s.updated_at DESC
        LIMIT 100;
    END IF;
END;
$$;

-- Create statistics function
CREATE OR REPLACE FUNCTION get_statistics()
RETURNS TABLE (
    total_snippets bigint,
    total_categories bigint,
    most_used_category text,
    total_usage_count bigint,
    favorites_count bigint
)
LANGUAGE sql
AS $$
    SELECT 
        (SELECT COUNT(*) FROM snippets)::bigint,
        (SELECT COUNT(DISTINCT category) FROM snippets)::bigint,
        (SELECT category FROM snippets GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1),
        (SELECT SUM(usage_count) FROM snippets)::bigint,
        (SELECT COUNT(*) FROM snippets WHERE is_favorite = true)::bigint;
$$;

-- Insert initial categories
INSERT INTO categories (name, icon, display_order) VALUES
    ('Docker', '🐳', 1),
    ('Git', '📚', 2),
    ('SQL', '🗄️', 3),
    ('Linux', '🐧', 4),
    ('Python', '🐍', 5),
    ('設定', '⚙️', 6),
    ('その他', '📝', 99)
ON CONFLICT (name) DO NOTHING;

-- Grant permissions
GRANT ALL ON snippets TO anon;
GRANT ALL ON categories TO anon;
GRANT ALL ON search_history TO anon;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon;

-- Success message
SELECT 'Database setup completed successfully!' as message;
