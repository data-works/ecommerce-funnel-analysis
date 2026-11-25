-- f09: 追跡期間（7日）の妥当性の確認
--   カート追加から24時間以内に購入されなかったカート（カート放棄）のうち、14日間の追跡ができるものについて、
--   同一商品の購入が「24時間〜7日」と「7〜14日」のそれぞれで何件起きたかを比べる
WITH a AS (
    SELECT c.visitorid, c.itemid, c.t_cart
    FROM fp c JOIN visitor_seg s USING (visitorid)
    WHERE s.seg = 'regular' AND c.t_cart IS NOT NULL
      AND c.t_cart <= (SELECT max(ts_ms) FROM events) - 14 * 86400000
      AND NOT EXISTS (SELECT 1 FROM events e WHERE e.visitorid = c.visitorid AND e.itemid = c.itemid
                      AND e.event = 'transaction' AND e.ts_ms >= c.t_cart AND e.ts_ms < c.t_cart + 86400000)
)
SELECT count(*) AS "カート放棄数",
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM events e WHERE e.visitorid = a.visitorid AND e.itemid = a.itemid
            AND e.event = 'transaction' AND e.ts_ms >= a.t_cart + 86400000 AND e.ts_ms < a.t_cart + 7 * 86400000)) AS "24時間〜7日の同一商品購入数",
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM events e WHERE e.visitorid = a.visitorid AND e.itemid = a.itemid
            AND e.event = 'transaction' AND e.ts_ms >= a.t_cart + 7 * 86400000 AND e.ts_ms < a.t_cart + 14 * 86400000)) AS "7〜14日の同一商品購入数"
FROM a;
