-- ΚΕΔΙΒΙΜ Diagnostic Hub CLEAN V2
-- Run once in Supabase SQL Editor.

alter table public.programs add column if not exists deleted_at timestamptz;
alter table public.programs add column if not exists deleted_by text;

alter table public.cash_bridge add column if not exists deleted_at timestamptz;
alter table public.cash_bridge add column if not exists deleted_by text;

alter table public.cost_base add column if not exists deleted_at timestamptz;
alter table public.cost_base add column if not exists deleted_by text;

alter table public.findings_actions add column if not exists deleted_at timestamptz;
alter table public.findings_actions add column if not exists deleted_by text;

create table if not exists public.attachments (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  file_name text not null,
  storage_path text not null unique,
  mime_type text,
  file_size bigint,
  uploaded_at timestamptz default now(),
  uploaded_by text
);

create index if not exists idx_attachments_entity on public.attachments(entity_type, entity_id);

insert into storage.buckets (id, name, public)
values ('kedivim-attachments','kedivim-attachments',false)
on conflict (id) do nothing;
