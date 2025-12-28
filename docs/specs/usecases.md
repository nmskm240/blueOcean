# 主要ユースケース

## 1. アカウント登録

### UI
- `AccountPage` から「登録」ボタンを押下
- `AccountCredentialDialog` が表示される

### 処理フロー
1. `AccountCredentialDialogNotifier` が入力値を保持
2. `RegistAccountUsecase.execute` が `AccountRepository.save` を呼び出し
3. SQLite (`data/blueOcean.sqlite3`) にアカウント情報を保存
4. `AccountPageNotifier.update` で一覧を更新

## 2. OHLCVデータ取得

### UI
- AppBar の「価格データ取得」ボタンで `OhlcvFetchDialog` を表示
- 取引所アカウントとシンボルを選択して保存

### 処理フロー
1. `OhlcvFetchDialogNotifier.submit` が `FetchOhlcvUsecase.execute` を呼び出し
2. `CcxtOhlcvFetcher` で OHLCV を取得
3. `OhlcvRepository.save` が Parquet を `data/<exchange>/<symbol>/YYYY-MM.parquet` に保存

## 3. バックテスト起動

### UI
- `BotTopPage` の「Backtest」メニューから `BacktestDialog` を開く
- 取引所/シンボル、期間、時間足、戦略パラメータを指定

### 処理フロー
1. `BacktestDialogNotifier.on_request_backtest` が `LaunchBotUsecase.execute` を呼び出し
2. `BotExecutionService.start` が `BacktestWorker` を起動
3. `BacktestRuntimeModule` が `LocalDataFeed` からデータを読み込み、Cerebro を実行
4. 実行結果は `out/<bot_id>/metrics.csv` と `quantstats_report.html` に出力

## 4. ライブボット起動 (準備段階)

- `BotTopPage` の「Live bot」メニューは UI 上に存在しますが、現時点では `on_click` が未設定です。
- ライブ実行の基盤 (`LiveTradeWorker` / `LiveTradeRuntimeModule`) は実装済みで、`LiveContext` を受け取れる構成です。
