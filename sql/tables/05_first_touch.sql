-- 05_first_touch.sql
-- 最初の閲覧: 訪問者が最初の閲覧の商品の在庫状態と、その後の行動（ファネルの入口）
-- 在庫フラグの記録開始以降、かつ追跡期間を確保できる訪問者のみ
CREATE OR REPLACE TABLE first_touch AS
WITH ranked AS (
    SELECT *, row_number() OVER (
        PARTITION BY visitorid
        ORDER BY ts_ms, CASE event WHEN 'view' THEN 0 WHEN 'addtocart' THEN 1 ELSE 2 END, itemid) AS rn
    FROM ev_cat
),
f AS (
    SELECT * FROM ranked
    WHERE rn = 1 AND event = 'view'
      AND ts_ms >= (SELECT min(t0) FROM avail)
      AND ts_ms <= (SELECT max(ts_ms) FROM events) - ${FOLLOW_UP_DAYS} * 86400000
)
SELECT f.visitorid, f.itemid, f.av, g.grp, s.seg,
       coalesce(a.n_after, 0) AS n_after,   -- 最初の閲覧後の追加イベント数
       coalesce(b.n_tx, 0)    AS n_tx       -- 最初の閲覧後の購入件数
FROM f
LEFT JOIN item_grp g    ON g.itemid = f.itemid
LEFT JOIN visitor_seg s ON s.visitorid = f.visitorid
LEFT JOIN (SELECT f.visitorid, count(*) AS n_after
           FROM f JOIN events e ON e.visitorid = f.visitorid AND e.ts_ms > f.ts_ms
                                AND e.ts_ms < f.ts_ms + ${FOLLOW_UP_DAYS} * 86400000
           GROUP BY f.visitorid) a ON a.visitorid = f.visitorid
LEFT JOIN (SELECT f.visitorid, count(*) AS n_tx
           FROM f JOIN events e ON e.visitorid = f.visitorid AND e.event = 'transaction' AND e.ts_ms >= f.ts_ms
                                AND e.ts_ms < f.ts_ms + ${FOLLOW_UP_DAYS} * 86400000
           GROUP BY f.visitorid) b ON b.visitorid = f.visitorid;
