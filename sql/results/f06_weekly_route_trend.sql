-- f06: 週次のカート追加数と「閲覧なしカート追加」の割合・カート追加→購入率（一般訪問者）
SELECT strftime(date_trunc('week', to_timestamp(t_cart / 1000.0)), '%Y-%m-%d') AS "週開始日",
       count(*) AS "カート数",
       avg((NOT viewed_before)::INT) AS "閲覧なしカート追加の割合",
       avg(buy::INT) AS "カート追加→購入率",
       avg(buy::INT) FILTER (WHERE viewed_before) AS "カート追加→購入率（閲覧後）",
       avg(buy::INT) FILTER (WHERE NOT viewed_before) AS "カート追加→購入率（閲覧なし）"
FROM cart_units
WHERE seg = 'regular'
  AND t_cart >= 1430697600000   -- 2015-05-04（月）以降の完全な週のみ
  AND t_cart <  1442188800000   -- 2015-09-14（月）より前
GROUP BY 1 ORDER BY 1;
