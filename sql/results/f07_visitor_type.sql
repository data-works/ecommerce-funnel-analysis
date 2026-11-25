-- f07: カート追加の経路による訪問者のタイプ別カート追加→購入率（一般訪問者、カートが1件以上ある訪問者）
WITH v AS (
    SELECT visitorid, count(*) AS n_cart, sum(buy::INT) AS n_buy, sum((NOT viewed_before)::INT) AS n_noview
    FROM cart_units WHERE seg = 'regular' GROUP BY visitorid
)
SELECT CASE WHEN n_noview = 0 THEN '1_すべて閲覧後にカート追加'
            WHEN n_noview = n_cart THEN '3_すべて閲覧なしでカート追加' ELSE '2_両方あり' END AS "訪問者タイプ",
       count(*) AS "訪問者数", sum(n_cart) AS "カート数", sum(n_buy) AS "購入数",
       sum(n_buy)::DOUBLE / sum(n_cart) AS "カート追加→購入率"
FROM v GROUP BY 1 ORDER BY 1;
