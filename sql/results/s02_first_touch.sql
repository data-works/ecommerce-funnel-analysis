-- s02: 最初の閲覧の商品の在庫状態別の離脱率・購入率（一般訪問者、訪問者単位）
SELECT CASE grp WHEN 'always_in' THEN '常時在庫あり' WHEN 'always_out' THEN '常時在庫なし'
               WHEN 'flip' THEN '在庫変動あり' ELSE '属性情報なし' END AS "商品区分",
       CASE av WHEN 1 THEN '在庫あり' WHEN 0 THEN '在庫なし' ELSE '不明' END AS "最初の閲覧時の在庫",
       count(*) AS "訪問者数",
       avg((n_after = 0)::INT) AS "最初の閲覧後の再行動なし率",
       avg((n_tx > 0)::INT) AS "7日以内購入率"
FROM first_touch
WHERE seg = 'regular' AND (av IS NOT NULL OR grp IS NULL)
GROUP BY ALL ORDER BY 1, 2;
