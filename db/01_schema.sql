-- Mobility AI — Knowledge Base PoC
-- Schema for the `quotations` table (per KB_SCAFFOLDING.md §4).
-- Run this once in the Supabase SQL editor (or via psql).
-- Idempotent: safe to re-run.

create extension if not exists "pgcrypto";

create table if not exists quotations (
  id                       uuid        primary key default gen_random_uuid(),
  created_at               timestamptz not null    default now(),
  uploaded_by              text,
  pdf_url                  text,
  vendor                   text        not null    default 'arval',

  -- Offer / customer identifiers
  offer_number             text,
  customer_code            text,
  customer_type            text        check (customer_type in ('b2c', 'b2b')),
  customer_first_name      text,
  customer_last_name       text,
  customer_fiscal_code     text,
  customer_birth_date      date,
  customer_gender          text        check (customer_gender in ('M', 'F')),
  customer_birth_place     text,
  customer_address_city    text,
  customer_address_province text,
  customer_address_cap     text,

  -- Vehicle
  vehicle_brand            text,
  vehicle_model            text,
  vehicle_version          text,
  vehicle_year             int,
  vehicle_type             text        check (vehicle_type in (
                              'city_car','berlina','sw','suv','crossover','monovolume','commercial'
                           )),
  motorization             text        check (motorization in (
                              'benzina','diesel','elettrico',
                              'hybrid_benzina','hybrid_diesel','phev','gpl','metano'
                           )),
  power_kw                 int,
  co2_emissions            int,
  transmission             text        check (transmission in ('manuale','automatico')),

  -- Commercials
  list_price               numeric(10,2),
  optional_price           numeric(10,2),
  duration_months          int,
  km_total                 int,
  km_annual                int generated always as (
                              (km_total::numeric * 12 / nullif(duration_months, 0)::numeric)::int
                           ) stored,
  monthly_fee              numeric(10,2),
  monthly_fee_lease        numeric(10,2),
  monthly_fee_services     numeric(10,2),
  anticipo                 numeric(10,2),
  deposito                 numeric(10,2),

  -- Services
  services_included        text[],
  services_excluded        text[],

  -- Provenance
  parsed_raw_json          jsonb,
  parser_version           text
);

-- Indexes from §4
create index if not exists idx_quotations_vendor        on quotations(vendor);
create index if not exists idx_quotations_vehicle_brand on quotations(vehicle_brand);
create index if not exists idx_quotations_vehicle_type  on quotations(vehicle_type);
create index if not exists idx_quotations_monthly_fee   on quotations(monthly_fee);
create index if not exists idx_quotations_duration      on quotations(duration_months);
create index if not exists idx_quotations_motorization  on quotations(motorization);
