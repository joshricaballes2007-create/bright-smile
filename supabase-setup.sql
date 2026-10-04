-- Run this once in the chosen Supabase project's SQL Editor. Draft lang ito until may real project.
begin;

-- Patient profiles store names, never passwords. Supabase Auth ang bahala sa passwords.
create table if not exists public.patient_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null check (char_length(full_name) between 2 and 100),
  created_at timestamptz not null default now()
);

-- This table receives contact notes from Python. Hindi ito public inbox na mababasa ng lahat.
create table if not exists public.contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 2 and 100),
  email text not null check (char_length(email) <= 254),
  message text not null check (char_length(message) between 10 and 2000),
  created_at timestamptz not null default now()
);

-- Future verified Cal.com events can be copied here. Cal.com pa rin ang source of real bookings.
create table if not exists public.appointments (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid references auth.users(id) on delete set null,
  cal_booking_uid text not null unique,
  service_id text not null check (service_id in ('checkup','cleaning','filling','extraction','followup')),
  starts_at timestamptz not null,
  status text not null,
  created_at timestamptz not null default now()
);
create index if not exists appointments_patient_idx on public.appointments(patient_id);

-- These locks stop public users from reading other people's details. Bawat account may sariling access.
alter table public.patient_profiles enable row level security;
alter table public.contact_messages enable row level security;
alter table public.appointments enable row level security;
revoke all on public.patient_profiles, public.contact_messages, public.appointments from anon, authenticated;
grant select, insert, update on public.patient_profiles to authenticated;
grant select on public.appointments to authenticated;
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
