-- Rollback Migration: Enhance Template Categorization System
-- Date: 2025-01-20
-- Description: Revert template categorization enhancements

-- Step 1: Drop new indexes
DROP INDEX IF EXISTS idx_content_templates_parent_id;
DROP INDEX IF EXISTS idx_content_templates_ai_categorized;
DROP INDEX IF EXISTS idx_content_templates_ai_tags_gin;
DROP INDEX IF EXISTS idx_content_templates_custom_category;
DROP INDEX IF EXISTS idx_content_templates_custom_format;

-- Step 2: Remove new columns
ALTER TABLE public.content_templates 
DROP COLUMN IF EXISTS user_id,
DROP COLUMN IF EXISTS parent_template_id,
DROP COLUMN IF EXISTS ai_categorized,
DROP COLUMN IF EXISTS ai_tags,
DROP COLUMN IF EXISTS custom_category,
DROP COLUMN IF EXISTS custom_format,
DROP COLUMN IF EXISTS categorization_confidence;

-- Step 3: Drop RLS policies (restore original state)
DROP POLICY IF EXISTS "select content templates" ON public.content_templates;
DROP POLICY IF EXISTS "insert content templates" ON public.content_templates;
DROP POLICY IF EXISTS "update content templates" ON public.content_templates;
DROP POLICY IF EXISTS "delete content templates" ON public.content_templates;

-- Step 4: Re-add CHECK constraints
ALTER TABLE public.content_templates 
ADD CONSTRAINT content_templates_category_check 
CHECK (category IN ('attract', 'nurture', 'convert'));

ALTER TABLE public.content_templates 
ADD CONSTRAINT content_templates_format_check 
CHECK (format IN (
  'belief_shift', 'origin_story', 'industry_myths',  -- attract
  'framework', 'step_by_step', 'how_i_how_to',       -- nurture  
  'objection_post', 'result_breakdown', 'client_success_story' -- convert
));
