-- Mobility AI — Knowledge Base PoC
-- 20 hand-crafted seed records for the `quotations` table (per spec §7).
--
-- ------------------------------------------------------------------------
-- WHAT THIS SEED IS DESIGNED TO PROVE
-- ------------------------------------------------------------------------
-- Coverage:
--   • 20 rows total · 12 b2c + 8 b2b
--   • Full vehicle_type enum: 5 suv, 3 berlina, 3 city_car, 3 sw,
--     3 crossover, 2 monovolume, 1 commercial
--   • Full motorization enum (≥2 each): 3 benzina, 4 diesel, 2 elettrico,
--     2 hybrid_benzina, 2 hybrid_diesel, 3 phev, 2 gpl, 2 metano
--   • Durations: 36, 48, 60 (no 24 — would be unusually short for NLT)
--   • Fees: 280–720 €/mese (within spec band 250–950)
--   • km_total: 60.000 (city) → 150.000 (B2B fleet, 60mo). B2C capped at 100k.
--   • created_at: explicit per row, spread across last 18 months so the
--     recency factor in search_quotations() has something interesting to
--     score. Distribution:
--        – 4 quotes within the last 30 days  (s_recency ≈ 0.95–1.00)
--        – 3 quotes 1–3 months old           (s_recency ≈ 0.86–0.95)
--        – 3 quotes 3–6 months old           (s_recency ≈ 0.75–0.86)
--        – 4 quotes 6–12 months old          (s_recency ≈ 0.50–0.75)
--        – 6 quotes 12–18 months old         (s_recency ≈ 0.25–0.50)
--
-- Test scenarios:
--
--   1. SUV PHEV ~650€ / 48 mesi / 100k km   (min_score 0.80, all features active)
--      Filter: type=suv, motorization=phev, target_fee=650,
--              target_duration=48, target_km=100000.
--      Expected ranking with recency factor enabled (weight 0.10):
--        • Mattina Napoli (uploaded via the app)  → ≈ 1.00
--        • Giulia Padova   (BYD SEAL U Comfort, recent)   → ≈ 0.89
--        • Sofia Bari      (Volvo XC40 Recharge,  9mo old) → ≈ 0.88
--        • Marco Verona    (VW Tiguan diesel,    recent)   → ≈ 0.86
--        • Lorenzo Bologna (Toyota C-HR hybrid, 8mo old)   → ≈ 0.85
--        • Andrea Trento   (Cupra Formentor, 15mo old)     → ≈ 0.84
--      Recency now lifts Giulia above Sofia (closer match, but Giulia is
--      newer) and pushes Andrea down. A diesel SUV (Marco) still surfaces
--      as a near-match alternative.
--
--   2. City car benzina ~280€ / 36 mesi
--      Filter: type=city_car, motorization=benzina, target_fee=280,
--      target_duration=36.
--      Expected: Chiara Genova (Fiat Panda 1.2 Pop) → ≈ 1.00, then the
--      e-C3 (elettrico) and the Panda GPL as fuzzy alternatives.
--
--   3. Berlina elettrica B2B ~600€ / 48 mesi
--      Returns Federica Pisa's Tesla Model 3 as a strong match.
--
--   4. Empty filters
--      Returns all 21 rows ordered by recency (s_recency drives score),
--      effectively a "latest quotes first" feed.
--
-- ------------------------------------------------------------------------
-- IDEMPOTENCY
-- ------------------------------------------------------------------------
-- Re-running this script wipes prior seed rows (parser_version='seed-v1')
-- and re-inserts. Records uploaded via the Streamlit app are tagged
-- parser_version='claude-haiku-4-5-v1' and are preserved.
--
-- The trailing UPDATE backfills a fictitious customer_fiscal_code on the
-- Mattina Napoli record (the source PDF leaves "CF Cliente" blank, so the
-- parser correctly returns null; the mock value is needed for demo coherence).

begin;

delete from quotations where parser_version = 'seed-v1';

insert into quotations (
  created_at,
  vendor, offer_number, customer_code, customer_type,
  customer_first_name, customer_last_name, customer_fiscal_code,
  customer_birth_date, customer_gender, customer_birth_place,
  customer_address_city, customer_address_province, customer_address_cap,
  vehicle_brand, vehicle_model, vehicle_version, vehicle_year,
  vehicle_type, motorization, power_kw, co2_emissions, transmission,
  list_price, optional_price, duration_months, km_total,
  monthly_fee, monthly_fee_lease, monthly_fee_services, anticipo, deposito,
  services_included, services_excluded, parser_version, uploaded_by
) values

-- 1. Lorenzo Bologna · b2c · Toyota C-HR Hybrid · 8mo old
('2025-09-10 10:32:00+00',
 'arval', '15780001/1', 'N10001', 'b2c',
 'Lorenzo', 'Bologna', 'LRZBLG85C12A944M', '1985-03-12', 'M', 'Bologna',
 'Bologna', 'BO', '40121',
 'Toyota', 'C-HR', '2.0 Hybrid Lounge', 2024,
 'suv', 'hybrid_benzina', 144, 110, 'automatico',
 38500.00, 800.00, 48, 100000,
 540.50, 378.35, 162.15, 4500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 2. Giulia Padova · b2c · BYD SEAL U DM-i Comfort · 30gg fa (SUV PHEV neighbour, recent)
('2026-04-05 09:14:00+00',
 'arval', '15780002/1', 'N10002', 'b2c',
 'Giulia', 'Padova', 'GLIPDV90A41G224R', '1990-01-01', 'F', 'Padova',
 'Padova', 'PD', '35121',
 'BYD', 'SEAL U DM-i', '1.5 324cv Comfort', 2024,
 'suv', 'phev', 96, 75, 'automatico',
 44900.00, 600.00, 36, 80000,
 595.00, 416.50, 178.50, 5000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 3. Marco Verona · b2b · VW Tiguan TDI · 2.5mo old (diesel SUV alt)
('2026-02-20 14:05:00+00',
 'arval', '15780003/1', 'B20001', 'b2b',
 'Marco', 'Verona', null, null, null, null,
 'Verona', 'VR', '37121',
 'Volkswagen', 'Tiguan', '2.0 TDI 150cv Life', 2023,
 'suv', 'diesel', 110, 145, 'manuale',
 41200.00, 1200.00, 48, 120000,
 580.00, 406.00, 174.00, 3000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 4. Sofia Bari · b2c · Volvo XC40 Recharge PHEV · 9mo old (premium SUV-PHEV)
('2025-08-15 11:22:00+00',
 'arval', '15780004/1', 'N10003', 'b2c',
 'Sofia', 'Bari', 'SFOBRI88L67A662H', '1988-07-27', 'F', 'Bari',
 'Bari', 'BA', '70121',
 'Volvo', 'XC40', 'Recharge T5 PHEV Inscription', 2024,
 'suv', 'phev', 180, 47, 'automatico',
 51800.00, 1500.00, 60, 100000,
 720.00, 504.00, 216.00, 6000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko','pneumatici','veicolo_sostitutivo'],
 ARRAY[]::text[],
 'seed-v1', 'system'),

-- 5. Andrea Trento · b2c · Cupra Formentor e-Hybrid · 15mo old (PHEV ma vecchio)
('2025-02-10 16:48:00+00',
 'arval', '15780005/1', 'N10004', 'b2c',
 'Andrea', 'Trento', 'NDRTNT82B15L378Q', '1982-02-15', 'M', 'Trento',
 'Trento', 'TN', '38121',
 'Cupra', 'Formentor', '1.5 e-Hybrid 245cv VZ', 2024,
 'suv', 'phev', 180, 35, 'automatico',
 47500.00, 900.00, 60, 90000,
 580.00, 406.00, 174.00, 5500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 6. Chiara Genova · b2c · Fiat Panda Pop benzina · 20gg fa
('2026-04-15 08:55:00+00',
 'arval', '15780006/1', 'N10005', 'b2c',
 'Chiara', 'Genova', 'CHRGNV92E55D969L', '1992-05-15', 'F', 'Genova',
 'Genova', 'GE', '16121',
 'Fiat', 'Panda', '1.2 8v Pop', 2024,
 'city_car', 'benzina', 51, 134, 'manuale',
 14900.00, 0.00, 36, 60000,
 280.00, 196.00, 84.00, 1500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente'],
 ARRAY['kasko','pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 7. Simone Cagliari · b2c · Citroen e-C3 elettrico · 4mo old
('2026-01-10 15:31:00+00',
 'arval', '15780007/1', 'N10006', 'b2c',
 'Simone', 'Cagliari', 'SMNCGL94H08B354Y', '1994-06-08', 'M', 'Cagliari',
 'Cagliari', 'CA', '09121',
 'Citroen', 'e-C3', '100kW You', 2024,
 'city_car', 'elettrico', 83, 0, 'automatico',
 23900.00, 0.00, 36, 60000,
 320.00, 224.00, 96.00, 2500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 8. Davide Lecce · b2b · Fiat Panda GPL · 16mo old
('2025-01-05 10:08:00+00',
 'arval', '15780008/1', 'B20002', 'b2b',
 'Davide', 'Lecce', null, null, null, null,
 'Lecce', 'LE', '73100',
 'Fiat', 'Panda', '1.2 8v Easy GPL', 2023,
 'city_car', 'gpl', 51, 132, 'manuale',
 15200.00, 0.00, 36, 75000,
 295.00, 206.50, 88.50, 1200.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente'],
 ARRAY['kasko','pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 9. Elena Catania · b2c · BMW Serie 1 118d · 5mo old
('2025-12-15 09:42:00+00',
 'arval', '15780009/1', 'N10007', 'b2c',
 'Elena', 'Catania', 'LNECTN87M52C351W', '1987-08-12', 'F', 'Catania',
 'Catania', 'CT', '95121',
 'BMW', 'Serie 1', '118d Business Advantage', 2024,
 'berlina', 'diesel', 110, 122, 'automatico',
 33900.00, 700.00, 48, 100000,
 480.00, 336.00, 144.00, 4000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 10. Alessio Trieste · b2b · Audi A3 35 TFSI · 2mo old
('2026-03-12 13:00:00+00',
 'arval', '15780010/1', 'B20003', 'b2b',
 'Alessio', 'Trieste', null, null, null, null,
 'Trieste', 'TS', '34121',
 'Audi', 'A3 Sportback', '35 TFSI S tronic Business', 2024,
 'berlina', 'benzina', 110, 132, 'automatico',
 36800.00, 1100.00, 36, 90000,
 510.00, 357.00, 153.00, 3500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 11. Federica Pisa · b2b · Tesla Model 3 SR+ elettrico · 15gg fa
('2026-04-20 12:17:00+00',
 'arval', '15780011/1', 'B20004', 'b2b',
 'Federica', 'Pisa', null, null, null, null,
 'Pisa', 'PI', '56121',
 'Tesla', 'Model 3', 'Standard Range Plus RWD', 2023,
 'berlina', 'elettrico', 208, 0, 'automatico',
 44900.00, 0.00, 48, 100000,
 615.00, 430.50, 184.50, 6000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 12. Luca Brescia · b2b · Skoda Octavia SW TDI · 10mo old (fleet workhorse)
('2025-07-22 07:38:00+00',
 'arval', '15780012/1', 'B20005', 'b2b',
 'Luca', 'Brescia', null, null, null, null,
 'Brescia', 'BS', '25121',
 'Skoda', 'Octavia SW', '2.0 TDI 150cv Style', 2024,
 'sw', 'diesel', 110, 130, 'manuale',
 32500.00, 800.00, 60, 150000,
 470.00, 329.00, 141.00, 2500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko','pneumatici'],
 ARRAY['veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 13. Martina Modena · b2c · Volvo V60 B4 MHEV · 17mo old
('2024-12-15 11:51:00+00',
 'arval', '15780013/1', 'N10008', 'b2c',
 'Martina', 'Modena', 'MRTMDN89D60F257K', '1989-04-20', 'F', 'Modena',
 'Modena', 'MO', '41121',
 'Volvo', 'V60', 'B4 Mild Hybrid 197cv Plus', 2024,
 'sw', 'hybrid_diesel', 145, 135, 'automatico',
 47200.00, 900.00, 48, 100000,
 615.00, 430.50, 184.50, 5000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 14. Beatrice Como · b2c · Mercedes Classe C SW MHEV · 6mo old (premium SW)
('2025-11-20 14:23:00+00',
 'arval', '15780014/1', 'N10009', 'b2c',
 'Beatrice', 'Como', 'BTRCMO91P44C933T', '1991-09-04', 'F', 'Como',
 'Como', 'CO', '22100',
 'Mercedes', 'Classe C SW', 'C 220 d 4MATIC Mild Hybrid', 2024,
 'sw', 'hybrid_diesel', 147, 138, 'automatico',
 56800.00, 1500.00, 48, 100000,
 720.00, 504.00, 216.00, 6000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko','pneumatici','veicolo_sostitutivo'],
 ARRAY[]::text[],
 'seed-v1', 'system'),

-- 15. Stefano Treviso · b2c · VW T-Roc benzina · 1.5mo old
('2026-03-25 08:11:00+00',
 'arval', '15780015/1', 'N10010', 'b2c',
 'Stefano', 'Treviso', 'STFTVS84C18L407D', '1984-03-18', 'M', 'Treviso',
 'Treviso', 'TV', '31100',
 'Volkswagen', 'T-Roc', '1.5 TSI ACT 150cv Style', 2024,
 'crossover', 'benzina', 110, 138, 'manuale',
 31200.00, 600.00, 36, 75000,
 425.00, 297.50, 127.50, 3500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 16. Valentina Parma · b2c · Hyundai Kona HEV · 7gg fa
('2026-04-28 17:04:00+00',
 'arval', '15780016/1', 'N10011', 'b2c',
 'Valentina', 'Parma', 'VLNPRM93H58G337X', '1993-06-18', 'F', 'Parma',
 'Parma', 'PR', '43121',
 'Hyundai', 'Kona', '1.6 GDi HEV Xline', 2024,
 'crossover', 'hybrid_benzina', 104, 111, 'automatico',
 32800.00, 700.00, 48, 100000,
 460.00, 322.00, 138.00, 4000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 17. Roberto Rimini · b2b · Renault Captur GPL · 11mo old
('2025-06-30 09:47:00+00',
 'arval', '15780017/1', 'B20006', 'b2b',
 'Roberto', 'Rimini', null, null, null, null,
 'Rimini', 'RN', '47921',
 'Renault', 'Captur', '1.0 TCe 100cv GPL Equilibre', 2024,
 'crossover', 'gpl', 74, 127, 'manuale',
 24500.00, 300.00, 48, 120000,
 380.00, 266.00, 114.00, 2000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente'],
 ARRAY['kasko','pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 18. Caterina Salerno · b2c · Citroen C4 Picasso BlueHDi · 17mo old
('2024-11-28 13:18:00+00',
 'arval', '15780018/1', 'N10012', 'b2c',
 'Caterina', 'Salerno', 'CTRSLN86D50H703V', '1986-04-10', 'F', 'Salerno',
 'Salerno', 'SA', '84121',
 'Citroen', 'C4 Picasso', '1.5 BlueHDi 130 Feel', 2022,
 'monovolume', 'diesel', 96, 118, 'manuale',
 27800.00, 400.00, 48, 100000,
 395.00, 276.50, 118.50, 3000.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko'],
 ARRAY['pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 19. Gianluca Ravenna · b2b · Fiat Doblò metano · 18mo old
('2024-11-10 10:02:00+00',
 'arval', '15780019/1', 'B20007', 'b2b',
 'Gianluca', 'Ravenna', null, null, null, null,
 'Ravenna', 'RA', '48121',
 'Fiat', 'Doblò', '1.4 T-Jet Natural Power', 2023,
 'monovolume', 'metano', 88, 116, 'manuale',
 22500.00, 500.00, 60, 150000,
 365.00, 255.50, 109.50, 1500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente'],
 ARRAY['kasko','pneumatici','veicolo_sostitutivo'],
 'seed-v1', 'system'),

-- 20. Silvia Ancona · b2b · Iveco Daily CNG · 18mo old (fleet van)
('2024-10-25 06:36:00+00',
 'arval', '15780020/1', 'B20008', 'b2b',
 'Silvia', 'Ancona', null, null, null, null,
 'Ancona', 'AN', '60121',
 'Iveco', 'Daily', '35S14 NP Furgone CNG', 2024,
 'commercial', 'metano', 100, 209, 'manuale',
 38500.00, 800.00, 60, 150000,
 540.00, 378.00, 162.00, 2500.00, null,
 ARRAY['manutenzione','soccorso_stradale','rca','infortunio_conducente','kasko','pneumatici'],
 ARRAY['veicolo_sostitutivo'],
 'seed-v1', 'system');

-- Backfill the mock fiscal code on the Mattina Napoli record uploaded via
-- the app in Milestone C (PDF leaves "CF Cliente" blank so the parser
-- correctly returned null; mock value provided by the user for demo).
update quotations
set customer_fiscal_code = 'RSSMRA80A01H501U'
where offer_number = '15789678/1'
  and customer_last_name = 'Napoli'
  and customer_fiscal_code is null;

commit;

-- Sanity checks (run separately to confirm):
--   select count(*) from quotations;                                      -- expect 21 (20 seed + 1 Mattina)
--   select customer_type, count(*) from quotations group by 1;            -- 12 b2c, 8 b2b, +1 b2c (Mattina) = 13/8
--   select vehicle_type, count(*) from quotations group by 1 order by 2;  -- coverage of all 7 enums
--   select motorization, count(*) from quotations group by 1 order by 2;  -- coverage of all 8 enums
--
--   -- Scenario 1: SUV PHEV ~650€ 48mo 100k km (recency-aware ranking)
--   select customer_full_name, vehicle_full_name, monthly_fee,
--          to_char(created_at, 'DD/MM/YYYY') as data, score,
--          score_breakdown->>'recency' as s_recency
--     from search_quotations(
--       p_target_monthly_fee := 650,
--       p_target_duration_months := 48,
--       p_target_km_total := 100000,
--       p_vehicle_type := 'suv',
--       p_motorization := 'phev',
--       p_min_score := 0.80
--     );
