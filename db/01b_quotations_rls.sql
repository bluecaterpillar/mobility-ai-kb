-- Mobility AI — Knowledge Base PoC
-- Disable RLS on the `quotations` table.
--
-- Why: in this PoC the only auth gate is the mock login in lib/auth.py and
-- every request from the Streamlit app uses the Supabase anon key. Spec
-- hard constraint #3 explicitly forbids real auth, so any RLS policy here
-- would be fictitious. The public RPC search_quotations also runs as the
-- caller (SECURITY INVOKER by default) and would see zero rows under a
-- restrictive RLS policy.
--
-- Supabase enables RLS by default on tables in the `public` schema, so
-- without this statement INSERT and the public REST API both 42501.
--
-- Idempotent: safe to re-run.

alter table quotations disable row level security;
