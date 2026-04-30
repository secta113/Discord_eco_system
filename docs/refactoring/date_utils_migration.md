# 日時取得処理のリファクタリング計画 (将来用)

## 概要
システム全体で日本時間 (JST) を取得する際、従来は各所で個別に `datetime.datetime.utcnow() + datetime.timedelta(hours=9)` を計算していました。
これを `core/utils/time_utils.py` に集約するリファクタリングが進められています。
ドブモン機能については既に対応済みですが、以下の機能については今後対応が必要です。

## 未対応のコンポーネント

### 1. デイリーボーナス機能 (`logic/economy/bonus.py`)
- **該当箇所**: `claim_daily` メソッド (L20-L21)
- **内容**:
  ```python
  jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
  today_str = jst_now.strftime("%Y-%m-%d")
  ```
- **修正方針**: `time_utils.get_jst_today()` に置き換える。

### 2. ガチャ機能 (`logic/gacha_service.py`)
- **該当箇所1**: `_check_and_reset_daily` メソッド (L46-L47)
- **該当箇所2**: `execute_gacha` メソッド (L130-L131)
- **内容**:
  ```python
  jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
  today_str = jst_now.strftime("%Y-%m-%d")
  ```
- **修正方針**: `time_utils.get_jst_today()` または `time_utils.get_jst_now()` に置き換える。

## リファクタリングのメリット
- **保守性の向上**: タイムゾーンの仕様変更（例: UTC直取得への変更など）に一か所で対応可能になります。
- **コードの簡潔化**: 重複する計算ロジックを排除し、コードの意図（「今日のJST日付を取得する」）を明確にします。
- **テストの容易性**: `time_utils` をモックすることで、日付に依存するテストが書きやすくなります。

## 実施時期
次回の経済システムまたはガチャ機能の大規模改修時に合わせて実施することを推奨します。
