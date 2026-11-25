"""図表の作成（output/figures）。数値は output/tables のCSVのみから作る"""
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from common import TABLE_DIR, FIG_DIR

rcParams["font.family"] = "Noto Sans CJK JP"
rcParams["axes.spines.top"] = rcParams["axes.spines.right"] = False
B, O, A, G = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
FIG_DIR.mkdir(parents=True, exist_ok=True)
T = lambda n: pd.read_csv(TABLE_DIR / n)


def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG_DIR / name, dpi=160); plt.close(fig)


# 図1 訪問者単位ファネル
f = T("f01_funnel_overall.csv"); f = f[f["単位"] == "訪問者単位"].sort_values("段階順")
fig, ax = plt.subplots(figsize=(7, 3.6))
ax.barh(f["段階"][::-1], f["件数"][::-1], color=B, height=0.55)
ax.set_xlabel("訪問者数"); ax.set_xlim(0, f["件数"].max() * 1.2)
prev = None
for i, (s, n) in enumerate(zip(f["段階"][::-1], f["件数"][::-1])):
    ax.text(n * 1.08, i, f"{int(n):,}", va="center", fontsize=9)
ax.set_title("訪問者単位のファネル（一般訪問者）", loc="left")
save(fig, "fig1_funnel.png")

# 図2 段階間の所要時間
d = T("f02_lag_distribution.csv").sort_values(["段階間", "並び順"])
fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, (name, g), col in zip(axs, d.groupby("段階間", sort=False), [B, O]):
    ax.bar(g["所要時間"], g["構成比"] * 100, color=col, width=0.6)
    for i, v in enumerate(g["構成比"] * 100): ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_title(name, loc="left"); ax.tick_params(axis="x", labelrotation=35, labelsize=8)
axs[0].set_ylabel("構成比（%）")
save(fig, "fig2_lag.png")

# 図3 セグメント別カート追加→購入率
s = T("f10_segment_ci.csv"); s = s[s["軸"].isin(["閲覧の有無", "時間帯（UTC）", "曜日", "同時にカート追加した商品数（同一1時間内）", "商品ページ閲覧数（期間中の総数）"])]
ORDER = {"閲覧の有無": ["閲覧後にカート追加", "閲覧なしでカート追加"], "時間帯（UTC）": ["15〜21時", "22〜7時", "8〜14時"],
         "曜日": ["月〜木", "金", "土", "日"], "同時にカート追加した商品数（同一1時間内）": ["1件", "2件", "3件", "4件", "5件以上"],
         "商品ページ閲覧数（期間中の総数）": ["50件以上", "10-49件", "3-9件", "1-2件"]}
s = pd.concat([s[(s["軸"] == a) & (s["区分"] == c)] for a, cs in ORDER.items() for c in cs])
s = s.reset_index(drop=True); s["lab"] = s["軸"].str.replace("（同一1時間内）", "") + "：" + s["区分"]
fig, ax = plt.subplots(figsize=(8.5, 7))
y = list(range(len(s)))[::-1]
ax.errorbar(s["カート追加→購入率"] * 100, y, xerr=[(s["カート追加→購入率"] - s["95%CI下限"]) * 100, (s["95%CI上限"] - s["カート追加→購入率"]) * 100],
            fmt="o", color=B, ecolor=G, capsize=2)
ax.axvline(s["全体平均"].iloc[0] * 100, color=O, ls=":", lw=1.2)
ax.set_yticks(y); ax.set_yticklabels(s["lab"], fontsize=8); ax.set_xlabel("カート追加→購入率（%、95%信頼区間）")
ax.set_title("セグメント別のカート追加→購入率（点線は全体平均）", loc="left")
save(fig, "fig3_segments.png")

# 図4 カテゴリ別の閲覧→カート追加率とカート追加→購入率
c = T("f16_category_ci.csv")
fig, ax = plt.subplots(figsize=(7.5, 5))
ax.errorbar(c["閲覧→カート追加率"] * 100, c["カート追加→購入率"] * 100,
            yerr=[(c["カート追加→購入率"] - c["カート追加→購入率_下限"]) * 100, (c["カート追加→購入率_上限"] - c["カート追加→購入率"]) * 100],
            fmt="o", color=B, ecolor=G, capsize=2)
for _, r in c.iterrows():
    ax.annotate(str(int(r["カテゴリID"])), (r["閲覧→カート追加率"] * 100, r["カート追加→購入率"] * 100), fontsize=8, xytext=(6, 4), textcoords="offset points")
ax.set_xlabel("閲覧→カート追加率（%）"); ax.set_ylabel("カート追加→購入率（%、95%信頼区間）")
ax.set_title("カテゴリ別の閲覧→カート追加率とカート追加→購入率", loc="left")
save(fig, "fig4_category.png")

# 図5 週次: 閲覧なしカート追加の割合
w = T("f06_weekly_route_trend.csv")
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(w["週開始日"], w["閲覧なしカート追加の割合"] * 100, color=O, lw=2)
ax.set_xticks(range(0, len(w), 2)); ax.set_xticklabels(w["週開始日"][::2], rotation=45, fontsize=8)
ax.set_ylabel("閲覧なしカート追加の割合（%）"); ax.set_ylim(0, 50)
ax.set_title("カート追加に占める「閲覧なし」の割合（週次）", loc="left")
save(fig, "fig5_weekly_noview.png")

# 図6 在庫状態別の段階別の割合
t = T("s01_stage_by_stock.csv")
t["lab"] = t["商品区分"] + "\n（" + t["起点時点の在庫"] + "）"
fig, axs = plt.subplots(1, 2, figsize=(10, 4))
for ax, col, ttl in zip(axs, ["閲覧→カート追加率", "カート追加→購入率"], ["閲覧→カート追加率", "カート追加→購入率"]):
    ax.bar(t["lab"], t[col] * 100, color=[B if "あり）" in l and "変動" not in l else (A if "あり）" in l else O) for l in t["lab"]], width=0.6)
    for i, v in enumerate(t[col] * 100): ax.text(i, v + 0.05 * max(t[col] * 100), f"{v:.2f}%" if v < 0.1 else f"{v:.1f}%", ha="center", fontsize=8)
    ax.set_title(ttl, loc="left"); ax.tick_params(axis="x", labelsize=7)
axs[0].set_ylabel("割合（%）")
save(fig, "fig6_stage_by_stock.png")

# 図7 比較方法別の率の比（在庫）
e = T("s10_stock_effects.csv"); e = e[e["段階"].isin(["閲覧→カート追加", "カート追加→購入"])].reset_index(drop=True); e["lab"] = e["段階"] + "：" + e["比較方法"]
fig, ax = plt.subplots(figsize=(8, 3.8))
y = list(range(len(e)))[::-1]
ax.errorbar(e["比"], y, xerr=[e["比"] - e["95%CI下限"], e["95%CI上限"] - e["比"]],
            fmt="o", color=B, ecolor=G, capsize=3)
for yi, v in zip(y, e["比"]): ax.text(v, yi + 0.22, f"{v:.2f}倍", ha="center", fontsize=8)
ax.axvline(1, color=G, ls=":"); ax.set_yticks(y); ax.set_yticklabels(e["lab"], fontsize=8)
ax.set_xlabel("購入率（カート追加率）の比：在庫あり ÷ 在庫なし（95%信頼区間）")
ax.set_title("在庫なしの影響の段階別・比較方法別の推定（1より大きいほど在庫なしで低い）", loc="left")
save(fig, "fig7_stock_effects.png")

# 図8 カート追加後の時間: 購入者（購入までの時間）と購入しなかった訪問者（滞在時間）
d8 = T("f08_dwell_after_cart.csv"); d8["時間"] = d8["時間"].str.replace(r"^\d_", "", regex=True)
fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, (name, g), col in zip(axs, d8.groupby("区分", sort=False), [A, O]):
    ax.bar(g["時間"], g["構成比"] * 100, color=col, width=0.6)
    for i, v in enumerate(g["構成比"] * 100): ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_title(name, loc="left", fontsize=10)
axs[0].set_ylabel("構成比（%）")
save(fig, "fig8_dwell_after_cart.png")
print("ok")
