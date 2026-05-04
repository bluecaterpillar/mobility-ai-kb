-- Mobility AI — Knowledge Base PoC
-- Storage RLS policies for the `arval_quotes` bucket.
--
-- Why: storage.objects always has RLS enabled (you cannot disable it). Marking
-- a bucket as "Public" only opens anonymous SELECT via the public URL; INSERT
-- and DELETE still need explicit policies. Our PoC uses the anon key from the
-- Streamlit app, so anon needs full CRUD on objects in this bucket.
--
-- Run this AFTER creating the bucket `arval_quotes` (Storage → New bucket → Public).

drop policy if exists "anon_insert_arval_quotes" on storage.objects;
drop policy if exists "anon_select_arval_quotes" on storage.objects;
drop policy if exists "anon_delete_arval_quotes" on storage.objects;

create policy "anon_insert_arval_quotes"
on storage.objects for insert
to anon, authenticated
with check (bucket_id = 'arval_quotes');

create policy "anon_select_arval_quotes"
on storage.objects for select
to anon, authenticated
using (bucket_id = 'arval_quotes');

create policy "anon_delete_arval_quotes"
on storage.objects for delete
to anon, authenticated
using (bucket_id = 'arval_quotes');
