-- f05: 最上位カテゴリ別の段階別の割合（一般訪問者）
--   閲覧→カート追加率: 閲覧起点（7日以内）  /  カート追加→購入率: カート起点（7日以内）
WITH v AS (
    SELECT root_category, count(*) AS n_view, sum(cart::INT) AS n_cart_from_view
    FROM view_units WHERE seg = 'regular' AND root_category IS NOT NULL GROUP BY root_category
), c AS (
    SELECT root_category, count(*) AS n_cart, sum(buy::INT) AS n_buy
    FROM cart_units WHERE seg = 'regular' AND root_category IS NOT NULL GROUP BY root_category
)
SELECT v.root_category AS "カテゴリID", n_view AS "閲覧組数", n_cart_from_view AS "カート追加組数（閲覧起点）",
       n_cart_from_view::DOUBLE / n_view AS "閲覧→カート追加率",
       n_cart AS "カート数", n_buy AS "購入数（カート起点）", n_buy::DOUBLE / n_cart AS "カート追加→購入率"
FROM v JOIN c USING (root_category)
WHERE n_view >= 20000 AND n_cart >= 1000
ORDER BY n_view DESC;
