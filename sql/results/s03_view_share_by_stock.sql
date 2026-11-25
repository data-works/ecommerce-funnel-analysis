-- s03: 閲覧された商品（訪問者×商品、一般訪問者）の在庫区分別シェア
SELECT CASE WHEN grp = 'always_in' THEN '常時在庫あり'
            WHEN grp = 'always_out' THEN '常時在庫なし'
            WHEN grp = 'flip' AND av = 1 THEN '在庫変動あり（在庫あり期間）'
            WHEN grp = 'flip' AND av = 0 THEN '在庫変動あり（在庫なし期間）'
            WHEN grp IS NULL THEN '属性情報なし' ELSE '在庫変動あり（状態不明）' END AS "区分",
       count(*) AS "閲覧組数", count(*)::DOUBLE / sum(count(*)) OVER () AS "シェア"
FROM view_units
WHERE seg = 'regular' AND t_view >= (SELECT min(t0) FROM avail)
GROUP BY 1 ORDER BY 2 DESC;
