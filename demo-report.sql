-- These reports show presentation data only. Hindi kasama ang real patients.
-- Group rows by service, status, and source, then count each group.
-- The is_demo filter keeps presentation reports separate from real patient activity.
-- Read-only query ito: it summarizes records without changing or deleting them.
select service_id, status, source, count(*) as appointments
from public.appointments
where is_demo = true
group by service_id, status, source
order by service_id, status;

-- Each patient has a sample history. Fake names lang ang demo records.
select p.full_name, count(a.id) as visits,
       count(a.id) filter (where a.status = 'completed') as completed_visits
from public.patient_profiles p
left join public.appointments a on a.patient_id = p.id and a.is_demo = true
where p.is_demo = true
group by p.id, p.full_name
order by p.full_name;
