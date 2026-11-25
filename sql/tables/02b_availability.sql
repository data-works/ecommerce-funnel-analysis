-- 02b_availability.sql
-- 在庫フラグ(available)の履歴と商品グループ
--   在庫フラグは週次スナップショットのため、各イベント時点の状態は「直近の記録」で近似する

CREATE OR REPLACE TABLE avail AS
SELECT itemid, ts_ms AS t0, CAST(value AS INTEGER) AS av   -- 1 = 在庫あり, 0 = 在庫なし
FROM item_props
WHERE property = 'available';

-- 商品グループ: 観測期間を通じた在庫フラグの動き方
--   always_in: 常に在庫あり / always_out: 常に在庫なし / flip: 期間中に切り替わる
CREATE OR REPLACE TABLE item_grp AS
SELECT itemid,
       CASE WHEN min(av) = 1 AND max(av) = 1 THEN 'always_in'
            WHEN min(av) = 0 AND max(av) = 0 THEN 'always_out'
            ELSE 'flip' END AS grp
FROM avail GROUP BY itemid;
