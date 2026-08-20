-- Seed da liga piloto e times do Brasileirão 2024 (API-Football league 71).
-- Necessário antes de team_aliases.

INSERT INTO leagues (slug, name, country, season)
VALUES ('brasileirao-serie-a', 'Brasileirão Série A', 'Brazil', '2024')
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  season = EXCLUDED.season,
  updated_at = now();

WITH league AS (
  SELECT id FROM leagues WHERE slug = 'brasileirao-serie-a'
), seed(slug, name, short_name) AS (
  VALUES
    ('bahia', 'Bahia', 'Bahia'),
    ('internacional', 'Internacional', 'Inter'),
    ('botafogo', 'Botafogo', 'Botafogo'),
    ('palmeiras', 'Palmeiras', 'Palmeiras'),
    ('fluminense', 'Fluminense', 'Fluminense'),
    ('sao-paulo', 'Sao Paulo', 'São Paulo'),
    ('flamengo', 'Flamengo', 'Flamengo'),
    ('gremio', 'Gremio', 'Grêmio'),
    ('corinthians', 'Corinthians', 'Corinthians'),
    ('vasco-da-gama', 'Vasco DA Gama', 'Vasco'),
    ('atletico-paranaense', 'Atletico Paranaense', 'Athletico-PR'),
    ('cruzeiro', 'Cruzeiro', 'Cruzeiro'),
    ('vitoria', 'Vitoria', 'Vitória'),
    ('criciuma', 'Criciuma', 'Criciúma'),
    ('atletico-goianiense', 'Atletico Goianiense', 'Atlético-GO'),
    ('juventude', 'Juventude', 'Juventude'),
    ('fortaleza-ec', 'Fortaleza EC', 'Fortaleza'),
    ('rb-bragantino', 'RB Bragantino', 'Bragantino'),
    ('atletico-mg', 'Atletico-MG', 'Atlético-MG'),
    ('cuiaba', 'Cuiaba', 'Cuiabá')
)
INSERT INTO teams (league_id, slug, name, short_name)
SELECT l.id, s.slug, s.name, s.short_name
FROM league l
CROSS JOIN seed s
ON CONFLICT (league_id, slug) DO UPDATE SET
  name = EXCLUDED.name,
  short_name = EXCLUDED.short_name,
  updated_at = now();
