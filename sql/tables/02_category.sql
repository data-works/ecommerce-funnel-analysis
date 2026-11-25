-- 02_category.sql
-- カテゴリの履歴と最上位カテゴリ（root）。商品のカテゴリは時間とともに変わりうるため、履歴のまま保持する
CREATE OR REPLACE TABLE catprop AS
SELECT itemid, ts_ms AS t0, CAST(value AS BIGINT) AS categoryid
FROM item_props
WHERE property = 'categoryid';

CREATE OR REPLACE TABLE cat_root AS
WITH RECURSIVE r (categoryid, root, depth) AS (
    SELECT categoryid, categoryid, 0 FROM category_tree WHERE parentid IS NULL
    UNION ALL
    SELECT c.categoryid, r.root, r.depth + 1
    FROM category_tree c JOIN r ON c.parentid = r.categoryid
)
SELECT categoryid, root, depth FROM r;
