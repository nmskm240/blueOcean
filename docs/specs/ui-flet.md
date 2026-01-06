# UI (Flet)

## 画面構成

- **Home** (`/`)
  - `RootLayout` のコンテンツに `Home` テキストを表示
- **Bots** (`/bots`)
  - `Backtest` 開始用のメニューを提供
  - 画面上のリスト/詳細は今後拡張前提
- **Accounts** (`/accounts`)
  - 登録済みアカウント一覧を表示
  - 「登録」ボタンから認証情報を追加
- **Strategy** (`/strategies`)
  - `Strategies` テキストを表示 (拡張前提)

## 共通レイアウト

- `RootLayout` が NavigationRail を提供
- `RootAppBar` に「価格データ取得」ボタンを配置

## ダイアログ

### AccountCredentialDialog
- 取引所APIの認証情報を入力
- 入力項目: exchange / label / api key / api secret / is sandbox
- `RegistAccountUsecase` を呼び出して保存

### OhlcvFetchDialog
- 登録済みアカウントから取引所を選択
- シンボルを手動入力
- `FetchOhlcvUsecase` を呼び出して Parquet 保存

### BacktestDialog
- 取引所/シンボル、期間、時間足、戦略を指定
- 戦略パラメータは `StrategyParamField` により動的生成
- `LaunchBotUsecase` を呼び出してバックテストを実行

## 入力コンポーネント

- `TimeframeDropdown` : `Timeframe` を UI で選択
- `ExchangeDropdown` : ccxt 対応取引所の一覧
- `SymbolDropdown` : 取引ペアの一覧
- `AccountDropdown` : 登録済みアカウント
- `StrategyDropdown` : `StrategyRegistry` 登録戦略
