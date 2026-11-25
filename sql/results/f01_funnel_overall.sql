-- f01: ファネルの全体像
-- (1) 訪問者単位（追跡期間なし・全期間）
SELECT '訪問者単位' AS "単位", '一般' AS "訪問者区分", 1 AS "段階順", '閲覧' AS "段階", count(DISTINCT visitorid) AS "件数"
FROM events e JOIN visitor_seg s USING (visitorid) WHERE e.event = 'view' AND s.seg = 'regular'
UNION ALL SELECT '訪問者単位', '一般', 2, 'カート追加', count(DISTINCT visitorid)
FROM events e JOIN visitor_seg s USING (visitorid) WHERE e.event = 'addtocart' AND s.seg = 'regular'
UNION ALL SELECT '訪問者単位', '一般', 3, '購入', count(DISTINCT visitorid)
FROM events e JOIN visitor_seg s USING (visitorid) WHERE e.event = 'transaction' AND s.seg = 'regular'
-- (2) 訪問者×商品単位（最初の閲覧から7日以内）
UNION ALL SELECT '訪問者×商品（閲覧起点）', CASE seg WHEN 'regular' THEN '一般' ELSE '高頻度アクセス' END, 1, '閲覧', count(*) FROM view_units GROUP BY seg
UNION ALL SELECT '訪問者×商品（閲覧起点）', CASE seg WHEN 'regular' THEN '一般' ELSE '高頻度アクセス' END, 2, 'カート追加', sum(cart::INT) FROM view_units GROUP BY seg
UNION ALL SELECT '訪問者×商品（閲覧起点）', CASE seg WHEN 'regular' THEN '一般' ELSE '高頻度アクセス' END, 3, '購入', sum(buy::INT) FROM view_units GROUP BY seg
-- (3) カート起点（カート追加から7日以内の購入）
UNION ALL SELECT '訪問者×商品（カート起点）', CASE seg WHEN 'regular' THEN '一般' ELSE '高頻度アクセス' END, 2, 'カート追加', count(*) FROM cart_units GROUP BY seg
UNION ALL SELECT '訪問者×商品（カート起点）', CASE seg WHEN 'regular' THEN '一般' ELSE '高頻度アクセス' END, 3, '購入', sum(buy::INT) FROM cart_units GROUP BY seg
ORDER BY 1, 2, 3;
