"""在庫状態が各段階の割合に与える影響の推定（一般訪問者）

在庫なしの商品は、そもそも人気や品質が異なる可能性がある。そこで次の3通りで比べる。
  単純比較       : 在庫なし vs 在庫あり（全商品）
  商品内比較     : 在庫変動あり商品について、同一商品の在庫あり期間 vs 在庫なし期間（Mantel-Haenszel型で統合）
  訪問者内比較   : 同一訪問者が在庫あり商品・在庫なし商品を見た場合（在庫変動あり商品）
信頼区間は層（商品・訪問者）単位のブートストラップ（1,000回）。
出力: s10_stock_effects.csv  （比 = 在庫あり時の割合 / 在庫なし時の割合）
"""
import numpy as np
import pandas as pd
from common import TABLE_DIR, connect

B = 1000
rng = np.random.default_rng(20260102)


def strata(con, table, outcome, key, where, both):
    having = "HAVING sum((av = 0)::INT) > 0 AND sum((av = 1)::INT) > 0" if both else ""
    return con.execute(f"""
        SELECT {key} AS k, sum((av = 0)::INT) AS n1, sum((av = 0 AND {outcome})::INT) AS a,
                           sum((av = 1)::INT) AS n0, sum((av = 1 AND {outcome})::INT) AS c
        FROM {table} WHERE seg = 'regular' AND av IS NOT NULL AND {where}
        GROUP BY 1 {having}""").fetchdf()


def naive(d, w):
    return ((w * d.c).sum() / (w * d.n0).sum()) / ((w * d.a).sum() / (w * d.n1).sum())


def mh(d, w):
    n = d.n0 + d.n1
    return (w * d.c * d.n1 / n).sum() / (w * d.a * d.n0 / n).sum()


def est(d, fn):
    e = fn(d, np.ones(len(d)))
    p = np.full(len(d), 1 / len(d))
    bs = [fn(d, rng.multinomial(len(d), p).astype(float)) for _ in range(B)]
    return e, *np.percentile(bs, [2.5, 97.5])


def main():
    con = connect()
    specs = [
        # (段階, 単位テーブル, 結果列, 比較方法, 層のキー, 条件, 両状態必須, 推定量)
        ("閲覧→カート追加", "view_units", "cart", "単純比較（全商品）", "itemid", "TRUE", False, naive),
        ("閲覧→カート追加", "view_units", "cart", "商品内比較", "itemid", "grp = 'flip'", True, mh),
        ("閲覧→カート追加", "view_units", "cart", "訪問者内比較", "visitorid", "grp = 'flip'", True, mh),
        ("カート追加→購入", "cart_units", "buy", "単純比較（全商品）", "itemid", "TRUE", False, naive),
        ("カート追加→購入", "cart_units", "buy", "商品内比較", "itemid", "grp = 'flip'", True, mh),
    ]
    rows = []
    for stage, tbl, out, name, key, where, both, fn in specs:
        d = strata(con, tbl, out, key, where, both)
        e, lo, hi = est(d, fn)
        rows.append({"段階": stage, "比較方法": name, "層の数": len(d),
                     "在庫なしの組数": int(d.n1.sum()), "在庫ありの組数": int(d.n0.sum()),
                     "在庫なしの成功数": int(d.a.sum()), "在庫ありの成功数": int(d.c.sum()),
                     "率の比（在庫あり/在庫なし）": e, "95%CI下限": lo, "95%CI上限": hi})
        print(stage, name, len(d), round(e, 2), round(lo, 2), round(hi, 2))
    # 最初の閲覧: 在庫変動あり商品について、同一商品の在庫なし期間 / 在庫あり期間の「最初の閲覧後の再行動なし率」の比
    #   （この表だけは比の向きが逆で、在庫なし ÷ 在庫あり。1より大きいほど、在庫なしのとき再行動が少ない）
    ft = con.execute("""
        SELECT itemid AS k, sum((av = 0)::INT) AS n1, sum((av = 0 AND n_after = 0)::INT) AS a,
               sum((av = 1)::INT) AS n0, sum((av = 1 AND n_after = 0)::INT) AS c
        FROM first_touch WHERE seg = 'regular' AND grp = 'flip' AND av IS NOT NULL
        GROUP BY 1 HAVING sum((av = 0)::INT) > 0 AND sum((av = 1)::INT) > 0""").fetchdf()
    inv = lambda d, w: 1 / mh(d, w)     # mh は (在庫あり率/在庫なし率) なので逆数をとる。ここでの「率」は再行動なし率
    e, lo, hi = est(ft, lambda d, w: mh(d.rename(columns={"a": "c", "c": "a", "n1": "n0", "n0": "n1"}), w))
    rows.append({"段階": "最初の閲覧後の再行動なし率", "比較方法": "商品内比較（在庫なし÷在庫あり）", "層の数": len(ft),
                 "在庫なしの組数": int(ft.n1.sum()), "在庫ありの組数": int(ft.n0.sum()),
                 "在庫なしの成功数": int(ft.a.sum()), "在庫ありの成功数": int(ft.c.sum()),
                 "率の比（在庫あり/在庫なし）": e, "95%CI下限": lo, "95%CI上限": hi})
    print("最初の閲覧 再行動なし率 商品内比較(在庫なし/在庫あり)", len(ft), round(e, 3), round(lo, 3), round(hi, 3))
    eff = pd.DataFrame(rows).rename(columns={"率の比（在庫あり/在庫なし）": "比"})
    eff.to_csv(TABLE_DIR / "s10_stock_effects.csv", index=False, encoding="utf-8-sig")

    # 改善余地の試算: 在庫変動商品の在庫なし期間の閲覧が、在庫あり期間並みに「カート追加」へ転換した場合
    v = con.execute("""
        SELECT sum((grp = 'flip' AND av = 0)::INT) AS n_out,
               sum((grp = 'flip' AND av = 0 AND cart)::INT) AS cart_out,
               sum(cart::INT) AS cart_all
        FROM view_units WHERE seg = 'regular'""").fetchone()
    c2b = con.execute("""SELECT avg(buy::INT) FROM cart_units WHERE seg = 'regular' AND grp = 'flip' AND av = 1""").fetchone()[0]
    r_item = eff.loc[(eff["段階"] == "閲覧→カート追加") & (eff["比較方法"] == "商品内比較"), "比"].iloc[0]
    r_vis = eff.loc[(eff["段階"] == "閲覧→カート追加") & (eff["比較方法"] == "訪問者内比較"), "比"].iloc[0]
    sz = pd.DataFrame([{"シナリオ": "下限（訪問者内比較の比）", "比": r_vis}, {"シナリオ": "上限（商品内比較の比）", "比": r_item}])
    sz["在庫変動商品の在庫なし期間の閲覧組数"] = v[0]
    sz["現在のカート追加組数（在庫なし期間）"] = v[1]
    sz["追加のカート追加組数"] = v[1] * (sz["比"] - 1)
    sz["全カート追加組数（閲覧起点）に対する割合"] = sz["追加のカート追加組数"] / v[2]
    sz["追加の購入数（カート追加→購入率を乗じた目安）"] = sz["追加のカート追加組数"] * c2b
    sz.to_csv(TABLE_DIR / "s11_stock_gap_sizing.csv", index=False, encoding="utf-8-sig")
    print(sz.to_string())


if __name__ == "__main__":
    main()
