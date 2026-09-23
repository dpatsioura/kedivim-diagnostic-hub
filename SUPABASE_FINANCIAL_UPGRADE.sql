
-- ΚΕΔΙΒΙΜ Diagnostic Hub - Financial Model Upgrade
-- Run ONCE in Supabase SQL Editor before deploying the new app.

create table if not exists public.financial_transactions (
    id uuid primary key default gen_random_uuid(),
    transaction_date date not null,
    transaction_type text not null check (transaction_type in ('income','expense')),
    amount numeric not null check (amount >= 0),
    category text not null,
    program_id uuid references public.programs(id) on delete set null,
    description text not null,
    reference_no text,
    payment_status text default 'paid',
    notes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now(),
    deleted_at timestamptz,
    deleted_by text
);

create index if not exists idx_fin_transactions_date
on public.financial_transactions(transaction_date);

create index if not exists idx_fin_transactions_program
on public.financial_transactions(program_id);

create index if not exists idx_fin_transactions_type
on public.financial_transactions(transaction_type);

alter table public.programs add column if not exists budget_revenue numeric;
alter table public.programs add column if not exists budget_expenses numeric;
alter table public.programs add column if not exists nominal_tuition numeric;
alter table public.programs add column if not exists other_direct_expenses numeric;
alter table public.programs add column if not exists withholdings_charges numeric;
alter table public.programs add column if not exists marketing_cost numeric;
alter table public.programs add column if not exists admin_allocation numeric;

drop trigger if exists trg_financial_transactions_updated_at on public.financial_transactions;
create trigger trg_financial_transactions_updated_at
before update on public.financial_transactions
for each row execute function public.set_updated_at();

alter table public.financial_transactions enable row level security;

-- Attachments table already supports arbitrary entity types.
-- The app uses entity_type='transaction' for financial transaction attachments.
