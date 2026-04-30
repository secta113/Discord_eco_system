# エコノミー・エラーハンドリング標準化仕様書

## 概要
システム全体のエコノミー（経済機能）に関連するエラーハンドリングを、従来の「戻り値（bool/tuple）チェック方式」から「例外（Exception）送出方式」へ刷新しました。これにより、ロジック層とUI層の責任が明確になり、ユーザーに対して一貫した高級感のある（黄金テーマの）フィードバックを提供することが可能になりました。

## 例外設計 (Exceptions)

### 1. 例外の階層構造
すべての経済エラーは `core.utils.exceptions.EconomyError` を基底クラスとしています。

- `EconomyError` (Base)
    - `InsufficientFundsError`: 所持金不足（参加コスト、チップ不足など）
    - `BetLimitViolationError`: ランク別ベット額上限違反
    - `DailyAlreadyClaimedError`: デイリーボーナスの二重受け取り
    - `GachaLimitReachedError`: ガチャの1日上限（3回）到達

### 2. 送出ルール
ロジック層（`BetService`, `EconomyProvider`, `GachaService` 等）は、経済ルールに違反した場合、**メッセージを返さず、即座に適切な例外を送出**します。呼び出し側での手動の `if not success:` チェックは原則不要です。

## UI/UX仕様 (Gold Theme)

### 1. エコノミー専用フォーマッタ
経済関連のエラーが発生した場合、`EconomyFormatter` を通じて以下のデザインが適用されます。

- **Embed Color**: `0xF1C40F` (Gold)
- **スタイル**: メッセージの冒頭にエラー内容に応じた絵文字（💸, ⚠️, 🎰 等）が付与されます。
- **表示属性**: 原則として `ephemeral=True`（本人にのみ見える形式）として送信され、チャンネルのログを汚しません。

### 2. グローバル・ハンドリング
`system.py` のグローバルエラーハンドラが `EconomyError` を検知し、自動的に上記のゴールドテーマを適用します。また、ボタン操作（Views）に関しても `JoinView.on_error` 等で同様の処理が共通化されています。

## 改修された主要コンポーネント

### 1. Service/Provider層
- **[BetService](file:///d:/python_project/Discord_eco_system/logic/bet_service.py)**: `validate_bet`, `escrow`, `claim_daily` が例外ベースに変更。
- **[EconomyProvider](file:///d:/python_project/Discord_eco_system/logic/economy/provider.py)**: `escrow` が `InsufficientFundsError` を送出。
- **[GachaService](file:///d:/python_project/Discord_eco_system/logic/gacha_service.py)**: ガチャ実行可否を `can_play` 例外で判定。

### 2. 管理層 (Managers)
- **[GameManager](file:///d:/python_project/Discord_eco_system/managers/manager.py)**: `join_session` での例外握り潰しを廃止。
- **[BaseGameSession](file:///d:/python_project/Discord_eco_system/managers/game_session.py)**: `add_player`, `can_start` が `GameActionError` または `EconomyError` を送出。

### 3. UI層 (Cogs/Views)
- **[Economy Cog](file:///d:/python_project/Discord_eco_system/cogs/economy.py)**: `daily`, `pay` コマンドの簡略化。
- **[Games Cog](file:///d:/python_project/Discord_eco_system/cogs/games.py)**: `gacha` コマンドからの手動チェック排除。
- **[JoinView](file:///d:/python_project/Discord_eco_system/core/ui/common.py)**: 参加ボタンおよび開始ボタンの例外駆動化。

## 開発上の注意点
新しい経済機能やギャンブルアクションを追加する場合、以下のガイドラインに従ってください。

1. **バリデーション**: `BetService.validate_bet` または `escrow` を呼び出し、不備がある場合は例外をそのまま通す。
2. **エラー表示**: 独自に `interaction.response.send_message` でエラーメッセージを構築せず、例外を送出してシステムに委ねる（黄金テーマを適用するため）。
3. **テスト**: 異常系のテストでは `with pytest.raises(EconomyError):` を使用して、正しい例外が飛んでいるかを確認する。
