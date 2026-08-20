-- Seed inicial de aliases para resolver diferenças API-Football x The Odds API.
-- Requer tabelas leagues, teams e team_aliases já existentes.

WITH target_teams AS (
  SELECT t.id, t.name
  FROM teams t
  JOIN leagues l ON l.id = t.league_id
  WHERE l.slug = 'brasileirao-serie-a'
), aliases(source, external_name, canonical_name, external_id) AS (
  VALUES
    ('the_odds_api'::data_source, 'Bragantino-SP', 'RB Bragantino', 'bragantino-sp'),
    ('the_odds_api'::data_source, 'Atletico Mineiro', 'Atletico-MG', 'atletico-mineiro'),
    ('the_odds_api'::data_source, 'Cuiaba', 'Cuiaba', 'cuiaba'),
    ('api_football'::data_source, 'Atlético-MG', 'Atletico-MG', 'atletico-mg'),
    ('api_football'::data_source, 'Criciuma', 'Criciuma', 'criciuma')
)
INSERT INTO team_aliases (team_id, source, external_id, external_name)
SELECT t.id, a.source, a.external_id, a.external_name
FROM aliases a
JOIN target_teams t ON lower(unaccent(t.name)) = lower(unaccent(a.canonical_name))
ON CONFLICT (source, external_id) DO NOTHING;
