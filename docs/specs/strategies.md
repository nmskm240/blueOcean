# 戦略とレジストリ

## 戦略の登録

- `StrategyRegistry` が戦略クラスを登録/参照する中心機構です。
- `StrategyRegistry.register()` を使って戦略クラスを登録します。
- `StrategyRegistry.params_of()` でパラメータ一覧を抽出でき、UI 側に反映されます。

## パラメータ抽出

- `StrategyRegistry` は `params` 属性を参照して、キーと初期値を抽出します。
- `StrategyParamField` は抽出されたパラメータをフォーム化し、バックテストの入力に利用します。

## サンプル戦略

### TestRandomOrder

- ランダムに売買を行うデモ戦略
- パラメータ
  - `order_chance` : 発注確率
  - `max_size` : 1回の発注量
  - `cooldown` : 連続発注を抑制するクールダウン

## UI連携

- `StrategyDropdown` が `StrategyRegistry` の内容を一覧表示
- `BacktestDialog` で戦略選択とパラメータ入力が可能
