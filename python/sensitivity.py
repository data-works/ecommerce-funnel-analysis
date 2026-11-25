"""感度分析: 高頻度アクセス訪問者の閾値を変えても、主要な結果が変わらないかを確認する
出力: f14_sensitivity.csv
"""
import pandas as pd
from common import TABLE_DIR, connect


def main():
    con = connect()
    rows = []
    for th in [30, 50, 100, 200, 100000000]:   # 100000000 = 高頻度アクセス訪問者を分けない（全訪問者）
        r = con.execute(f"""
            SELECT count(*) AS carts, avg(c.buy::INT) AS c2b,
                   avg(c.buy::INT) FILTER (WHERE c.viewed_before) AS c2b_view,
                   avg(c.buy::INT) FILTER (WHERE NOT c.viewed_before) AS c2b_noview,
                   avg((NOT c.viewed_before)::INT) AS noview_share,
                   count(DISTINCT c.visitorid) FILTER (WHERE s.n_events >= {th}) AS heavy_visitors
            FROM cart_units c JOIN visitor_seg s USING (visitorid)
            WHERE s.n_events < {th}""").fetchdf().iloc[0]
        rows.append({"高頻度アクセス訪問者の閾値（イベント数）": "分けない" if th > 1e6 else th,
                     "対象カート数": int(r.carts), "カート追加→購入率": r.c2b,
                     "カート追加→購入率（閲覧後）": r.c2b_view, "カート追加→購入率（閲覧なし）": r.c2b_noview,
                     "閲覧なしカート追加の割合": r.noview_share})
    out = pd.DataFrame(rows)
    out.to_csv(TABLE_DIR / "f14_sensitivity.csv", index=False, encoding="utf-8-sig")
    print(out.to_string())


if __name__ == "__main__":
    main()
