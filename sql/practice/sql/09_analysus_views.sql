DROP VIEW IF EXISTS v_ball;  -- so the file can be run twice 
 CREATE VIEW v_ball AS  SELECT d.*,                  -- keep every original column         
 CASE WHEN d.over_number <= 5  THEN 'Powerplay'             
WHEN d.over_number <= 14 THEN 'Middle'             
ELSE 'Death' END AS phase,         
-- ^ label each ball with its part of the innings           
CASE WHEN d.is_wide_ball = 0 AND d.is_no_ball = 0              
THEN 1 ELSE 0 END AS is_legal,         
-- ^ 1 if the ball counted towards the over, 0 if it was re-bowled            
d.total_runs - d.bye_runs - d.leg_bye_runs                      
- d.penalty_runs AS bowler_runs,         
-- ^ runs that were actually the bowler's fault            
CASE WHEN d.is_wicket = 1 AND d.wicket_kind NOT IN              
('run out','retired hurt','retired out',               
'obstructing the field')              
THEN 1 ELSE 0 END AS bowler_wicket         
-- ^ 1 only if the bowler gets the credit for the wicket     
FROM   deliveries d  
WHERE  d.is_super_over = 0;  -- drop the 175 tie-breaker balls 

DROP VIEW IF EXISTS v_innings;

CREATE VIEW v_innings AS
SELECT
    match_id,
    innings,
    MIN(batting_team) AS batting_team,
    MIN(bowling_team) AS bowling_team,
    SUM(total_runs) AS runs,
    SUM(is_wicket) AS wickets,
    SUM(is_legal) AS legal_balls
FROM v_ball
WHERE innings IN (1, 2)
GROUP BY match_id, innings;

DROP VIEW IF EXISTS v_match_totals;

CREATE VIEW v_match_totals AS
SELECT
    m.*,
    i1.runs AS first_innings_runs,
    i1.batting_team AS bat_first_team,

    CASE
        WHEN m.match_winner = i1.batting_team
        THEN 0
        ELSE 1
    END AS chase_won

FROM matches m

JOIN v_innings i1
    ON i1.match_id = m.match_id
    AND i1.innings = 1

WHERE m.result = 'win';