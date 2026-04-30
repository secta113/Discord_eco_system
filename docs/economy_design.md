# 経済ロジック設計書 (economy_design.md)

> **最終更新**: 2026-03-29  
> *v2.4 へ更新 (Adaptive Benchmark / Tier Rebranding / Additive Daily Bonus)*

---

## 1. コンセプト：持続可能な「奪い合い」

- **非レベル制**: 「レベルで飯は奢れない」という哲学のもと、経験値やランクによるポイント供給を廃止。
- **勝負への集約**: 全てのポイント増減は、対人戦（Match/Chinchiro）または対システム戦（Blackjack）の結果に紐づく。
- **祝儀チャージ（Win-based Minting）**: 勝利の際、システムが「祝儀」としてポイントを補填し経済を循環させる。
- **動的租税（Taxation）**: 独走状態のプレイヤーが「勝ちすぎた」際、その利益の一部をジャックポットへ還元。

---

## 2. 経済指標とステータス判定

経済指標（Benchmark）を、アクティブユーザー数（N）に応じて動的に切り替え、格差是正の基準とします。

| 条件 | 採用指標 (Benchmark) | 理由 |
| :---- | :---- | :---- |
| N > 10 | **中央値 (Median)** | 外れ値（大富豪や破産者）の影響を排除し、安定した階層構造を維持するため。 |
| N <= 10 | **平均値 (Mean)** | 指標が特定の個人の残高に固執するのを防ぎ、全員の資産状況を滑らかに反映するため。 |

### ステータス区分とインセンティブ

| クラス | 判定条件 | 主なインセンティブ |
| :---- | :---- | :---- |
| **Prime** | 残高 > Benchmark | 資産配当 (資産に応じたボーナス) |
| **Standard** | Benchmark * 0.3 ≤ 残高 ≤ Benchmark | デイリー最低保証 + 底上げ配当 |
| **Recovery** | 残高 < Benchmark * 0.3 | デイリー最低保証 + 爆速復興支援 (SN) |
| **System** | user_id = 0 (不可変) | ジャックポット成長ボーナス (Standard同等) |

---

## 3. 接待（Bad Luck Protection / Hospitality）

負けが続いた際、あるいは資産状況が厳しい場合に、システムが「接待」として勝利確率を調整する仕組みです。詳細は [接待ロジック詳細仕様 (hospitality_logic.md)](file:///d:/python_project/Discord_eco_system/docs/hospitality_logic.md) を参照してください。

| クラス | 接待率 (Hospitality Rate) |
| :---- | :--- |
| **Prime** | **0.05 (5%)** |
| **Standard** | **0.20 (20%)** |
| **Recovery** | **0.40 (40%)** |

---

## 4. デイリーボーナス（加算型ハイブリッド）

「弱者救済」と「経済循環」を両立するため、固定の基本給とティア別ボーナスの**二階建て構造**を採用します。

### 4.1 計算式

```
DailyBonus = Base(1000) + TierBonus
```

1.  **Base (基本給)**: 全員一律 **1,000 pts**。
2.  **TierBonus**:
    *   **Prime**: `max(残高 * 0.01, Benchmark * 0.05)` (資産配当)
    *   **Standard**: `Benchmark * 0.05` (底上げ配当)
    *   **Recovery**: `(Benchmark * 0.05) + (再起ライン - 残高) * 0.50` (復興支援)
    *   **System**: `Benchmark * 0.05` (ジャックポット成長支援)
    *   ※再起ライン = Benchmark * 0.30

### 4.3 自動連動システム
経済圏の活性化を促すため、システムアカウントのデイリーボーナスは**「その日最初のユーザーによる請求」**があった瞬間に自動的に実行されます。
これにより、ジャックポットプールはプレイヤーの動きに応じて毎日確実に成長します。

### 4.2 実装パラメータ

| パラメータ名 | 設定値 | 説明 |
| :---- | :---- | :---- |
| `ADAPTIVE_THRESHOLD` | **10** | 平均値/中央値を切り替える境界人数 |
| `DAILY_BASE_PAY` | **1,000 pts** | 全員への最低保証（加算ベース） |
| `BI_RATE` | **0.05** | 底上げ率 (Benchmark に対する比率) |
| `DIVIDEND_RATE` | **0.01** | Prime層の資産配当率 |
| `SN_THRESHOLD_RATE` | **0.30** | 再起ライン判定閾値 (Benchmark に対する比率) |
| `SN_DIFF_RATE` | **0.50** | Recovery層の差分補填率 |

## 5. ジャックポット（希少役）ルール

希少役発生時にシステムプールから特別配当を支払う仕組みです。蓄積・配当の詳細は [ゲーム設計書 (game_design.md)](file:///d:/python_project/Discord_eco_system/docs/game_design.md) を参照してください。

---

## 6. システム・レバレッジ（Match奨励金）

Botを通した対人戦（Match機能）を活性化するための補填システムです。

- **計算式**: `Payout = Pot × (1.0 + MATCH_BONUS_RATE × ラバーバンド倍率)`
- **Standard / Recovery** の場合、ボーナス率に **1.5倍** (`RUBBERBAND_MULTIPLIER`) を適用。

| パラメータ | 値 | 説明 |
| :--- | :--- | :--- |
| `MATCH_BONUS_RATE` | **0.05** | 対人戦勝者へのシステム上乗せ率（基本5%） |
| `RUBBERBAND_MULTIPLIER` | **1.5** | Standard / Recovery への倍率 |

---

## 7. 実装の責務分担

| サービス | ファイル | 担当 |
| :--- | :--- | :--- |
| `EconomyProvider` | `logic/economy/provider.py` | 基礎入出金 / エスクロー / 払い出し |
| `BonusService` | `logic/economy/bonus.py` | 加算方式デイリーボーナス計算 |
| `JackpotService` | `logic/economy/jackpot.py` | ジャックポット積立・払い出し |
| `StatusService` | `logic/economy/status.py` | 動的ベンチマーク判定・ティア分類 |
| `GameLogicService` | `logic/economy/game_logic.py` | 接待レート管理・共通ゲームロジック |
