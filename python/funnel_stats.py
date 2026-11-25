"""カート追加→購入率の差の統計的な確認と、改善余地の試算（一般訪問者）

同一訪問者が複数のカートを持つため、行（カート）を独立とみなす信頼区間は狭くなりすぎる。
そのため信頼区間はすべて「訪問者単位のブートストラップ（1,000回）」、回帰は訪問者単位のクラスタ頑健標準誤差で求める。

1. セグメント別カート追加→購入率とその95%信頼区間                    -> f10_segment_ci.csv
2. 全体平均を有意に下回るセグメントを平均まで引き上げた場合の追加購入数（上限の目安） -> f11_gap_sizing.csv
3. ロジスティック回帰（各要因の影響を互いに調整）                  -> f12_logit.csv
4. 「閲覧なしカート追加」の差が、商品・訪問者の違いによるものでないかの確認     -> f13_route_robustness.csv
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import TABLE_DIR, connect

B = 1000
rng = np.random.default_rng(20260101)


def load():
    con = connect()
    d = con.execute("""
        SELECT visitorid, itemid, buy::INT AS buy, viewed_before, pop_tier,
          CASE WHEN hour_utc BETWEEN 15 AND 21 THEN '15〜21時'
               WHEN hour_utc BETWEEN 8 AND 14 THEN '8〜14時' ELSE '22〜7時' END AS g_hour,
          CASE WHEN dow IN (1,2,3,4) THEN '月〜木' WHEN dow = 5 THEN '金' WHEN dow = 6 THEN '土' ELSE '日' END AS g_dow,
          CASE WHEN cart_size_1h >= 5 THEN '5件以上' ELSE cart_size_1h::VARCHAR || '件' END AS g_size,
          CASE WHEN viewed_before THEN '閲覧後にカート追加' ELSE '閲覧なしでカート追加' END AS g_route,
          CASE pop_tier WHEN '1_1-2件' THEN '1-2件' WHEN '2_3-9件' THEN '3-9件' WHEN '3_10-49件' THEN '10-49件'
                        WHEN '4_50件以上' THEN '50件以上' END AS g_pop
        FROM cart_units WHERE seg = 'regular'""").fetchdf()
    return d


AXES = {"時間帯（UTC）": "g_hour", "曜日": "g_dow", "同時にカート追加した商品数（同一1時間内）": "g_size",
        "閲覧の有無": "g_route", "商品ページ閲覧数（期間中の総数）": "g_pop"}


def segment_table(d):
    rows = []
    vid, vidx = np.unique(d.visitorid.values, return_inverse=True)
    for axis, col in AXES.items():
        dd = d.dropna(subset=[col])
        cats = sorted(dd[col].unique())
        n = np.zeros((len(vid), len(cats))); b = np.zeros_like(n)
        for j, c in enumerate(cats):
            m = dd[col] == c
            np.add.at(n[:, j], vidx[dd.index[m]], 1)
            np.add.at(b[:, j], vidx[dd.index[m]], dd.buy[m].values)
        boots = np.empty((B, len(cats)))
        p = np.full(len(vid), 1 / len(vid))
        for k in range(B):
            w = rng.multinomial(len(vid), p).astype(float)
            boots[k] = (w @ b) / np.maximum(w @ n, 1)
        lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
        for j, c in enumerate(cats):
            rows.append({"軸": axis, "区分": c, "カート数": int(n[:, j].sum()), "購入数": int(b[:, j].sum()),
                         "カート追加→購入率": b[:, j].sum() / n[:, j].sum(), "95%CI下限": lo[j], "95%CI上限": hi[j]})
    out = pd.DataFrame(rows)
    out["全体平均"] = d.buy.mean()
    return out


def mh_ratio(df, w):
    """Mantel-Haenszel型: 層内で比較して統合した 閲覧あり購入率 / 閲覧なし購入率"""
    n = df.n0 + df.n1
    return (w * df.c * df.n1 / n).sum() / (w * df.a * df.n0 / n).sum()


def route_robustness(d):
    """閲覧なし(n1,a) と 閲覧あり(n0,c) を、層（商品 / 訪問者）内で比較する"""
    rows = []
    naive = d.groupby("viewed_before").buy.agg(["sum", "count"])
    for key, label in [("itemid", "商品内比較"), ("visitorid", "訪問者内比較")]:
        g = d.groupby(key).apply(lambda x: pd.Series({
            "n1": (~x.viewed_before).sum(), "a": x.buy[~x.viewed_before].sum(),
            "n0": x.viewed_before.sum(), "c": x.buy[x.viewed_before].sum()}), include_groups=False)
        g = g[(g.n1 > 0) & (g.n0 > 0)]
        est = mh_ratio(g, np.ones(len(g)))
        boots = [mh_ratio(g, rng.multinomial(len(g), np.full(len(g), 1 / len(g))).astype(float)) for _ in range(B)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append({"比較方法": label, "層の数": len(g), "閲覧なしのカート数": int(g.n1.sum()), "閲覧後のカート数": int(g.n0.sum()),
                     "購入率比（閲覧後/閲覧なし）": est, "95%CI下限": lo, "95%CI上限": hi})
    p1 = naive.loc[True, "sum"] / naive.loc[True, "count"]; p0 = naive.loc[False, "sum"] / naive.loc[False, "count"]
    rows.insert(0, {"比較方法": "単純比較", "層の数": np.nan, "閲覧なしのカート数": int(naive.loc[False, "count"]),
                    "閲覧後のカート数": int(naive.loc[True, "count"]), "購入率比（閲覧後/閲覧なし）": p1 / p0,
                    "95%CI下限": np.nan, "95%CI上限": np.nan})
    return pd.DataFrame(rows)


def within_visitor(d):
    """時間帯・曜日・同時にカート追加した商品数・商品ページ閲覧数の差が、訪問者の違いによるものでないかを確認する。
    同一訪問者が基準区分と比較区分の両方でカートを持つ場合に限り、訪問者内で購入率を比べる。"""
    specs = [("時間帯（UTC）", "g_hour", "15〜21時", "8〜14時"),
             ("曜日", "g_dow", "月〜木", ["土", "日"]),
             ("同時にカート追加した商品数（同一1時間内）", "g_size", "1件", "5件以上"),
             ("商品ページ閲覧数（期間中の総数）", "g_pop", "50件以上", "1-2件")]
    rows = []
    for axis, col, ref, cmp_ in specs:
        cmp_ = cmp_ if isinstance(cmp_, list) else [cmp_]
        x = d[d[col].isin([ref] + cmp_)].copy()
        x["is_ref"] = x[col] == ref
        g = x.groupby("visitorid").apply(lambda t: pd.Series({
            "n1": (~t.is_ref).sum(), "a": t.buy[~t.is_ref].sum(), "n0": t.is_ref.sum(), "c": t.buy[t.is_ref].sum()}), include_groups=False)
        g = g[(g.n1 > 0) & (g.n0 > 0)]
        est = mh_ratio(g, np.ones(len(g)))
        p = np.full(len(g), 1 / len(g))
        bs = [mh_ratio(g, rng.multinomial(len(g), p).astype(float)) for _ in range(B)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        pooled = (x.buy[x.is_ref].mean()) / (x.buy[~x.is_ref].mean())
        rows.append({"軸": axis, "基準区分": ref, "比較区分": "・".join(cmp_), "訪問者数（両方に該当）": len(g),
                     "基準のカート数": int(g.n0.sum()), "比較のカート数": int(g.n1.sum()),
                     "購入率の比（単純比較）": pooled, "購入率の比（訪問者内比較）": est, "95%CI下限": lo, "95%CI上限": hi})
    return pd.DataFrame(rows)


def category_ci(d_all):
    """カテゴリ別カート追加→購入率（訪問者単位ブートストラップ）。f05（SQL）の対象カテゴリに合わせる"""
    con = connect()
    c = con.execute("""SELECT visitorid, root_category AS cat, buy::INT AS buy FROM cart_units
                       WHERE seg = 'regular' AND root_category IS NOT NULL""").fetchdf()
    f5 = pd.read_csv(TABLE_DIR / "f05_category_bottleneck.csv")
    cats = list(f5["カテゴリID"].astype(int))
    vid, vidx = np.unique(c.visitorid.values, return_inverse=True)
    n = np.zeros((len(vid), len(cats))); b = np.zeros_like(n)
    for j, k in enumerate(cats):
        m = (c.cat == k).values
        np.add.at(n[:, j], vidx[m], 1); np.add.at(b[:, j], vidx[m], c.buy.values[m])
    p = np.full(len(vid), 1 / len(vid))
    bs = np.empty((B, len(cats)))
    for i in range(B):
        w = rng.multinomial(len(vid), p).astype(float)
        bs[i] = (w @ b) / np.maximum(w @ n, 1)
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    out = f5.copy()
    out["カート追加→購入率_下限"], out["カート追加→購入率_上限"] = lo, hi
    return out


def main():
    d = load()
    seg = segment_table(d)
    seg.to_csv(TABLE_DIR / "f10_segment_ci.csv", index=False, encoding="utf-8-sig")
    overall = d.buy.mean()

    below = seg[seg["95%CI上限"] < overall].copy()
    # 同時にカート追加した商品数・商品ページ閲覧数は、回帰（調整後）でも購入されにくい傾向が確認できた区分（5件以上、閲覧2件以下）に絞って試算する
    # （4件、閲覧3〜9件は調整後のオッズ比の信頼区間が1を含む）
    below = below[~below.set_index(["軸", "区分"]).index.isin([("同時にカート追加した商品数（同一1時間内）", "4件"), ("商品ページ閲覧数（期間中の総数）", "3-9件")])]
    below["追加購入数"] = (overall - below["カート追加→購入率"]) * below["カート数"]
    gap = below.groupby("軸").agg(対象区分=("区分", lambda s: "、".join(s)), 対象カート数=("カート数", "sum"),
                                追加購入数_平均まで改善=("追加購入数", "sum")).reset_index()
    gap["現在の購入数に対する割合"] = gap["追加購入数_平均まで改善"] / d.buy.sum()
    wv = within_visitor(d)
    wv.to_csv(TABLE_DIR / "f15_within_visitor.csv", index=False, encoding="utf-8-sig")
    print(wv.round(3).to_string())
    cat = category_ci(d)
    cat.to_csv(TABLE_DIR / "f16_category_ci.csv", index=False, encoding="utf-8-sig")
    # カテゴリ別: カート追加後の購入率の信頼区間の上限が全体平均を下回るカテゴリを、全体平均まで引き上げた場合
    cb = cat[cat["カート追加→購入率_上限"] < overall].copy()
    cb["追加購入数"] = (overall - cb["カート追加→購入率"]) * cb["カート数"]

    rr = route_robustness(d)
    rr.to_csv(TABLE_DIR / "f13_route_robustness.csv", index=False, encoding="utf-8-sig")
    print(rr.to_string())
    # 「閲覧なしカート追加」は、訪問者の違いを除いた比（訪問者内比較）で試算した値を下限シナリオとして併記する
    r_v = rr.loc[rr["比較方法"] == "訪問者内比較", "購入率比（閲覧後/閲覧なし）"].iloc[0]
    nv = d[~d.viewed_before]
    low = pd.DataFrame([{"軸": "閲覧の有無（訪問者内比較の比で試算）", "対象区分": "閲覧なしでカート追加",
                         "対象カート数": len(nv), "追加購入数_平均まで改善": nv.buy.sum() * (r_v - 1),
                         "現在の購入数に対する割合": nv.buy.sum() * (r_v - 1) / d.buy.sum()}])
    catrow = pd.DataFrame([{"軸": "カテゴリ", "対象区分": "、".join(cb["カテゴリID"].astype(str)), "対象カート数": cb["カート数"].sum(),
                            "追加購入数_平均まで改善": cb["追加購入数"].sum(),
                            "現在の購入数に対する割合": cb["追加購入数"].sum() / d.buy.sum()}])
    gap = pd.concat([gap, low, catrow], ignore_index=True)
    gap.to_csv(TABLE_DIR / "f11_gap_sizing.csv", index=False, encoding="utf-8-sig")
    print(gap.to_string())

    dl = d.dropna(subset=["g_pop"]).copy()
    dl["g_pop"] = pd.Categorical(dl.g_pop, ["50件以上", "10-49件", "3-9件", "1-2件"])
    dl["g_hour"] = pd.Categorical(dl.g_hour, ["15〜21時", "22〜7時", "8〜14時"])
    dl["g_dow"] = pd.Categorical(dl.g_dow, ["月〜木", "金", "土", "日"])
    dl["g_size"] = pd.Categorical(dl.g_size, ["1件", "2件", "3件", "4件", "5件以上"])
    dl["g_route"] = pd.Categorical(dl.g_route, ["閲覧後にカート追加", "閲覧なしでカート追加"])
    m = smf.logit("buy ~ C(g_hour) + C(g_dow) + C(g_size) + C(g_route) + C(g_pop)", data=dl).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(dl.visitorid)[0]})
    ci = m.conf_int()
    lg = pd.DataFrame({"変数": m.params.index, "オッズ比": np.exp(m.params.values),
                       "95%CI下限": np.exp(ci[0].values), "95%CI上限": np.exp(ci[1].values), "p値": m.pvalues.values})
    lg = lg[lg["変数"] != "Intercept"]
    lab = {"g_hour": "時間帯（UTC）", "g_dow": "曜日", "g_size": "同時にカート追加した商品数", "g_route": "閲覧の有無",
           "g_pop": "商品ページ閲覧数"}
    for k, v in lab.items():
        lg["変数"] = lg["変数"].str.replace(f"C({k})[T.", v + "：", regex=False).str.rstrip("]")
    lg.to_csv(TABLE_DIR / "f12_logit.csv", index=False, encoding="utf-8-sig")
    print(lg.round(3).to_string())


if __name__ == "__main__":
    main()
