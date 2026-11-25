-- f00: 高頻度アクセス訪問者（期間中のイベント100件以上）の位置づけ
SELECT count(DISTINCT s.visitorid) FILTER (WHERE s.seg = 'heavy') AS "高頻度アクセス訪問者数",
       count(DISTINCT s.visitorid) AS "全訪問者数",
       count(*) FILTER (WHERE s.seg = 'heavy')::DOUBLE / count(*) AS "イベント数に占める割合",
       count(*) FILTER (WHERE s.seg = 'heavy' AND e.event = 'addtocart')::DOUBLE
           / count(*) FILTER (WHERE e.event = 'addtocart') AS "カート追加に占める割合",
       count(*) FILTER (WHERE s.seg = 'heavy' AND e.event = 'transaction')::DOUBLE
           / count(*) FILTER (WHERE e.event = 'transaction') AS "購入に占める割合"
FROM events e JOIN visitor_seg s USING (visitorid);
