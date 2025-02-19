-- get post type distribution for all runs by id
select type, count() from scraper_scrapedata where scraper_run_id_id in (30, 31, 32) group by type;

-- get first and last datapoint of a run by run name
select * from (
    select * from scraper_scrapedata
    where scraper_run_id_id in
        (select id from scraper_scraperrun where name like '%bild%')
    order by id asc limit 1
)
union all
select * from (
    select * from scraper_scrapedata
    where scraper_run_id_id in
        (select id from scraper_scraperrun where name like '%bild%')
    order by id desc limit 1
);

-- get post type distribution for all runs by name
SELECT type, COUNT(*)
FROM scraper_scrapedata
WHERE scraper_scrapedata.scraper_run_id_id IN (
  SELECT id
  FROM scraper_scraperrun
  WHERE name LIKE '%bild%'
)
GROUP BY type;

-- get post type distribution for all runs
SELECT type, COUNT(*)
FROM scraper_scrapedata
GROUP BY type;

-- get hashtags count
SELECT 'no_hashtags' as hashtags, count(*)
FROM scraper_scrapedata
WHERE extracted_hashtags = '[]'
UNION ALL
SELECT 'has_hashtags' as hashtags, count(*)
FROM scraper_scrapedata
WHERE extracted_hashtags != '[]';

-- get hashtags distribution count by type
SELECT 'no_hashtags' as hashtags, type, count(*)
FROM scraper_scrapedata
WHERE extracted_hashtags = '[]'
GROUP BY type
UNION ALL
SELECT 'has_hashtags' as hashtags, type, count(*)
FROM scraper_scrapedata
WHERE extracted_hashtags != '[]'
GROUP BY type;

-- get hashtags distribution count by news portal
SELECT 'no_hashtags' as hashtags, scraper_scraperrun.profile_id, count(*)
FROM scraper_scrapedata
JOIN scraper_scraperrun ON scraper_scrapedata.scraper_run_id_id = scraper_scraperrun.id
WHERE extracted_hashtags = '[]'
GROUP BY scraper_scraperrun.profile_id
UNION ALL
SELECT 'has_hashtags' as hashtags, scraper_scraperrun.profile_id, count(*)
FROM scraper_scrapedata
JOIN scraper_scraperrun ON scraper_scrapedata.scraper_run_id_id = scraper_scraperrun.id
WHERE extracted_hashtags != '[]'
GROUP BY scraper_scraperrun.profile_id;

-- get hashtags distribution count by news portal and type
SELECT 'no_hashtags' as hashtags, scraper_scraperrun.profile_id, type, count(*)
FROM scraper_scrapedata
JOIN scraper_scraperrun ON scraper_scrapedata.scraper_run_id_id = scraper_scraperrun.id
WHERE extracted_hashtags = '[]'
GROUP BY scraper_scraperrun.profile_id, type
UNION ALL
SELECT 'has_hashtags' as hashtags, scraper_scraperrun.profile_id, type, count(*)
FROM scraper_scrapedata
JOIN scraper_scraperrun ON scraper_scrapedata.scraper_run_id_id = scraper_scraperrun.id
WHERE extracted_hashtags != '[]'
GROUP BY scraper_scraperrun.profile_id, type;


-- list and count all hashtags
WITH extracted AS (
  SELECT json_each.value as tag
  FROM scraper_scrapedata, json_each(scraper_scrapedata.extracted_hashtags)
)
SELECT
  tag,
  COUNT(*) as count
FROM extracted
GROUP BY tag
ORDER BY count DESC;