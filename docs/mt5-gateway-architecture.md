# MT5 Gateway 調査・基本設計

Status: Proposed
Date: 2026-07-11

## 1. 結論

BlueOcean は次の境界で構成する。

```text
Windows host
  MT5 terminal (1 account)
        ^ MetaTrader5 Python API
        |
  MT5 Gateway worker (1 process per terminal/account)
        | Redis Streams + local SQLite outbox/checkpoint
        v
Docker Desktop
  Redis <-> Strategy workers / Backtrader adapter
              |
              v
         BlueOcean API / DB
```

- MT5 公式 Python API を利用するプロセスは Windows ホストに限定する。
- Docker コンテナは MT5 のパスや資格情報を持たず、イベント契約だけを知る。
- 確定足は Python 側のポーリングで検知し、履歴差分で欠損を補完する。
- HTTP は設定・状態照会用の control plane、Redis Streams はイベント配送用の data plane とする。
- 配送保証は exactly-once ではなく at-least-once とし、producer/consumer の両側で冪等にする。
- 注文機能は価格配信の安定後に別フェーズで追加する。

## 2. 調査結果

### 2.1 既存実装

現在のリポジトリには以下がある。

- FastAPI/Jinja による MT5 アカウント CRUD
- SQLite/Peewee によるアカウント永続化
- Fernet による MT5 パスワード暗号化
- `MT5Client`: 公式 `MetaTrader5` モジュールの薄いラッパー
- `MT5Store`: Backtrader feed/broker 間の接続所有
- `MT5Data`: 履歴取得後、確定足を1秒周期でポーリング
- `MT5Broker`: Market/Limit/Stop の基本的な `order_send` 変換
- Linux devcontainer と Redis サービス。ただし現行アプリは Redis を使用していない

既存テストは、`BLUEOCEAN_SECRET_KEY` を与えると 28 件すべて成功する。一方、MT5 adapter の単体テストと実機統合テストはない。

### 2.2 現在の主要な不足

1. `MT5Data` はライブ時に `start_pos=1, count=1` だけを取得するため、停止や遅延が1期間を超えると中間足を失う。
2. 保存アカウントから資格情報を復号して Gateway worker を起動する application service がない。
3. Docker から利用できる Gateway、イベントbus、checkpoint、再接続、health がない。
4. `MT5Broker` は pending order の後続約定、部分約定、外部キャンセル、再起動後の照合を行わない。
5. ヘッジ口座の決済で `position` ticket を指定しないため、反対建玉を新規作成する可能性がある。
6. API はアカウント CRUD のみで、現状のまま外部公開すると認証なしで口座設定へ到達できる。

### 2.3 技術上の制約

MT5 Python API の `initialize()` は terminal executable のローカルパスを受け取って terminal と接続する。ネットワーク上の MT5 を指定する host/port 型 API ではない。このため Linux コンテナからホスト MT5 へ直接接続する設計は採用しない。

Docker Desktop から Windows ホストの TCP service へは `host.docker.internal` で到達できる。ただし今回の第一案では Gateway が Docker の Redis 公開ポートへ外向き接続するため、Gateway HTTP port を LAN に公開しなくても価格配信できる。

Redis Streams は append-only log、consumer group、明示 ACK、pending message の reclaim を提供する。停止後の再開と負荷分散には適するが、アプリケーション処理を含めた exactly-once は保証しない。

## 3. 設計原則

1. **MT5境界をWindowsに閉じ込める**: `MetaTrader5` import は Gateway/MT5 adapter だけに許可する。
2. **1 terminal = 1 account = 1 worker process**: process-global な接続状態の干渉と障害半径を避ける。
3. **検知はポーリング、正しさは履歴照合**: 毎回複数本を読み、checkpoint より新しい足を昇順処理する。
4. **永続化してから配信**: checkpoint と outbox を同一 DB transaction で更新する。
5. **価格と注文を分離**: worker、stream、権限、状態モデルを共有しない。
6. **障害時は注文を fail-closed**: 状態が不明な注文を推測で再送しない。
7. **既存公開APIを当面維持**: `blueOcean.metatrader` とローカル Backtrader example は移行完了まで残す。

## 4. コンポーネント

### 4.1 Windows Gateway worker

口座ごとに独立プロセスとして起動する。

責務:

- 暗号化資格情報の取得と worker 内での復号
- terminal への接続と直列化された MT5 API 呼び出し
- subscription ごとの確定足取得
- 欠損補完、checkpoint、outbox
- Redis Streams への publish
- 再接続、heartbeat、readiness
- Phase 2 以降の注文実行と約定照合

Gateway worker に戦略判断やインジケーター計算は置かない。

### 4.2 Gateway supervisor

口座 worker の起動・停止・監視を担当する。FastAPI request の中で長時間 worker を直接実行せず、subprocess lifecycle を管理する。

同一プロセスに複数の MT5 account connection を同居させる案は、公式モジュールの接続所有を実機検証するまで採用しない。

### 4.3 Redis Streams

Phase 1:

- `mt5.market.<account_id>`: 確定足
- `mt5.gateway.status`: heartbeat/status

Phase 2:

- `mt5.commands.<account_id>`: 注文 command
- `mt5.results.<account_id>`: 注文 result/event

Docker Compose の Redis は `127.0.0.1:6379:6379` のように localhost のみに公開する。Gateway は `localhost:6379`、コンテナは `redis:6379` を使用する。

### 4.4 Docker strategy worker

- consumer group で足を読む。
- event 処理と DB commit が成功した後だけ `XACK` する。
- `event_id` に unique constraint を置き、再配送を無害化する。
- MT5 path/password や公式 MT5 module を持たない。

#### 現在の Strategy/Run MVP

Redis market stream の実装に先行して、Strategy の登録・実行ライフサイクルを検証するローカル MVP を実装済みとする。このMVPは最終形の Docker strategy worker ではなく、Backtrader実行境界とSupervisorの状態管理を固めるための中間段階である。

責務は次のように分離する。

- `StrategyConfig`: DBへ永続化する稼働設定。戦略実装キー、任意の口座、シンボル、時間足、価格データsource、execution backend、パラメータを保持する。
- `bt.Strategy`派生クラス: 売買ロジックの実装。DBエンティティを兼ねない。
- `StrategyDefinition`: 実装キー、表示名、Strategyクラス、型付きパラメータ定義を関連付ける。
- `StrategyRun`: 1回の実行履歴。状態、PID、heartbeat、開始・終了時刻、エラーを保持する。
- `StrategySupervisor`: 1 Run = 1 child processとして起動・停止・監視する。
- `StrategyService`: Web/API共通のapplication boundary。ルートからRepositoryとSupervisorの直接操作を排除する。
- Backtrader Runner: child process内で`Cerebro`、Data Feed、Strategyを組み立てて`next()`を実行する。
- `MarketDataSource`: Backtrader Data Feed生成port。`synthetic`、`yfinance`、将来のRedis/MT5確定足を差し替える。
- `ExecutionBackend`: broker、初期資金、commission、analyzer、実行結果の抽出を差し替える。

```text
StrategyConfig
      | definition_key + parameters
      v
StrategyDefinition registry ---> bt.Strategy subclass
      |
      v
StrategySupervisor ---> child process ---> Cerebro + Data Feed + Strategy
      |
      v
StrategyRun (SQLite heartbeat/status/history)
```

現在は次の組み合わせを許可する。

- `synthetic + paper`: ライフサイクル、heartbeat、継続実行の確認。
- `yfinance + backtest`: Yahoo Finance履歴をPandasDataへ変換し、Backtrader標準brokerで有限バックテストを実行。

yfinance adapterはBlueOcean側のFX表記`EURUSD`をYahoo Finance ticker`EURUSD=X`へ変換する。株式`AAPL`や暗号資産`BTC-USD`はそのまま使用する。

対応しないsource/backendの組み合わせはドメイン検証で拒否する。demo/live backendは注文Gateway完成までfail-closedとする。次段階でRedis確定足sourceを追加するが、Strategyクラスは変更しない。

バックテストRunは`initial_cash`、`final_value`、`return_pct`、`trades`をresultとしてSQLiteへ保存する。yfinance利用時はMT5アカウントを必須としない。

戦略追加は登録デコレーターを利用する。1つの`bt.Strategy`派生クラスを追加すると、Webフォーム、API定義、パラメータ検証、Runnerのクラス解決へ同じRegistryが反映される。

Run状態は次を使用する。

```text
starting -> running -> stopping -> stopped
             |
             +-----------> error
application restart -----> lost
```

- `starting`: child process生成後、Runner準備中。
- `running`: Cerebro実行開始済み。Data Feedからheartbeatを更新する。
- `stopped`: stop eventを受けて正常終了。
- `error`: Strategy初期化、Runner、processで回復不能な例外が発生。
- `lost`: アプリ再起動時にDB上でactiveだったが、所有processを復元できないRun。
- 同じStrategyConfigのactive Runは1つに限定する。
- heartbeatとRun履歴はSQLiteを正本とし、Webプロセスのメモリだけに依存しない。

### 4.5 Control API

初期段階では Windows Gateway のローカル運用・診断用とする。

```text
GET  /health/live
GET  /health/ready
GET  /v1/accounts/{account_id}/status
POST /v1/accounts/{account_id}/start
POST /v1/accounts/{account_id}/stop
PUT  /v1/accounts/{account_id}/subscriptions/{symbol}/{timeframe}
DELETE /v1/accounts/{account_id}/subscriptions/{symbol}/{timeframe}
GET  /v1/accounts/{account_id}/bars?symbol=&timeframe=&from=
```

Docker から HTTP を呼ぶ必要が出た場合だけ `host.docker.internal` を使用する。bind、Windows Firewall、API key/HMAC、request ID、timeout を同時に導入し、無認証で LAN に公開しない。

## 5. 推奨ディレクトリ

既存ファイルをすぐ移動せず、次を追加する。

```text
blueOcean/
  market_data/
    models.py          # Bar, BarId, Symbol, Timeframe
    ports.py           # BarSource, Publisher, CheckpointRepository
    services.py        # completed-bar reconciliation
  messaging/
    schemas.py         # versioned wire DTO
    redis_streams.py   # publisher/consumer adapter
  gateway/
    app.py             # Windows Gateway composition root
    settings.py
    account_factory.py # Account -> decrypted MT5Client
    session.py         # connection/reconnect/health/API lock
    bars.py             # subscriptions and BarPoller
    repositories.py    # checkpoint/outbox/subscription
    supervisor.py
    routes.py
    orders.py           # Phase 2
  execution/
    models.py           # Phase 2
    ports.py            # Phase 2
  strategy/
    models.py          # StrategyConfig, StrategyRun
    definitions.py     # registry primitives and typed parameter definitions
    implementations.py # bt.Strategy subclasses
    registry.py        # loaded built-in strategy registry
    runner.py          # Cerebro composition and current paper feed
    ports.py           # MarketDataSource, ExecutionBackend
    adapters.py        # synthetic/yfinance data and paper/backtest backend
    events.py          # typed RunnerEvent including result
    supervisor.py      # child process lifecycle
    repositories.py
    services.py        # shared application boundary for Web/API
    dependencies.py    # FastAPI dependency composition
    schemas.py
    migrations.py
    routes_api.py
    routes_pages.py
    backtrader_remote.py # Phase 4 Redis-backed feed
```

`MT5Store` は Backtrader の参照カウント接続用なので Gateway の接続所有には使わず、`MT5Client` のみ再利用する。`MT5Broker` も同期的な Backtrader Order と密結合しているため注文 Gateway の中核にはしない。

## 6. 確定足のデータ設計

### 6.1 イベント契約 v1

```json
{
  "schema_version": 1,
  "event_id": "bar:account-1:EURUSD:M5:1783692000",
  "event_type": "bar.closed",
  "occurred_at": "2026-07-11T00:05:01Z",
  "account_id": "account-1",
  "symbol": "EURUSD",
  "timeframe": "M5",
  "open_time": 1783692000,
  "open": "1.17210",
  "high": "1.17280",
  "low": "1.17190",
  "close": "1.17250",
  "tick_volume": 834,
  "spread": 12,
  "real_volume": 0,
  "source": "mt5"
}
```

- identity は account/symbol/timeframe/open_time。
- 時刻は UTC epoch seconds、表示用時刻は UTC ISO 8601。
- 価格は wire 上で decimal string とし、binary float の丸め差を避ける。
- event schema は additive change を基本とし、破壊的変更は stream/version を上げる。

### 6.2 Poll algorithm

```text
rates = copy_rates_from_pos(symbol, timeframe, start=1, count=lookback)
rates = open_time ascending

for bar in rates:
    if bar.open_time > checkpoint.last_open_time:
        transaction:
            insert outbox(event_id unique, payload)
            update checkpoint(last_open_time)

outbox dispatcher:
    XADD stream payload
    mark outbox published
```

- position 0 の形成中足は配信しない。
- 通常 `lookback=10` で取得する。
- checkpoint が lookback より古い場合は時刻範囲 API で checkpoint 以降を backfill する。
- 初回 subscription は `bootstrap_mode=latest` を既定とする。明示時のみ過去 N 本を backfill する。
- publish 後、outbox 更新前に停止すると重複するが、event_id で無害化する。
- MT5 が `None`/exception を返した場合は checkpoint を進めない。

## 7. 接続・復旧設計

### 7.1 Session state

```text
STOPPED -> CONNECTING -> READY
                    |      |
                    v      v
                  DEGRADED -> RECONNECTING -> READY
```

- 失敗時は exponential backoff + jitter。
- reconnect 後は必ず checkpoint 以降を backfill してから LIVE に戻す。
- 単一 worker 内の MT5 呼び出しは queue/lock で直列化する。
- shutdown は新規処理停止、outbox/checkpoint flush、`mt5.shutdown()` の順にする。

### 7.2 Health model

Liveness は event loop/process が動作していること、readiness は以下を満たすこととする。

- Redis に接続できる
- MT5 initialize/account_info が成功
- terminal/account identity が設定と一致
- market-data の最終 poll が閾値内
- 注文 readiness の場合は trade_allowed も true

heartbeat fields:

```text
gateway_version, account_id, terminal_build, mt5_connected,
trade_allowed, redis_connected, last_poll_at, last_closed_bar_at,
outbox_depth, reconnect_count, last_error_code
```

市場休場中は「新しい足がない」ことを接続障害と判定しない。poll 成功時刻と最終足時刻を分離する。

## 8. 注文設計（Phase 2）

### 8.1 原則

- `client_order_id` を account 内で unique にする。
- 同一 ID・同一 payload の再送は保存済み結果を返す。
- 同一 ID・異なる payload は conflict とする。
- DB に command ledger を保存してから MT5 へ送る。
- `SUBMITTING` 中の timeout は `UNKNOWN` とし、注文履歴・約定履歴を照合するまで再送しない。
- `order_check`、volume/tick/digits/filling validation を通してから `order_send` する。
- hedging close は `position_ticket` 必須とし、MT5 request の `position` に設定する。
- strategy/magic ごとにポジションを分離し、symbol 全体を合算しない。

### 8.2 状態遷移

```text
RECEIVED -> VALIDATING -> READY -> SUBMITTING
                                     |-- REJECTED
                                     |-- UNKNOWN -> RECONCILING
                                     `-- PLACED -> PARTIALLY_FILLED -> FILLED
                                             |             |
                                             `-> CANCEL_REQUESTED -> CANCELED
                                             `-> EXPIRED
```

HTTP/stream の `accepted` は MT5 受付完了を意味しない。最終状態は result stream または status projection で返す。

### 8.3 Safety controls

- demo account allowlist から開始
- symbol、volume、注文種類の allowlist/limit
- 日次損失上限
- command の `expires_at`
- manual kill switch
- MT5/Redis/ledger が不整合なら新規注文停止
- command、retcode、order/deal ticket の監査ログ
- password/token は全ログから redact

## 9. 永続データ

Phase 1 で追加する。

```text
gateway_subscriptions
  account_id, symbol, timeframe, poll_ms, lookback,
  bootstrap_mode, enabled, UNIQUE(account_id, symbol, timeframe)

bar_checkpoints
  account_id, symbol, timeframe, last_open_time, updated_at,
  UNIQUE(account_id, symbol, timeframe)

outbox_events
  id, event_id UNIQUE, event_type, stream, payload,
  created_at, published_at, attempts, last_error
```

Phase 2 で `order_commands`, `order_events`, `order_projection` を追加する。本番移行前に `create_tables` だけに依存せず migration mechanism を導入する。

Redis は AOF と persistent volume を使用する。ただし Redis を確定足や注文監査の唯一の正本にはしない。

## 10. セキュリティ

- MT5 資格情報を Docker や stream に渡さない。
- 復号鍵は Gateway worker が動く Windows 側だけに置く。
- 長期的には Windows Credential Manager/DPAPI を検討する。
- Redis は localhost publish、ACL user 分離、永続 volume、可能なら TLS。
- market publisher、strategy consumer、order commander で Redis ACL を分ける。
- control API を公開する場合は HMAC/API key、Firewall、rate limit、audit log を必須にする。

既存の Web API と Gateway control API を同一権限で公開しない。

## 11. Observability

最低限、以下を structured log/metrics に出す。

- `account_id`, `symbol`, `timeframe`, `event_id`, `client_order_id`
- poll latency、bar lag、last successful poll
- reconnect total、consecutive failure count
- outbox depth/publish retry
- Redis pending entries/oldest pending age
- command latency、expired commands、unknown order count
- MT5 retcode 別件数

主な alert:

- heartbeat stale
- poll failure の連続
- outbox/pending の増加
- 市場開場中の bar lag
- 注文 `UNKNOWN`
- MT5 retcode 異常率

## 12. テスト戦略

### Unit（fake MT5 module）

- 形成中足を除外する
- 同一足を再取得しても重複保存しない
- 3本以上進んだ後に全足を昇順回復する
- 長期停止時に range backfill する
- None/exception 後に checkpoint を維持して reconnect する
- out-of-order rates を整列する
- outbox publish 前後の crash を重複無害化する
- volume step/digits/filling/hedging close を検証する
- order timeout を UNKNOWN として照合し、二重発注しない

### Integration

- temp SQLite + InMemory publisher
- 実 Redis の XADD/XREADGROUP/XACK/reclaim
- Gateway/Redis/consumer の個別 kill/restart
- Windows + MT5 demo terminal の接続/再起動/注文照合
- event schema contract snapshot
- ログに秘密情報が混入しないこと

### 受入基準

1. Gateway を30分停止しても、再起動後に確定足欠損0、DB重複0。
2. 同じ command を100回再配送しても MT5 発注は1回。
3. Redis を60秒停止すると注文は fail-closed になり、期限切れ command を復旧後に発注しない。
4. MT5 terminal 再起動後に自動で READY へ復帰する。
5. Docker 再作成後も Redis AOF、DB、checkpoint、ledger が維持される。
6. local Backtrader feed と remote feed が同一期間で同じ確定足列になる。

## 13. 実装ロードマップ

### Current: Strategy/Run lifecycle MVP

- `StrategyConfig`、`StrategyDefinition`、`StrategyRun`を分離
- decorator-based Strategy registry
- Backtrader `Cerebro`をchild processで実行
- Synthetic paper feedで`next()`、heartbeat、stopを検証
- yfinance履歴sourceとBacktrader backtest backend
- backtest resultのRun永続化
- `/strategies`、`/runs` Web UI
- `/api/strategies`、`/api/strategy-definitions`、`/api/runs`
- 起動中Runの二重作成防止と再起動時`lost`補正

完了済み範囲: Backtrader Strategyの生成・継続実行・heartbeat・停止・エラー遷移。未完了範囲: MT5確定足、Redis consumer、OrderIntent、Risk Gateway、注文実行。

### Phase 0: Characterization

- `MT5Client`, `MT5Data`, `MT5Broker` の fake-module tests
- 現行の外部 import/API を固定
- 設計 ADR の作成

### Phase 1: Read-only Gateway MVP

- market-data domain/ports
- 1 account / 1 symbol / 1 timeframe
- BarPoller、checkpoint、outbox
- Redis market stream
- heartbeat/status
- Docker consumer と event-id unique constraint

完了条件: 再起動試験で欠損0・重複無害。

### Phase 2: Demo execution

- command/result streams
- command ledger/idempotency
- `order_check` と request normalization
- market order、明示 close、reconciliation
- risk limits と kill switch

完了条件: demo account の故障注入試験で二重発注0。

### Phase 3: Full order lifecycle

- pending/cancel/partial fill/expire
- multi-account supervisor
- metrics/alerts/Windows service 化

### Phase 4: Strategy migration

- Redis-backed Backtrader feed
- local/remote shadow comparison
- 安定後に strategy の MT5 direct dependency を削除

## 14. ADR として確定が必要な項目

実装前に最低限以下を ADR 化する。

1. Windows Gateway + Linux Docker 分離
2. polling + history reconciliation。MQL Socket は tick latency 要件発生まで延期
3. HTTP control plane + Redis Streams data plane
4. at-least-once + idempotent consumer
5. 1 worker process / terminal / account
6. credential ownership と key rotation
7. checkpoint/outbox の正本と保持期間
8. bar close、broker timezone、週末、訂正足、symbol suffix の扱い
9. schema versioning
10. order unknown outcome と reconciliation
11. Backtrader の DELAYED/LIVE semantics
12. SLO と alert threshold

## 15. 今回採用しない案

### Docker から公式 MT5 API へ直接接続

terminal executable path をローカルに必要とするため採用しない。

### MQL EA から Socket push

tick 単位の低遅延が必要になれば有力だが、現段階の確定足用途では再接続、ACK、欠損履歴、EA配布の複雑性が先に増えるため延期する。

### WebSocket だけで確定足配信

切断中の履歴、ACK、consumer recovery を別実装する必要があるため、durable stream の代用にはしない。

### 既存 `MT5Broker` をそのまま注文サービス化

Backtrader の同期 order lifecycle と密結合し、冪等 command、再起動復旧、部分約定照合に向かないため採用しない。

## 16. UML資料

- [`uml/classes.puml`](uml/classes.puml): Account、MT5 worker、StrategyConfig、StrategyDefinition、Backtrader Strategy、Run/Supervisorのクラス関係。
- [`uml/strategy-run-sequence.puml`](uml/strategy-run-sequence.puml): Run開始、Cerebro実行、heartbeat、停止、再起動時lost補正のシーケンス。
- [`uml/components.puml`](uml/components.puml): 現在のローカルpaper MVPと、Redis／Docker／注文Gatewayを含む目標コンポーネント境界。

## 17. 参考資料

- MetaTrader 5 Python integration: <https://www.mql5.com/en/docs/python_metatrader5>
- MetaTrader 5 `initialize`: <https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py>
- Docker Desktop networking: <https://docs.docker.com/desktop/features/networking/networking-how-tos/>
- Redis Streams: <https://redis.io/docs/latest/develop/data-types/streams/>
