-- f03: カート放棄の回収状況（一般訪問者）
--   カート放棄 = カート追加から24時間以内に同一商品を購入しなかった組
--   ※ 同一商品を購入した組の97%は24時間以内に購入しているため、24時間を放置の目安とした
WITH a AS (
    SELECT visitorid, itemid, t_cart, root_category
    FROM cart_units
    WHERE seg = 'regular' AND NOT (lag_min IS NOT NULL AND lag_min <= 1440)
),
r AS (
    SELECT a.visitorid, a.itemid, a.t_cart,
           bool_or(e.event IS NOT NULL AND e.ts_ms > a.t_cart + 3600000)                       AS returned_1h,   -- 1時間後以降に何らかの行動
           bool_or(e.event IS NOT NULL AND e.ts_ms > a.t_cart + 86400000)                      AS returned_24h,  -- 24時間後以降に何らかの行動
           bool_or(e.event = 'transaction' AND e.itemid = a.itemid AND e.ts_ms >= a.t_cart)   AS buy_same,
           bool_or(e.event = 'transaction' AND e.ts_ms >= a.t_cart)                           AS buy_any
    FROM a
    LEFT JOIN events e ON e.visitorid = a.visitorid AND e.ts_ms >= a.t_cart
                      AND e.ts_ms < a.t_cart + ${FOLLOW_UP_DAYS} * 86400000
    GROUP BY a.visitorid, a.itemid, a.t_cart
)
SELECT count(*) AS "カート放棄数",
       avg(coalesce(returned_1h, false)::INT)  AS "1時間後以降に再訪した割合",
       avg(coalesce(returned_24h, false)::INT) AS "24時間後以降に再訪した割合",
       avg(coalesce(buy_same, false)::INT)     AS "7日以内に同一商品を購入した割合",
       avg(coalesce(buy_any, false)::INT)      AS "7日以内に何らかの購入をした割合"
FROM r;
