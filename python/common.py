"""共通設定とユーティリティ"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "work" / "portfolio.duckdb"
TABLE_DIR = ROOT / "output" / "tables"
FIG_DIR = ROOT / "output" / "figures"

# 分析パラメータ
PARAMS = {
    "FOLLOW_UP_DAYS": 7,      # 最初の閲覧後の追跡期間（日）
    "HEAVY_THRESHOLD": 100,   # 高頻度アクセス訪問者とみなす期間中のイベント数
}


def connect() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def render_sql(path: Path) -> str:
    """SQLファイル内の ${PARAM} をパラメータ値に置換する"""
    sql = path.read_text(encoding="utf-8")
    for k, v in PARAMS.items():
        sql = sql.replace("${" + k + "}", str(v))
    return sql
