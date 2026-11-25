-- 06_cart_session.sql
-- カート追加後のサイト滞在時間（カート放棄の「介入できる時間」を測るため）
--   セッション = 同一訪問者のイベント間隔が30分以内で連続する区間
--   滞在時間 = カート追加時刻から、そのセッションの最後のイベントまでの時間
CREATE OR REPLACE TABLE cart_stay AS
WITH e AS (
    SELECT visitorid, ts_ms FROM events
    WHERE visitorid IN (SELECT visitorid FROM cart_units)
),
g AS (
    SELECT visitorid, ts_ms,
           CASE WHEN ts_ms - lag(ts_ms) OVER (PARTITION BY visitorid ORDER BY ts_ms) > 1800000 THEN 1 ELSE 0 END AS brk
    FROM e
),
s AS (
    SELECT visitorid, ts_ms, sum(brk) OVER (PARTITION BY visitorid ORDER BY ts_ms) AS sid FROM g
),
sess AS (
    SELECT visitorid, sid, min(ts_ms) AS s_start, max(ts_ms) AS s_end FROM s GROUP BY visitorid, sid
)
SELECT c.visitorid, c.itemid, c.seg, c.buy, c.lag_min,
       (s.s_end - c.t_cart) / 60000.0 AS stay_min
FROM cart_units c
JOIN sess s ON s.visitorid = c.visitorid AND c.t_cart BETWEEN s.s_start AND s.s_end;
