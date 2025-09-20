-- Migration: Enhance Template Categorization System
-- Date: 2025-01-20
-- Description: Remove constraints and add new fields for flexible template categorization

-- Step 1: Add new columns to content_templates table
ALTER TABLE public.content_templates 
ADD COLUMN IF NOT EXISTS parent_template_id uuid REFERENCES public.content_templates(id),
ADD COLUMN IF NOT EXISTS ai_categorized boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS ai_tags text[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS custom_category boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS custom_format boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS categorization_confidence decimal(3,2) DEFAULT 0.00;

-- Step 2: Remove CHECK constraints (this will allow any text values)
-- Note: We'll keep the existing categories as defaults but allow flexibility

-- Remove category constraint
ALTER TABLE public.content_templates 
DROP CONSTRAINT IF EXISTS content_templates_category_check;

-- Remove format constraint  
ALTER TABLE public.content_templates 
DROP CONSTRAINT IF EXISTS content_templates_format_check;

-- Step 3: Update existing records to mark them as system categories
UPDATE public.content_templates 
SET custom_category = false, custom_format = false
WHERE category IN ('attract', 'nurture', 'convert');

-- Step 4: Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_content_templates_parent_id ON public.content_templates (parent_template_id);
CREATE INDEX IF NOT EXISTS idx_content_templates_ai_categorized ON public.content_templates (ai_categorized);
CREATE INDEX IF NOT EXISTS idx_content_templates_ai_tags_gin ON public.content_templates USING gin (ai_tags);
CREATE INDEX IF NOT EXISTS idx_content_templates_custom_category ON public.content_templates (custom_category);
CREATE INDEX IF NOT EXISTS idx_content_templates_custom_format ON public.content_templates (custom_format);

-- Step 5: Add comments for documentation
COMMENT ON COLUMN public.content_templates.parent_template_id IS 'Reference to original template if this is a copy';
COMMENT ON COLUMN public.content_templates.ai_categorized IS 'Whether this template was categorized by AI';
COMMENT ON COLUMN public.content_templates.ai_tags IS 'Up to 3 AI-generated tags for content creator insights';
COMMENT ON COLUMN public.content_templates.custom_category IS 'Whether category was created by user (vs system default)';
COMMENT ON COLUMN public.content_templates.custom_format IS 'Whether format was created by user (vs system default)';
COMMENT ON COLUMN public.content_templates.categorization_confidence IS 'AI confidence score for categorization (0.00-1.00)';
