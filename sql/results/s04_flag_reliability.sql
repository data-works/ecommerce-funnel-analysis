-- s04: 在庫フラグの信頼度の確認（購入が起きた時点の在庫フラグ）
--   購入が起きたのに在庫なしと記録されている割合と、その前後のスナップショットでも在庫なしのままの割合
WITH a2 AS (
    SELECT itemid, t0, av, lead(av) OVER (PARTITION BY itemid ORDER BY t0) AS av_next FROM avail
),
t AS (
    SELECT e.itemid, x.av, x.av_next, g.grp
    FROM events e
    ASOF LEFT JOIN a2 x ON e.itemid = x.itemid AND e.ts_ms >= x.t0
    LEFT JOIN item_grp g ON g.itemid = e.itemid
    WHERE e.event = 'transaction'
)
SELECT count(*) FILTER (WHERE av IS NOT NULL) AS "在庫フラグが判明している購入数",
       count(*) FILTER (WHERE av = 0) AS "在庫なしと記録されている購入数",
       count(*) FILTER (WHERE av = 0)::DOUBLE / count(*) FILTER (WHERE av IS NOT NULL) AS "在庫なし記録の割合",
       count(*) FILTER (WHERE av = 0 AND av_next = 0) AS "うち次のスナップショットも在庫なし",
       count(*) FILTER (WHERE av = 0 AND grp = 'always_out') AS "うち常時在庫なしの商品"
FROM t;
