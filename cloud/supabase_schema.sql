-- =====================================================================
--  Supabase schema for the ESP32 IoT projects that use Supabase
--  (P05 Smart Parking, P06 RFID Attendance, P09 Smart Greenhouse,
--   P10 Vehicle Tracker).
--  Paste the whole file into  Supabase > SQL Editor > New query > Run.
--  It is safe to run more than once.
--
--  Security model (educational): the ESP32 uses the project's
--  publishable/anon key, so Row Level Security policies below allow the
--  "anon" role to do exactly what each device needs and nothing more.
--  For a real deployment, give each device its own Supabase Auth user and
--  restrict policies to "authenticated".
-- =====================================================================

-- ---------------------------------------------------------------- P05
create table if not exists public.parking_slots (
  id           int primary key,
  occupied     boolean not null default false,
  distance_cm  real,
  updated_at   timestamptz not null default now()
);
insert into public.parking_slots (id) values (1), (2) on conflict (id) do nothing;

create table if not exists public.parking_events (
  id          bigserial primary key,
  event       text not null,          -- slot_occupied | slot_freed | full_rejected
  slot        int,
  free_slots  int,
  device      text,
  created_at  timestamptz not null default now()
);

create or replace view public.parking_summary as
  select count(*) filter (where not occupied) as free_slots,
         count(*)                              as total_slots,
         max(updated_at)                       as last_change
  from public.parking_slots;

-- ---------------------------------------------------------------- P06
create table if not exists public.members (
  uid         text primary key,        -- card UID in UPPER-CASE hex, e.g. A1B2C3D4
  name        text not null,
  role        text not null default 'member',
  created_at  timestamptz not null default now()
);

create table if not exists public.attendance (
  id          bigserial primary key,
  uid         text not null,
  name        text,
  direction   text check (direction in ('IN', 'OUT')),
  device      text,
  offline     boolean not null default false,   -- true = scanned without internet, uploaded later
  scanned_at  timestamptz not null default now()
);
create index if not exists attendance_scanned_at_idx on public.attendance (scanned_at desc);

create or replace view public.attendance_today as
  select name, uid,
         min(scanned_at) filter (where direction = 'IN')  as first_in,
         max(scanned_at) filter (where direction = 'OUT') as last_out,
         count(*) as scans
  from public.attendance
  where scanned_at >= date_trunc('day', now() at time zone 'Asia/Kolkata') at time zone 'Asia/Kolkata'
  group by name, uid
  order by first_in;

-- ---------------------------------------------------------------- P09
create table if not exists public.greenhouse_readings (
  id           bigserial primary key,
  soil         real,
  temperature  real,
  humidity     real,
  light        real,
  pump         boolean,
  fan          boolean,
  device       text,
  created_at   timestamptz not null default now()
);

create table if not exists public.greenhouse_events (
  id          bigserial primary key,
  event       text not null,
  detail      text,
  device      text,
  created_at  timestamptz not null default now()
);

-- one row (id = 1) holds the thresholds the device downloads every minute
create table if not exists public.greenhouse_settings (
  id          int primary key default 1,
  soil_min    real not null default 35,
  soil_max    real not null default 60,
  temp_max    real not null default 32,
  hum_max     real not null default 85,
  auto_mode   boolean not null default true,
  updated_at  timestamptz not null default now(),
  constraint single_row check (id = 1),
  constraint soil_range check (soil_min < soil_max)
);
insert into public.greenhouse_settings (id) values (1) on conflict (id) do nothing;

-- ---------------------------------------------------------------- P10
create table if not exists public.vehicle_locations (
  id           bigserial primary key,
  lat          double precision not null,
  lng          double precision not null,
  speed_kmph   real,
  heading      real,
  satellites   int,
  device       text,
  recorded_at  timestamptz,                       -- GPS/NTP time on the device (null if unknown)
  created_at   timestamptz not null default now() -- time the row reached the cloud
);
create index if not exists vehicle_locations_created_idx on public.vehicle_locations (created_at desc);

create table if not exists public.vehicle_alerts (
  id          bigserial primary key,
  type        text not null,      -- accident_impact | accident_rollover | sos | geofence_exit | geofence_enter
  detail      text,
  device      text,
  g_force     real,
  lat         double precision,
  lng         double precision,
  maps_url    text,
  speed_kmph  real,
  created_at  timestamptz not null default now()
);

-- ------------------------------------------------- Row Level Security
alter table public.parking_slots       enable row level security;
alter table public.parking_events      enable row level security;
alter table public.members             enable row level security;
alter table public.attendance          enable row level security;
alter table public.greenhouse_readings enable row level security;
alter table public.greenhouse_events   enable row level security;
alter table public.greenhouse_settings enable row level security;
alter table public.vehicle_locations   enable row level security;
alter table public.vehicle_alerts      enable row level security;

do $$
declare t text;
begin
  -- devices may insert into every log table and read every table
  foreach t in array array['parking_events','attendance','greenhouse_readings','greenhouse_events',
                           'vehicle_locations','vehicle_alerts','members'] loop
    execute format('drop policy if exists "device insert" on public.%I', t);
    execute format('create policy "device insert" on public.%I for insert to anon with check (true)', t);
  end loop;
  foreach t in array array['parking_slots','parking_events','members','attendance','greenhouse_readings',
                           'greenhouse_events','greenhouse_settings','vehicle_locations','vehicle_alerts'] loop
    execute format('drop policy if exists "device read" on public.%I', t);
    execute format('create policy "device read" on public.%I for select to anon using (true)', t);
  end loop;
end $$;

-- P05 updates slot rows; P06 renames (upsert) and deletes members
drop policy if exists "device update" on public.parking_slots;
create policy "device update" on public.parking_slots for update to anon using (true) with check (true);
drop policy if exists "device update" on public.members;
create policy "device update" on public.members for update to anon using (true) with check (true);
drop policy if exists "device delete" on public.members;
create policy "device delete" on public.members for delete to anon using (true);

-- views run with the caller's rights so RLS still applies
alter view public.parking_summary  set (security_invoker = true);
alter view public.attendance_today set (security_invoker = true);
