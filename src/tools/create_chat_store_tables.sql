-- Chat history schema (Option A: conversations + messages)
-- Paste this whole script into the Supabase SQL Editor and Run

-- UUIDs (gen_random_uuid)
create extension if not exists pgcrypto;

-- Conversations table
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid null, -- optional now; wire to auth later
  title text,
  status text check (status in ('active','archived')) default 'active',
  summary text, -- running summary of the conversation
  state jsonb default '{}'::jsonb, -- shared state between agents
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Messages table
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid null,
  role text not null check (role in ('user','assistant','system','tool')),
  content text not null,
  agent_name text, -- tracks which agent created this message
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- System prompts table for agent prompts and versioning
create table if not exists public.system_prompts (
  id uuid primary key default gen_random_uuid(),
  agent_name text not null,
  version text not null,
  prompt text not null,
  is_current boolean default false, -- marks the current version for each agent
  created_at timestamptz not null default now(),
  unique(agent_name, version)
);

-- Content templates table for LinkedIn post templates
create table if not exists public.content_templates (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  content text not null,
  author text,
  linkedin_url text,
  category text not null check (category in ('attract', 'nurture', 'convert')),
  format text not null check (format in (
    'belief_shift', 'origin_story', 'industry_myths',  -- attract
    'framework', 'step_by_step', 'how_i_how_to',       -- nurture  
    'objection_post', 'result_breakdown', 'client_success_story' -- convert
  )),
  tags text[] default '{}', -- array of tags like ['hook', 'social_proof', 'cta']
  performance_metrics jsonb default '{}'::jsonb, -- likes, comments, shares if available
  screenshot_url text, -- optional screenshot of the post
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Indexes
create index if not exists idx_messages_conversation_time on public.messages (conversation_id, created_at desc);
create index if not exists idx_conversations_user_time on public.conversations (user_id, created_at desc);
create index if not exists idx_messages_metadata_gin on public.messages using gin (metadata);
create index if not exists idx_system_prompts_agent_current on public.system_prompts (agent_name, is_current);
create index if not exists idx_content_templates_category_format on public.content_templates (category, format);
create index if not exists idx_content_templates_tags_gin on public.content_templates using gin (tags);

-- updated_at trigger
create or replace function public.set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end; $$ language plpgsql;

drop trigger if exists trg_conversations_updated_at on public.conversations;
create trigger trg_conversations_updated_at
before update on public.conversations
for each row execute function public.set_updated_at();

drop trigger if exists trg_content_templates_updated_at on public.content_templates;
create trigger trg_content_templates_updated_at
before update on public.content_templates
for each row execute function public.set_updated_at();

-- Enable Row Level Security (future-ready)
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.content_templates enable row level security;

-- Owner-style policies; service role bypasses these during server-side use
drop policy if exists "select own conversations" on public.conversations;
drop policy if exists "insert own conversations" on public.conversations;
drop policy if exists "update own conversations" on public.conversations;
drop policy if exists "delete own conversations" on public.conversations;

drop policy if exists "select own messages" on public.messages;
drop policy if exists "insert own messages" on public.messages;
drop policy if exists "delete own messages" on public.messages;

create policy "select own conversations" on public.conversations for select using (
  user_id is null or auth.uid() = user_id
);
create policy "insert own conversations" on public.conversations for insert with check (
  user_id is null or auth.uid() = user_id
);
create policy "update own conversations" on public.conversations for update using (
  user_id is null or auth.uid() = user_id
) with check (
  user_id is null or auth.uid() = user_id
);
create policy "delete own conversations" on public.conversations for delete using (
  user_id is null or auth.uid() = user_id
);

create policy "select own messages" on public.messages for select using (
  user_id is null or auth.uid() = user_id
);
create policy "insert own messages" on public.messages for insert with check (
  user_id is null or auth.uid() = user_id
);
create policy "delete own messages" on public.messages for delete using (
  user_id is null or auth.uid() = user_id
);

-- Sanity checks
select 'Chat schema ready' as status;
select table_name from information_schema.tables where table_schema = 'public' and table_name in ('conversations','messages','system_prompts','content_templates');

