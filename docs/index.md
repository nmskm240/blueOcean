# blueOcean 仕様書

このドキュメントは、現行のスクリプト構成をもとに **blueOcean** の仕様を整理したものです。
FletベースのUIから、アカウント登録、OHLCVデータ取得、バックテストの起動などの操作ができる構成になっています。

## ドキュメント範囲

- UI: `blueOcean.presentation.flet` を中心にした画面・ダイアログ仕様
- アプリケーション層: `blueOcean.application` のユースケースとDI構成
- ドメイン層: `blueOcean.domain` の主要モデル
- インフラ層: SQLite/Parquetへの保存、外部取引所連携

## 参照先

- 詳細構成は [全体構成](specs/system-overview.md) を参照してください。
- 操作フローは [主要ユースケース](specs/usecases.md) を参照してください。
