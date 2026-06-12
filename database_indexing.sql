-- ============================================================
-- BloodDetect AI Database Indexing Script
-- Run these commands in the Supabase Dashboard SQL Editor
-- to optimize database performance for remote queries.
-- ============================================================

-- 1. Index for filtering predictions by user_id
CREATE INDEX IF NOT EXISTS idx_predictions_user_id 
ON predictions(user_id);

-- 2. Index for sorting predictions by date (e.g. for history list)
CREATE INDEX IF NOT EXISTS idx_predictions_created_at 
ON predictions(created_at DESC);

-- 3. Composite index for filtering by user_id AND sorting by date
CREATE INDEX IF NOT EXISTS idx_predictions_user_id_created_at
ON predictions(user_id, created_at DESC);
