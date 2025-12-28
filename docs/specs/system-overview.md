# 全体構成

## エントリーポイント

- `app.py` がアプリの起動スクリプトです。
- `blueOcean.presentation.flet.run` を起動し、Flet UI を `0.0.0.0` で立ち上げます。

## レイヤ構成 (DDDベース)

- `blueOcean.presentation` : UI (Flet / Jupyter)
- `blueOcean.application` : ユースケース、DI、ワーカー、サービス
- `blueOcean.domain` : ボット・アカウント・OHLCVなどのドメインモデル
- `blueOcean.infra` : DB、ストア、フェッチャー、アクセサ
- `blueOcean.shared` : レジストリや共通コンポーネント

## DI構成

- `AppModule` が SQLite と DuckDB (履歴データ) を初期化し、主要リポジトリ/ファクトリをバインドします。
- 実行モードごとに `BacktestRuntimeModule` / `LiveTradeRuntimeModule` が Cerebro を組み立てます。
- UI 側は `AppScope` から必要な Notifier を解決し、ユースケースを呼び出します。

## 実行モード

- **バックテスト**: `BacktestContext` を使って `BacktestWorker` を起動
- **ライブ**: `LiveContext` を使って `LiveTradeWorker` を起動

## 主要モジュール

| 役割 | モジュール | 概要 |
| --- | --- | --- |
| UI | `blueOcean.presentation.flet` | 画面/ダイアログを定義し、ユーザー操作を Notifier に委譲 |
| ユースケース | `blueOcean.application.usecases` | アカウント登録、OHLCV取得、ボット起動の入口 |
| ドメイン | `blueOcean.domain` | `Bot` / `Account` / `Ohlcv` のライフサイクル管理 |
| インフラ | `blueOcean.infra` | SQLite、Parquet、ccxt を用いた外部アクセス |
