-- 04_funnel_units.sql
-- ファネルの分析単位（訪問者×商品）。起点から ${FOLLOW_UP_DAYS} 日間の追跡期間を全件で確保するため、
-- 起点がログ最終時刻の ${FOLLOW_UP_DAYS} 日前までの組に限定する。
-- 追跡期間内の行動は events から直接判定する（初回イベント時刻だけで判定すると、先行する別の行動に引きずられるため）

-- (A) 閲覧起点: 最初の閲覧から7日以内のカート追加・購入
CREATE OR REPLACE TABLE view_units AS
WITH base AS (
    SELECT visitorid, itemid, t_view FROM fp
    WHERE t_view IS NOT NULL
      AND t_view <= (SELECT max(ts_ms) FROM events) - ${FOLLOW_UP_DAYS} * 86400000
),
outcome AS (
    SELECT b.visitorid, b.itemid,
           bool_or(e.event = 'addtocart')   AS cart,
           bool_or(e.event = 'transaction') AS buy
    FROM base b
    JOIN events e ON e.visitorid = b.visitorid AND e.itemid = b.itemid
                 AND e.event IN ('addtocart', 'transaction')
                 AND e.ts_ms >= b.t_view AND e.ts_ms < b.t_view + ${FOLLOW_UP_DAYS} * 86400000
    GROUP BY b.visitorid, b.itemid
)
SELECT b.visitorid, b.itemid, b.t_view, s.seg, p.pop_tier, g.grp,
       ec.root_category, ec.av,
       coalesce(o.cart, false) AS cart,
       coalesce(o.buy, false)  AS buy
FROM base b
JOIN visitor_seg s ON s.visitorid = b.visitorid
JOIN item_pop p ON p.itemid = b.itemid
LEFT JOIN item_grp g ON g.itemid = b.itemid
LEFT JOIN outcome o ON o.visitorid = b.visitorid AND o.itemid = b.itemid
LEFT JOIN ev_cat ec ON ec.visitorid = b.visitorid AND ec.itemid = b.itemid AND ec.ts_ms = b.t_view AND ec.event = 'view'
QUALIFY row_number() OVER (PARTITION BY b.visitorid, b.itemid ORDER BY ec.root_category NULLS LAST, ec.av NULLS LAST) = 1;

-- (B) カート起点: 初回カート追加から7日以内の購入
--   viewed_before: ログ上、カート追加より前に同一商品の閲覧がある
--   cart_size_1h : 同一訪問者が同じ暦時間（1時間枠）に初めてカートに入れた商品数
CREATE OR REPLACE TABLE cart_units AS
WITH c AS (
    SELECT visitorid, itemid, t_cart, t_view FROM fp
    WHERE t_cart IS NOT NULL
      AND t_cart <= (SELECT max(ts_ms) FROM events) - ${FOLLOW_UP_DAYS} * 86400000
),
outcome AS (
    SELECT c.visitorid, c.itemid, min(e.ts_ms) AS t_buy
    FROM c
    JOIN events e ON e.visitorid = c.visitorid AND e.itemid = c.itemid AND e.event = 'transaction'
                 AND e.ts_ms >= c.t_cart AND e.ts_ms < c.t_cart + ${FOLLOW_UP_DAYS} * 86400000
    GROUP BY c.visitorid, c.itemid
)
SELECT c.visitorid, c.itemid, c.t_cart, s.seg, p.pop_tier, g.grp, ec.root_category, ec.av,
       (c.t_view IS NOT NULL AND c.t_view <= c.t_cart) AS viewed_before,
       hour(to_timestamp(c.t_cart / 1000.0))      AS hour_utc,
       dayofweek(to_timestamp(c.t_cart / 1000.0)) AS dow,   -- 0=日曜
       count(*) OVER (PARTITION BY c.visitorid, c.t_cart // 3600000) AS cart_size_1h,
       o.t_buy IS NOT NULL AS buy,
       (o.t_buy - c.t_cart) / 60000.0 AS lag_min      -- カート追加→購入の所要時間（分）、購入なしは NULL
FROM c
JOIN visitor_seg s ON s.visitorid = c.visitorid
LEFT JOIN item_pop p ON p.itemid = c.itemid
LEFT JOIN item_grp g ON g.itemid = c.itemid
LEFT JOIN outcome o ON o.visitorid = c.visitorid AND o.itemid = c.itemid
LEFT JOIN ev_cat ec ON ec.visitorid = c.visitorid AND ec.itemid = c.itemid AND ec.ts_ms = c.t_cart AND ec.event = 'addtocart'
QUALIFY row_number() OVER (PARTITION BY c.visitorid, c.itemid ORDER BY ec.root_category NULLS LAST, ec.av NULLS LAST) = 1;
