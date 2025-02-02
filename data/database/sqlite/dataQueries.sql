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
