#!/bin/sh
# 全処理の実行（リポジトリのルートで実行。data/ に元データ4ファイルを配置しておくこと）
set -e
python python/run_pipeline.py      # SQL: テーブル構築 + 集計結果の出力
python python/funnel_stats.py      # セグメント差の統計確認・改善余地の試算
python python/stock_effects.py     # 在庫状態が各段階に与える影響
python python/sensitivity.py       # 感度分析
python python/make_figures.py      # 図表
