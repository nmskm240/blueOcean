# データ/ストレージ

## SQLite (アプリDB)

- `data/blueOcean.sqlite3` に保存
- Peewee を使用して `AccountEntity` / `BotEntity` / `BotContextEntity` を管理
- `AccountRepository` / `BotRepository` が CRUD を担当

## OHLCV履歴データ (Parquet + DuckDB)

- `OhlcvRepository` が Parquet を管理
- 保存先: `data/<exchange>/<symbol>/YYYY-MM.parquet`
- `duckdb` を使用し、時系列の集約・抽出を行う

## 実行結果

- `LocalBotRuntimeDirectoryAccessor` が `out/<bot_id>` を生成
- `StreamingAnalyzer` が `metrics.csv` を出力
- 実行終了後に `quantstats_report.html` を生成

## データ取得

- `CcxtOhlcvFetcher` が ccxt を用いて OHLCV を取得
- 取得単位は 1分足 (`TIMEFRAME = "1m"`) を基準にバッチ取得
