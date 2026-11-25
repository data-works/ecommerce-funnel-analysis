-- f08: カート追加後のサイト滞在時間（一般訪問者）
--   購入あり: 購入までの所要時間 / 購入なし（カート放棄）: カート追加後に同じ訪問が続いた時間
WITH x AS (
    SELECT buy,
           CASE WHEN buy THEN lag_min ELSE stay_min END AS t
    FROM cart_stay WHERE seg = 'regular'
),
b AS (
    SELECT buy,
           CASE WHEN t <= 1 THEN '1_1分以内' WHEN t <= 5 THEN '2_5分以内' WHEN t <= 30 THEN '3_30分以内'
                WHEN t <= 60 THEN '4_1時間以内' ELSE '5_1時間超' END AS bucket
    FROM x
)
SELECT CASE WHEN buy THEN '購入あり（購入までの時間）' ELSE '購入なし（カート放棄、滞在時間）' END AS "区分",
       bucket AS "時間", count(*) AS "カート数",
       count(*)::DOUBLE / sum(count(*)) OVER (PARTITION BY buy) AS "構成比"
FROM b GROUP BY buy, bucket ORDER BY buy DESC, bucket;
