-- s01: 在庫状態別の段階別の割合（一般訪問者、起点時点の在庫状態が判明している組）
WITH v AS (
    SELECT CASE grp WHEN 'always_in' THEN '常時在庫あり' WHEN 'always_out' THEN '常時在庫なし' ELSE '在庫変動あり' END AS g,
           CASE av WHEN 1 THEN '在庫あり' ELSE '在庫なし' END AS st,
           count(*) AS n_view, sum(cart::INT) AS n_cart_from_view, sum(buy::INT) AS n_buy_from_view
    FROM view_units WHERE seg = 'regular' AND av IS NOT NULL GROUP BY ALL
), c AS (
    SELECT CASE grp WHEN 'always_in' THEN '常時在庫あり' WHEN 'always_out' THEN '常時在庫なし' ELSE '在庫変動あり' END AS g,
           CASE av WHEN 1 THEN '在庫あり' ELSE '在庫なし' END AS st,
           count(*) AS n_cart, sum(buy::INT) AS n_buy
    FROM cart_units WHERE seg = 'regular' AND av IS NOT NULL GROUP BY ALL
)
SELECT v.g AS "商品区分", v.st AS "起点時点の在庫", n_view AS "閲覧組数",
       n_cart_from_view::DOUBLE / n_view AS "閲覧→カート追加率",
       n_buy_from_view::DOUBLE / n_view AS "閲覧→購入率",
       coalesce(n_cart, 0) AS "カート数（カート起点）",
       n_buy::DOUBLE / nullif(n_cart, 0) AS "カート追加→購入率"
FROM v LEFT JOIN c USING (g, st)
ORDER BY 1, 2;
