-- f02: 段階間の所要時間（一般訪問者・次の段階へ進んだ組のみ）
WITH v2c AS (   -- 閲覧→カート追加（閲覧後7日以内にカート追加した組）
    SELECT 'view_to_cart' AS stage, (f.t_cart - f.t_view) / 60000.0 AS lag_min
    FROM fp f JOIN visitor_seg s USING (visitorid)
    WHERE s.seg = 'regular' AND f.t_view IS NOT NULL AND f.t_cart >= f.t_view
      AND f.t_cart < f.t_view + ${FOLLOW_UP_DAYS} * 86400000
      AND f.t_view <= (SELECT max(ts_ms) FROM events) - ${FOLLOW_UP_DAYS} * 86400000
), c2b AS (     -- カート追加→購入
    SELECT 'cart_to_buy', lag_min FROM cart_units WHERE seg = 'regular' AND buy
), u AS (SELECT * FROM v2c UNION ALL SELECT * FROM c2b)
SELECT CASE stage WHEN 'view_to_cart' THEN '閲覧→カート追加' ELSE 'カート追加→購入' END AS "段階間",
       CASE WHEN lag_min <= 1 THEN '1分以内' WHEN lag_min <= 5 THEN '5分以内' WHEN lag_min <= 30 THEN '30分以内'
            WHEN lag_min <= 60 THEN '1時間以内' WHEN lag_min <= 1440 THEN '24時間以内' ELSE '24時間超（7日以内）' END AS "所要時間",
       CASE WHEN lag_min <= 1 THEN 1 WHEN lag_min <= 5 THEN 2 WHEN lag_min <= 30 THEN 3
            WHEN lag_min <= 60 THEN 4 WHEN lag_min <= 1440 THEN 5 ELSE 6 END AS "並び順",
       count(*) AS "件数",
       count(*)::DOUBLE / sum(count(*)) OVER (PARTITION BY stage) AS "構成比"
FROM u GROUP BY stage, 2, 3 ORDER BY stage DESC, 3;
