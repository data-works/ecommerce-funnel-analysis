"""SQLによるテーブル構築と集計結果のCSV出力

実行: python python/run_pipeline.py  （リポジトリのルートで実行。data/ に元データを配置しておくこと）
"""
import time
from common import ROOT, TABLE_DIR, connect, render_sql


def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    con = connect()

    # 1. 分析用テーブルの構築
    for f in sorted((ROOT / "sql" / "tables").glob("*.sql")):
        t = time.time()
        con.execute(render_sql(f))
        print(f"[tables] {f.name}  {time.time() - t:.1f}s")

    # 2. 集計クエリの実行 → CSV出力（ファイル名がそのまま出力CSV名になる）
    for f in sorted((ROOT / "sql" / "results").glob("*.sql")):
        df = con.execute(render_sql(f)).fetchdf()
        df.to_csv(TABLE_DIR / f"{f.stem}.csv", index=False, encoding="utf-8-sig")
        print(f"[results] {f.stem}.csv  {len(df)} rows")


if __name__ == "__main__":
    main()
