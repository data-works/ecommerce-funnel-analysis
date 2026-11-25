-- 01_load_raw.sql
-- 生データの読み込みと基本的なクレンジング
-- 実行環境: DuckDB（CSVを直接読み込めるため、前処理なしでSQLのみで処理可能）

-- 行動ログ。完全重複行（同一ミリ秒・同一ユーザー・同一商品・同一イベント）は1行にまとめる
CREATE OR REPLACE TABLE events AS
SELECT DISTINCT
    timestamp                       AS ts_ms,        -- UNIXミリ秒（UTC）
    to_timestamp(timestamp / 1000.0) AS ts,
    visitorid,
    event,
    itemid,
    transactionid
FROM read_csv('data/events.csv', header = true,
              types = {'timestamp': 'BIGINT', 'visitorid': 'BIGINT', 'event': 'VARCHAR',
                       'itemid': 'BIGINT', 'transactionid': 'DOUBLE'});

-- 商品属性（2ファイルを結合）。1行 = ある時点での属性値のスナップショット
CREATE OR REPLACE TABLE item_props AS
SELECT timestamp AS ts_ms, itemid, property, value
FROM read_csv(['data/item_properties_part1.csv', 'data/item_properties_part2.csv'],
              header = true,
              types = {'timestamp': 'BIGINT', 'itemid': 'BIGINT', 'property': 'VARCHAR', 'value': 'VARCHAR'});

-- カテゴリ階層
CREATE OR REPLACE TABLE category_tree AS
SELECT categoryid, parentid FROM read_csv('data/category_tree.csv', header = true);
