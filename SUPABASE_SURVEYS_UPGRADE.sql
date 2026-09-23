create table if not exists public.surveys (id uuid primary key default gen_random_uuid(), title text not null, survey_type text not null, period_label text, response_count integer default 0, status text default 'completed', summary text, created_at timestamptz default now(), updated_at timestamptz default now(), deleted_at timestamptz, deleted_by text);
create table if not exists public.survey_metrics (id uuid primary key default gen_random_uuid(), survey_id uuid not null references public.surveys(id) on delete cascade, metric_name text not null, metric_value numeric, metric_scale text, notes text, created_at timestamptz default now());
create table if not exists public.survey_findings (id uuid primary key default gen_random_uuid(), survey_id uuid not null references public.surveys(id) on delete cascade, finding_type text default 'finding', finding_text text not null, evidence text, priority text, monitoring_action_id uuid references public.findings_actions(id) on delete set null, created_at timestamptz default now());
create index if not exists idx_survey_metrics_survey on public.survey_metrics(survey_id);
create index if not exists idx_survey_findings_survey on public.survey_findings(survey_id);
drop trigger if exists trg_surveys_updated_at on public.surveys;
create trigger trg_surveys_updated_at before update on public.surveys for each row execute function public.set_updated_at();
alter table public.surveys enable row level security; alter table public.survey_metrics enable row level security; alter table public.survey_findings enable row level security;
