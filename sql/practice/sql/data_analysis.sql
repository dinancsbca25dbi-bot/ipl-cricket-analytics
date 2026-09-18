-- ============================================================
-- STUDENT PRACTICE
-- ============================================================


-- ============================================================
-- 1. Find the top 10 grounds by number of matches
-- ============================================================

SELECT
    venue_clean,
    COUNT(*) AS matches
FROM matches_clean
GROUP BY venue_clean
ORDER BY matches DESC
LIMIT 10;

-- Explanation:
-- venue_clean gives the cleaned name of each ground.
-- COUNT(*) counts the matches played at each ground.
-- GROUP BY groups the matches according to each ground.
-- ORDER BY DESC arranges the grounds from highest to lowest
-- number of matches.
-- LIMIT 10 displays only the top 10 grounds.


-- ============================================================
-- 2. Find grounds with an average innings score above 165
--    using a minimum of 25 matches
-- ============================================================

SELECT
    m.venue_clean,
    ROUND(AVG(i.runs), 2) AS average_score
FROM matches_clean AS m
JOIN v_innings AS i
    ON m.match_id = i.match_id
GROUP BY m.venue_clean
HAVING COUNT(DISTINCT m.match_id) >= 25
   AND AVG(i.runs) > 165
ORDER BY average_score DESC;

-- Explanation:
-- JOIN connects the matches_clean table with v_innings.
-- AVG(i.runs) calculates the average innings score.
-- ROUND(..., 2) rounds the average score to 2 decimal places.
-- GROUP BY groups the innings according to each ground.
-- COUNT(DISTINCT m.match_id) counts unique matches.
-- >= 25 selects grounds with at least 25 matches.
-- AVG(i.runs) > 165 selects grounds with an average score
-- above 165.
-- ORDER BY DESC shows the highest average score first.


-- ============================================================
-- 3. Calculate the chase win percentage
--    for grounds with at least 50 matches
-- ============================================================

SELECT
    venue_clean,
    ROUND(
        100.0 * SUM(chase_won) / COUNT(*),
        2
    ) AS chase_win_percentage
FROM v_match_totals
GROUP BY venue_clean
HAVING COUNT(*) >= 50
ORDER BY chase_win_percentage DESC;

-- Explanation:
-- venue_clean gives the ground name.
-- SUM(chase_won) counts the chase wins because chase_won
-- is represented using 1 for a chase win and 0 otherwise.
-- COUNT(*) counts the total matches.
-- 100.0 converts the result into a percentage.
-- ROUND(..., 2) rounds the percentage to 2 decimal places.
-- GROUP BY creates one result for each ground.
-- HAVING COUNT(*) >= 50 selects grounds with at least
-- 50 matches.
-- ORDER BY DESC shows the highest chase win percentage first.


-- ============================================================
-- 4. Count the number of unique cleaned venues
-- ============================================================

SELECT
    COUNT(DISTINCT venue_clean) AS unique_venues
FROM matches_clean;

-- Explanation:
-- venue_clean contains the cleaned venue names.
-- DISTINCT removes duplicate venue names.
-- COUNT counts the remaining unique venues.
-- The result gives the total number of unique cleaned venues.


-- ============================================================
-- 5. Find the five grounds with the lowest
--    Powerplay run rate
-- ============================================================

SELECT
    m.venue_clean,
    ROUND(
        6.0 * SUM(v.batter_runs) / SUM(v.is_legal),
        2
    ) AS powerplay_run_rate
FROM v_ball AS v
JOIN matches_clean AS m
    ON v.match_id = m.match_id
WHERE v.phase = 'Powerplay'
GROUP BY m.venue_clean
ORDER BY powerplay_run_rate ASC
LIMIT 5;

-- Explanation:
-- v_ball contains ball-by-ball information.
-- JOIN connects the ball data with the ground information.
-- WHERE phase = 'Powerplay' selects only Powerplay balls.
-- SUM(v.batter_runs) calculates the total runs.
-- SUM(v.is_legal) counts the legal balls.
-- 6.0 converts runs per legal ball into runs per over.
-- ROUND(..., 2) rounds the run rate to 2 decimal places.
-- GROUP BY calculates the run rate for each ground.
-- ORDER BY ASC puts the lowest run rates first.
-- LIMIT 5 displays the five grounds with the lowest
-- Powerplay run rate.


-- ============================================================
-- 6. Explain why COUNT(DISTINCT match_id) can be safer than COUNT(*) after a JOIN.
-- ============================================================

SELECT
    COUNT(DISTINCT match_id) AS unique_matches
FROM v_innings;

-- Explanation:
-- COUNT(*) counts every row.
-- After a JOIN, the same match can appear in multiple rows.
-- This can make COUNT(*) count the same match more than once.
-- COUNT(DISTINCT match_id) removes duplicate match IDs
-- and counts each match only once.
-- Therefore, COUNT(DISTINCT match_id) is safer when we
-- want to count the actual number of matches.


-- ============================================================
-- 7. Explain why the day/night question cannot be answered from match_date alone.
-- ============================================================

-- Explanation:
-- match_date tells us the date on which the match happened.
-- It does not tell us the starting time of the match.
-- Therefore, match_date alone cannot tell whether the match
-- was played during the day or at night.
-- We would need additional information such as the match
-- start time or a day/night indicator.