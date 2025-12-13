## プロジェクト概要

金融商品の自動売買とその分析ツールです

## 技術スタック

使用しているライブラリは `requirements.txt`を参照

### インフラ

- sqlite
- duckdb

### UI

- streamlit
- jupyter
- matplotlib
- plotly

### 自動売買処理

- backtrader

### 取引所連携

- ccxt

## アーキテクチャ

DDDをベースに開発します

### フォルダ構成

```
/
├─ blueOcean/
│  ├─ application/
│  │  ├─ decorators
│  │  ├─ services
│  │  ├─ analyzers
│  │  ├─ broker
│  │  ├─ di
│  │  ├─ dto
│  │  ├─ feed
│  │  ├─ store
│  │  ├─ usecases
│  │  └─ workers
│  ├─ core/
│  │  └─ strategies
│  ├─ domain/
│  │  ├─ account
│  │  └─ ohlcv
│  ├─ infra/
│  │  ├─ database/
│  │  │  ├─ entities
│  │  │  └─ repositories
│  │  ├─ fetchers
│  │  ├─ logging
│  │  └─ stores
│  └─ presentation/
│     ├─ jupyter/
│     │  └─ preprocessor
│     └─ streamlit/
│        ├─ contents
│        └─ widgets
├─ data/
│  ├─ exchange_name/
│  │  ├─ symbol_name_0/
│  │  │  ├─ 2025-1.parquet
│  │  │  └─ 2025-2.parquet
│  │  └─ symbol_name_1
│  └─ blueOcean.sqlite3
├─ notebooks/
│  └─ strategy_idea.ipynb
├─ out/
│  └─ <unique_id>/
│     ├─ analyze.csv
│     └─ tire_sheet.html
└─ main.py
```

### 設計思想

- 戦略の作成から実行までをbacktraderに一任する
    - backtraderのfeed, strategy, broker, analyzerを使い、バックテストと本番稼働で同じコードを使えるようにする
    - ccxtを使った実取引所との連携も `CcxtBroker`, `CcxtSpotStore`などを使用してbacktraderのロジックに乗って動作するようにする
- バックテストと本番稼働の差をなくす
    - backtraderによるエンジンの統一を徹底する
    - `BacktestWorker`, `RealTradeWorker`のように、backtraderの稼働は別プロセスで行う
- jupyterとstreamlitの繋ぎ込みを行う
    - jupyterで出力したグラフは`MarkdownInlineFigurePreprocessor`を使用してmarkdownに直接埋め込み、`strategy_page`デコレータを通してStreamlitページとして表示できるようにする
- Streamlitを管理ツール兼プレイグラウンドとして扱う
    - 本番稼働のダッシュボード、バックテストの履歴確認、戦略のアイデア帳として作成する

## コーディング規則

- コミットメッセージは Conventional Commits に従う
  - コミット内容部に関しては日本語で記述してください
- ブランチ名は Conventional Branch に従う
- コミットメッセージは対応内容をシンプルに1行で表現する


