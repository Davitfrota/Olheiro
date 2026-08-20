-- Complete aliases for Brasileirão + clubs present in current Odds API.

INSERT INTO teams (league_id, slug, name, short_name)
SELECT l.id, v.slug, v.name, v.short_name
FROM leagues l
CROSS JOIN (VALUES
  ('chapecoense', 'Chapecoense', 'CHA'),
  ('coritiba', 'Coritiba', 'CFC'),
  ('mirassol', 'Mirassol', 'MIR'),
  ('remo', 'Remo', 'REM'),
  ('santos', 'Santos', 'SAN')
) AS v(slug, name, short_name)
WHERE l.slug = 'brasileirao-serie-a'
ON CONFLICT (league_id, slug) DO NOTHING;

WITH target_teams AS (
  SELECT t.id, t.name, t.slug
  FROM teams t
  JOIN leagues l ON l.id = t.league_id
  WHERE l.slug = 'brasileirao-serie-a'
), aliases(source, external_name, team_slug, external_id) AS (
  VALUES
    ('api_football'::data_source, 'Atlético-MG', 'atletico-mg', 'atletico-mg-accent'),
    ('api_football'::data_source, 'Atletico-MG', 'atletico-mg', 'atletico-mg'),
    ('api_football'::data_source, 'Criciuma', 'criciuma', 'criciuma'),
    ('api_football'::data_source, 'Criciúma', 'criciuma', 'criciuma-accent'),
    ('api_football'::data_source, 'Cuiabá', 'cuiaba', 'cuiaba-accent'),
    ('api_football'::data_source, 'Cuiaba', 'cuiaba', 'cuiaba-af'),
    ('api_football'::data_source, 'Grêmio', 'gremio', 'gremio-accent'),
    ('api_football'::data_source, 'Gremio', 'gremio', 'gremio-af'),
    ('api_football'::data_source, 'São Paulo', 'sao-paulo', 'sao-paulo-accent'),
    ('api_football'::data_source, 'Sao Paulo', 'sao-paulo', 'sao-paulo-af'),
    ('api_football'::data_source, 'Vasco DA Gama', 'vasco-da-gama', 'vasco-af'),
    ('api_football'::data_source, 'Vasco da Gama', 'vasco-da-gama', 'vasco-af-2'),
    ('api_football'::data_source, 'RB Bragantino', 'rb-bragantino', 'rb-bragantino-af'),
    ('api_football'::data_source, 'Red Bull Bragantino', 'rb-bragantino', 'rb-bragantino-full'),
    ('api_football'::data_source, 'Fortaleza EC', 'fortaleza-ec', 'fortaleza-af'),
    ('api_football'::data_source, 'Fortaleza', 'fortaleza-ec', 'fortaleza-short'),
    ('api_football'::data_source, 'Atletico Goianiense', 'atletico-goianiense', 'atletico-go'),
    ('api_football'::data_source, 'Atlético Goianiense', 'atletico-goianiense', 'atletico-go-accent'),
    ('api_football'::data_source, 'Atletico Paranaense', 'atletico-paranaense', 'athletico-af'),
    ('api_football'::data_source, 'Athletico Paranaense', 'atletico-paranaense', 'athletico-af-2'),
    ('the_odds_api'::data_source, 'Atletico Mineiro', 'atletico-mg', 'atletico-mineiro'),
    ('the_odds_api'::data_source, 'Bragantino-SP', 'rb-bragantino', 'bragantino-sp'),
    ('the_odds_api'::data_source, 'Cuiaba', 'cuiaba', 'cuiaba-odds'),
    ('the_odds_api'::data_source, 'Gremio', 'gremio', 'gremio-odds'),
    ('the_odds_api'::data_source, 'Grêmio', 'gremio', 'gremio-odds-accent'),
    ('the_odds_api'::data_source, 'Sao Paulo', 'sao-paulo', 'sao-paulo-odds'),
    ('the_odds_api'::data_source, 'Vasco da Gama', 'vasco-da-gama', 'vasco-odds'),
    ('the_odds_api'::data_source, 'Atletico Paranaense', 'atletico-paranaense', 'athletico-odds'),
    ('the_odds_api'::data_source, 'Athletico-PR', 'atletico-paranaense', 'athletico-pr'),
    ('the_odds_api'::data_source, 'Fortaleza', 'fortaleza-ec', 'fortaleza-odds'),
    ('the_odds_api'::data_source, 'Bahia', 'bahia', 'bahia-odds'),
    ('the_odds_api'::data_source, 'Botafogo', 'botafogo', 'botafogo-odds'),
    ('the_odds_api'::data_source, 'Corinthians', 'corinthians', 'corinthians-odds'),
    ('the_odds_api'::data_source, 'Cruzeiro', 'cruzeiro', 'cruzeiro-odds'),
    ('the_odds_api'::data_source, 'Flamengo', 'flamengo', 'flamengo-odds'),
    ('the_odds_api'::data_source, 'Fluminense', 'fluminense', 'fluminense-odds'),
    ('the_odds_api'::data_source, 'Internacional', 'internacional', 'internacional-odds'),
    ('the_odds_api'::data_source, 'Juventude', 'juventude', 'juventude-odds'),
    ('the_odds_api'::data_source, 'Palmeiras', 'palmeiras', 'palmeiras-odds'),
    ('the_odds_api'::data_source, 'Vitoria', 'vitoria', 'vitoria-odds'),
    ('the_odds_api'::data_source, 'Chapecoense', 'chapecoense', 'chapecoense-odds'),
    ('the_odds_api'::data_source, 'Coritiba', 'coritiba', 'coritiba-odds'),
    ('the_odds_api'::data_source, 'Mirassol', 'mirassol', 'mirassol-odds'),
    ('the_odds_api'::data_source, 'Remo', 'remo', 'remo-odds'),
    ('the_odds_api'::data_source, 'Santos', 'santos', 'santos-odds')
)
INSERT INTO team_aliases (team_id, source, external_id, external_name)
SELECT t.id, a.source, a.external_id, a.external_name
FROM aliases a
JOIN target_teams t ON t.slug = a.team_slug
ON CONFLICT (source, external_id) DO UPDATE
SET external_name = EXCLUDED.external_name,
    team_id = EXCLUDED.team_id;
