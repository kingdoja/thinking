-- Migration 005: Add metrics_jsonb column to stage_tasks
-- This migration adds the metrics_jsonb column to store execution metrics for media stages
-- Requirement 10.5: Record execution metrics for each stage

-- Add metrics_jsonb column to stage_tasks table
ALTER TABLE stage_tasks
ADD COLUMN IF NOT EXISTS metrics_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Add index for querying metrics
CREATE INDEX IF NOT EXISTS idx_stage_tasks_metrics
    ON stage_tasks USING GIN(metrics_jsonb);

-- Add comment to document the column
COMMENT ON COLUMN stage_tasks.metrics_jsonb IS 'Execution metrics including duration_ms, provider_calls, success_count, failure_count, estimated_cost, token_usage, retry_count';
