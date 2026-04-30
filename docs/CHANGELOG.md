# Changelog

All notable changes to this project will be documented in this file.

## [v2.2] - 2026-05-01
### Added
- **専門サービスへの分解**: `DobumonService` を各機能（育成、戦闘、ショップ、遺伝）ごとの専門サービスに分解し、コードの保守性と拡張性を大幅に向上。
- **アセットマネジメントの最適化**: `CardAssetManager` によるトランプ画像の動的合成（Dynamic Synthesis）を導入。52枚の個別画像を読み込む代わりにパーツから生成することで、メモリ消費を劇的に削減。
- **高度な遺伝アルゴリズム**: 「Anti-Taboo」と「Singularity」の優先順位（Antinomy > Singularity > Anti-Taboo）を確立。遺伝の安定性と希少性を両立。
- **ショップ・エコシステム**: 「エリート・シンジケート」限定の変異ボーナスなど、ショップごとの特色あるロジックを実装。

### Fixed
- ポーカーの盤面描画における座標の微調整と、フォントマネージャーの統合。
- Gitリポジトリ履歴のクリーンアップ。重複した初期コミットを整理し、GitHubとの同期を安定化。
- `PokerView` における条件分岐とインデントの修正。
