-- Run in the dedicated Bright Smile database. Dito lang ang clinic tables.
-- This setup creates or updates clinic tables without deleting existing rows.
-- A transaction groups the steps: commit saves them; an error prevents a partial setup.
-- Parang isang complete form submission: magkakasama ang related database changes.
begin;

-- Patient profiles store names, never passwords. Supabase Auth ang bahala sa passwords.
create table if not exists public.patient_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null check (char_length(full_name) between 2 and 100),
  is_demo boolean not null default false,
  created_at timestamptz not null default now()
);

-- This table receives contact notes from Python. Hindi ito public inbox na mababasa ng lahat.
create table if not exists public.contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 2 and 100),
  email text not null check (char_length(email) <= 254),
  message text not null check (char_length(message) between 10 and 2000),
  is_demo boolean not null default false,
  created_at timestamptz not null default now()
);

-- Future verified Cal.com events can be copied here. Cal.com pa rin ang source of real bookings.
-- patient_id links a signed-in booking to an Auth user; guest bookings can leave it empty.
-- cal_booking_uid is unique so the same reservation cannot become two history rows.
-- Guest names and emails are added below para may contact details din ang admin.
create table if not exists public.appointments (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid references auth.users(id) on delete set null,
  cal_booking_uid text not null unique,
  service_id text not null check (service_id in ('checkup','cleaning','filling','extraction','followup')),
  starts_at timestamptz not null,
  status text not null,
  is_demo boolean not null default false,
  source text not null default 'cal.com' check (source in ('cal.com', 'demo')),
  demo_seed_key text unique,
  created_at timestamptz not null default now()
);
create index if not exists appointments_patient_idx on public.appointments(patient_id);
create index if not exists appointments_starts_idx on public.appointments(starts_at);

-- Add labels to older tables too. Hindi mawawala ang existing records.
alter table public.patient_profiles add column if not exists is_demo boolean not null default false;
alter table public.contact_messages add column if not exists is_demo boolean not null default false;
alter table public.appointments add column if not exists is_demo boolean not null default false;
alter table public.appointments add column if not exists source text not null default 'cal.com';
alter table public.appointments add column if not exists demo_seed_key text;
-- Keep guest booking details too. Kahit walang patient account, may name at email ang admin.
alter table public.appointments add column if not exists patient_name text;
alter table public.appointments add column if not exists patient_email text;
create unique index if not exists appointments_demo_seed_idx on public.appointments(demo_seed_key) where demo_seed_key is not null;

-- These locks stop public users from reading other people's details. Bawat account may sariling access.
-- RLS means Row Level Security: the database checks which rows an account may access.
-- GRANT allows a kind of action; a policy below decides which rows that action may use.
-- Both matter: may permission sa table, pero sariling records lang ang patient.
alter table public.patient_profiles enable row level security;
alter table public.contact_messages enable row level security;
alter table public.appointments enable row level security;
revoke all on public.patient_profiles, public.contact_messages, public.appointments from anon, authenticated;
grant select, insert, update on public.patient_profiles to authenticated;
grant select on public.appointments to authenticated;
-- The service_role has broad access and is used only by trusted Python server requests.
-- Python verifies admin permission before using the secret key to read clinic-wide records.
-- Hindi kasama ang private service key sa HTML, JavaScript, o GitHub.
grant all on public.patient_profiles, public.contact_messages, public.appointments to service_role;

-- You can only read and change YOUR profile. Hindi mo puwedeng ilipat ito sa ibang user ID.
drop policy if exists "Read own profile" on public.patient_profiles;
create policy "Read own profile" on public.patient_profiles for select to authenticated using ((select auth.uid()) = id);
drop policy if exists "Create own profile" on public.patient_profiles;
create policy "Create own profile" on public.patient_profiles for insert to authenticated with check ((select auth.uid()) = id);
drop policy if exists "Update own profile" on public.patient_profiles;
create policy "Update own profile" on public.patient_profiles for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);
drop policy if exists "Read own appointments" on public.appointments;
create policy "Read own appointments" on public.appointments for select to authenticated using ((select auth.uid()) = patient_id);

-- No contact-message policy is public. Python's private key lang ang puwedeng magsulat.
commit;
