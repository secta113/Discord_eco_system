# Changelog

All notable changes to this project will be documented in this file.

## [v2.6] - 2026-05-06
### Improved
- **特性ロジックのクラスベース化 (`traits/`)**: 特性（Traits）ごとに独立したクラスを定義。寿命・病気率・戦闘ボーナスなどの計算を各特性クラスにカプセル化し、`TraitRegistry` による統合管理を実現。
- **遺伝子座マッピングの正確な反映**: ドキュメント仕様に基づき、`anti_taboo` を `potential` へ、`glass_blade` を `body` へ再配置。新規カテゴリ `growth`（無限、捕食）を正式に定義。
- **禁忌ペナルティの整合性確保**: 赤の禁忌 (`+0.15`)・青の禁忌 (`+0.10`) の病気率ペナルティを特性クラス側で保証し、他の健康特性による減衰を防ぐ設計に変更。
- **遺伝判定アルゴリズムの堅牢化**: `MendelEngine.resolve_traits` においてアレルと表現型名の混同を防止するフィルタリングを強化。

### Fixed
- **究極の禁忌（禁断）の不妊優先**: `antinomy`（背反）による不妊解除よりも、`the_forbidden`（禁断）による不妊設定を優先するように修正。
- **遺伝時アレル消失バグ**: `MendelEngine.crossover` において、突然変異アレルを継承しない場合に汎用アレルが消失する問題を修正。

## [v2.5] - 2026-05-05
### Improved
- **UI ファイルの一元化 (`logic/dobumon/ui/`)**: 3箇所に分散していた Dobumon の View 群（`dob_views/`・`dob_shop/dob_shop_view.py`・`dob_battle/wild/wild_views.py`）を `logic/dobumon/ui/` に統合。`dob_views/` ディレクトリを廃止。
- **ゲーム UI のサブディレクトリ化**: `blackjack/`・`chinchiro/`・`poker/` の各 View ファイルをそれぞれ `ui/` サブパッケージに移動。ゲームロジックと UI の責務を明確に分離。
- **`DobumonFormatter` のレイヤー移動**: Embed 生成ロジック `DobumonFormatter` を `dob_views/` から `logic/dobumon/core/dob_formatter.py` に移動し、ロジック層として正しい位置に配置。
- **Match パッケージの整理**: `logic/match_service.py` と `logic/match_view.py` を `logic/match/` パッケージに統合。サービスと UI を `logic/match/match_service.py` および `logic/match/ui/match_view.py` として整理。
- **`starter.py` の責務移動**: ゲームフロー制御ロジック `execute_game_start()` を `core/ui/starter.py` から `managers/starter.py` に移動。`core/ui/` は純粋な基底 View（`view_base.py`）のみを保持。

## [v2.4] - 2026-05-05
### Added
- **数字フォーマット処理の共通化 (`formatters.py`)**: プロジェクト全体で一貫した数値表示（カンマ区切り、単位付与）を行うための共通ユーティリティを新設。
- **拡張フォーマット機能**: `f_pts` 関数に `signed`（符号付き表示）および `bold`（太字装飾）オプションを追加し、UIロジックの簡素化を実現。
- **フォーマッターの単体テスト**: 新設したフォーマット関数の正常動作を検証するためのユニットテストを追加。

### Improved
- **UI表示の堅牢化**: 各種 View や Cog における手動の数値操作（文字列連結や手動カンマ挿入）を共通関数に置換。
- **管理コマンドの視認性向上**: `/dd-mod logs` や `/dd-mod winner` などの管理用出力における数値表示を最適化。
- **ドブモン市場・トレーニングUIの改善**: 売却価格や必要費用の表示に共通フォーマッターを適用し、表記揺れを解消。

## [v2.3] - 2026-05-04
### Added
- **突然変異エンジン (`MutationEngine`) の新設**: 突然変異の発生と遺伝子座の固定（ホモ接合化）を一元管理するエンジンを導入。
- **遺伝システムの統合と洗練**: `GeneticFixer` を `MutationEngine` に統合。強力な変異（特異点等）が発生した際の自動固定をサポート。
- **データ整合性スクリプト**: 既存個体の遺伝子座マッピングを修正し、最新の仕様に適合させるマイグレーションスクリプトを提供。
- **カスタム例外クラス (`DobumonGeneticsError`)**: 遺伝システム専用のエラーハンドリングを追加し、堅牢性を向上。

### Fixed
- **遺伝子座マッピングの不整合修正**: `blue_blood`（青血）と `crystalized`（結晶化）の遺伝子座がドキュメントの定義と逆になっていた問題を修正。
- **強制変異の配置バグ修正**: 購入時などの強制変異が常に `growth` 遺伝子座に配置されていた問題を修正し、各変異に応じた正しい遺伝子座に割り当てるように改善。

## [v2.2] - 2026-05-01
### Added
- **専門サービスへの分解**: `DobumonService` を各機能（育成、戦闘、ショップ、遺伝）ごとの専門サービスに分解し、コードの保守性と拡張性を大幅に向上。
- **アセットマネジメントの最適化**: `CardAssetManager` によるトランプ画像の動的合成（Dynamic Synthesis）を導入。52枚の個別画像を読み込む代わりにパーツから生成することで、メモリ消費を劇的に削減。
- **高度な遺伝アルゴリズム**: 「Anti-Taboo」と「Singularity」の優先順位（Antinomy > Singularity > Anti-Taboo）を確立。遺伝の安定性と希少性を両立。
- **ショップ・エコシステム**: 「エリート・シンジケート」限定の変異ボーナスなど、ショップごとの特色あるロジックを実装。
- **ログ集約と専用ロガーの導入**: `DobumonLogger` クラスを新設し、個体のスペック（遺伝情報）とユーザーアクション（操作履歴）を分離して記録する仕組みを導入。システム全体のトレーサビリティを向上。

### Fixed
- ポーカーの盤面描画における座標の微調整と、フォントマネージャーの統合。
- Gitリポジトリ履歴のクリーンアップ。重複した初期コミットを整理し、GitHubとの同期を安定化。
- `PokerView` における条件分岐とインデントの修正。
