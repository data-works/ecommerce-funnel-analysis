-- 03_funnel_base.sql
-- ファネル分析の基礎テーブル

-- 各イベントにその時点のカテゴリ・在庫状態を付与（ASOF結合）
-- 記録開始前のイベント、および属性情報を持たない商品は NULL（不明）
CREATE OR REPLACE TABLE ev_cat AS
SELECT x.*, r.root AS root_category
FROM (
    SELECT e.*, c.categoryid, a.av
    FROM events e
    ASOF LEFT JOIN catprop c ON e.itemid = c.itemid AND e.ts_ms >= c.t0
    ASOF LEFT JOIN avail a   ON e.itemid = a.itemid AND e.ts_ms >= a.t0
) x
LEFT JOIN cat_root r ON r.categoryid = x.categoryid;

-- 訪問者区分: 期間中のイベント数100件以上を高頻度アクセス訪問者（全購入の約3割を占め、行動が大きく異なる）
CREATE OR REPLACE TABLE visitor_seg AS
SELECT visitorid, count(*) AS n_events,
       CASE WHEN count(*) >= ${HEAVY_THRESHOLD} THEN 'heavy' ELSE 'regular' END AS seg
FROM events GROUP BY visitorid;

-- 商品ページ閲覧数（期間中の総数による区分）
CREATE OR REPLACE TABLE item_pop AS
SELECT itemid, count(*) AS n_views,
       CASE WHEN count(*) >= 50 THEN '4_50件以上' WHEN count(*) >= 10 THEN '3_10-49件'
            WHEN count(*) >= 3 THEN '2_3-9件' ELSE '1_1-2件' END AS pop_tier
FROM events WHERE event = 'view' GROUP BY itemid;

-- 訪問者×商品ごとの各段階の初回時刻（ファネルの1単位）
CREATE OR REPLACE TABLE fp AS
SELECT visitorid, itemid,
       min(ts_ms) FILTER (WHERE event = 'view')        AS t_view,
       min(ts_ms) FILTER (WHERE event = 'addtocart')   AS t_cart,
       min(ts_ms) FILTER (WHERE event = 'transaction') AS t_buy
FROM events GROUP BY visitorid, itemid;
