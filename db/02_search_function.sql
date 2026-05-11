-- Mobility AI — Knowledge Base PoC
-- search_quotations() RPC (per KB_SCAFFOLDING.md §4 + recency extension).
-- Auto-exposed by Supabase as POST /rest/v1/rpc/search_quotations.
-- Run after 01_schema.sql. Idempotent: CREATE OR REPLACE.
--
-- Recency factor (added 2026-05):
-- s_recency is a linear decay over RECENCY_HORIZON_MONTHS (24) computed from
-- q.created_at. Weight 0.10 — small enough that match-quality still dominates,
-- big enough that newer quotes win ties and beat moderately older quotes that
-- match only slightly better. Created_at is also returned as a top-level
-- column and broken out in score_breakdown.

create or replace function search_quotations(
  p_vendor                  text     default 'arval',
  p_customer_type           text     default null,
  p_target_monthly_fee      numeric  default null,
  p_target_duration_months  int      default null,
  p_target_km_total         int      default null,
  p_target_anticipo         numeric  default null,
  p_vehicle_type            text     default null,
  p_vehicle_brand           text     default null,
  p_motorization            text     default null,
  p_min_score               numeric  default 0.5,
  p_limit                   int      default 10
)
returns table (
  id                  uuid,
  created_at          timestamptz,
  offer_number        text,
  customer_full_name  text,
  vehicle_full_name   text,
  monthly_fee         numeric,
  duration_months     int,
  km_total            int,
  anticipo            numeric,
  vehicle_type        text,
  motorization        text,
  pdf_url             text,
  score               numeric,
  score_breakdown     jsonb
)
language plpgsql as $$
declare
  recency_horizon_days constant numeric := 24 * 30;  -- 24 months, treated as 720 days
begin
  return query
  with scored as (
    select
      q.id,
      q.created_at,
      q.offer_number,
      (q.customer_first_name || ' ' || q.customer_last_name) as customer_full_name,
      (q.vehicle_brand || ' ' || q.vehicle_model || ' ' || coalesce(q.vehicle_version, '')) as vehicle_full_name,
      q.monthly_fee,
      q.duration_months,
      q.km_total,
      q.anticipo,
      q.vehicle_type,
      q.motorization,
      q.pdf_url,

      -- Per-feature scores (each in [0,1], 1 = perfect match)
      case when p_target_monthly_fee is null then null
           else greatest(0, 1 - abs(q.monthly_fee - p_target_monthly_fee) / nullif(p_target_monthly_fee, 0))
      end as s_fee,

      case when p_target_duration_months is null then null
           else greatest(0, 1 - abs(q.duration_months - p_target_duration_months)::numeric / nullif(p_target_duration_months, 0))
      end as s_duration,

      case when p_target_km_total is null then null
           else greatest(0, 1 - abs(q.km_total - p_target_km_total)::numeric / nullif(p_target_km_total, 0))
      end as s_km,

      case when p_target_anticipo is null then null
           else greatest(0, 1 - abs(q.anticipo - p_target_anticipo) / nullif(greatest(p_target_anticipo, 1000), 0))
      end as s_anticipo,

      case when p_vehicle_type is null then null
           when q.vehicle_type = p_vehicle_type then 1.0
           else 0.0
      end as s_type,

      case when p_vehicle_brand is null then null
           when q.vehicle_brand = p_vehicle_brand then 1.0
           else 0.0
      end as s_brand,

      case when p_motorization is null then null
           when q.motorization = p_motorization then 1.0
           else 0.0
      end as s_motor,

      -- Recency: 1.0 for "just created", linearly decays to 0 at 24 months old.
      -- Always present (created_at is NOT NULL), so it always contributes.
      greatest(
        0,
        1 - extract(epoch from (now() - q.created_at)) / (recency_horizon_days * 86400)
      )::numeric as s_recency

    from quotations q
    where q.vendor = p_vendor
      and (p_customer_type is null or q.customer_type = p_customer_type)
  ),
  weighted as (
    select s.*,
      -- Weighted average over only the non-NULL components.
      -- Recency (0.10) is always counted; the rest are nulled-out when the
      -- corresponding filter wasn't provided.
      (
        coalesce(s.s_fee      * 0.30, 0) +
        coalesce(s.s_duration * 0.15, 0) +
        coalesce(s.s_km       * 0.15, 0) +
        coalesce(s.s_type     * 0.15, 0) +
        coalesce(s.s_brand    * 0.10, 0) +
        coalesce(s.s_anticipo * 0.10, 0) +
        coalesce(s.s_motor    * 0.05, 0) +
                 s.s_recency  * 0.10
      ) / nullif(
        (case when s.s_fee      is null then 0 else 0.30 end) +
        (case when s.s_duration is null then 0 else 0.15 end) +
        (case when s.s_km       is null then 0 else 0.15 end) +
        (case when s.s_type     is null then 0 else 0.15 end) +
        (case when s.s_brand    is null then 0 else 0.10 end) +
        (case when s.s_anticipo is null then 0 else 0.10 end) +
        (case when s.s_motor    is null then 0 else 0.05 end) +
        0.10,                            -- recency always on
      0) as final_score
    from scored s
  )
  select
    w.id,
    w.created_at,
    w.offer_number,
    w.customer_full_name,
    w.vehicle_full_name,
    w.monthly_fee,
    w.duration_months,
    w.km_total,
    w.anticipo,
    w.vehicle_type,
    w.motorization,
    w.pdf_url,
    round(w.final_score::numeric, 3) as score,
    jsonb_build_object(
      'fee',          round(w.s_fee::numeric,      3),
      'duration',     round(w.s_duration::numeric, 3),
      'km',           round(w.s_km::numeric,       3),
      'anticipo',     round(w.s_anticipo::numeric, 3),
      'vehicle_type', round(w.s_type::numeric,     3),
      'vehicle_brand',round(w.s_brand::numeric,    3),
      'motorization', round(w.s_motor::numeric,    3),
      'recency',      round(w.s_recency::numeric,  3)
    ) as score_breakdown
  from weighted w
  where w.final_score >= p_min_score
  order by w.final_score desc, w.created_at desc   -- newer wins on tie
  limit p_limit;
end;
$$;

-- Allow the anon role (used by the public REST endpoint) to call the RPC.
grant execute on function search_quotations(
  text, text, numeric, int, int, numeric, text, text, text, numeric, int
) to anon, authenticated;
