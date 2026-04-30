# **daily_logic_V2.4**

## **1\. 経済指標の動的選定 (Economic Benchmark)**

ステータス判定（Prime/Standard/Recovery）の基準となる「経済指標（Benchmark）」を、アクティブユーザー数（N）に応じて動的に切り替えます。

| 条件 | 採用指標 | 理由 |
| :---- | :---- | :---- |
| N \> 10 | **中央値 (Median)** | 外れ値（大富豪や破産者）の影響を排除し、安定した階層構造を維持するため。 |
| N \<= 10 | **平均値 (Mean)** | 指標が特定の個人の残高に固執するのを防ぎ、全員の資産状況を滑らかに反映するため。 |

## **2\. 統合ステータスと判定式**

指標を Benchmark と置き換え、各階層を判定します。

| クラス | 判定条件 | インセンティブ |
| :---- | :---- | :---- |
| **Prime** | Balance \> Benchmark | 資産配当 MAX(1%, Benchmark \* 5%) / 損失リベート |
| **Standard** | Benchmark \* 0.3 \<= Balance \<= Benchmark | 底上げ配給 (Benchmark \* 5%) |
| **Recovery** | Balance \< Benchmark \* 0.3 | 爆速復興支援 (BI \+ SN成分) / 勝利倍率2.0倍 |

## **3\. デイリー配当（Daily Dividend）ロジック**

**計算式**: DailyBonus \= Base(1000) \+ TierBonus

1. **Base (基本給)**: 全員一律 **1,000 pts**。  
2. **TierBonus**:  
   * **Prime**: MAX(Balance \* 0.01, Benchmark \* 0.05)  
   * **Standard**: Benchmark \* 0.05  
   * **Recovery**: (Benchmark \* 0.05) \+ (再起ライン \- Balance) \* 0.50  
   * ※再起ライン \= Benchmark \* 0.30

## **4\. 小規模コミュニティでの挙動例 (N \= 5\)**

残高: 50,000, 12,000, 8,000, 5,000, 0 の場合

* **平均値 (Mean)**: 15,000  
* **中央値 (Median)**: 8,000

**【平均値を採用した場合】**

* **Prime**: 50,000 の人のみ（1人）  
* **Standard**: 12,000, 8,000, 5,000（3人）  
* **Recovery**: 0（1人）  
* **結果**: 1位が「支える側」になり、中堅層がしっかり「Standard」として保護される。

**【中央値を採用していた場合】**

* **Prime**: 50,000, 12,000（2人）  
* **Standard**: 8,000（1人）  
* **Recovery**: 5,000, 0（2人）  
* **結果**: 5,000 pts 持っている人（初期値の半分）まで「絶望層」扱いになり、過剰な扶助が発生してしまう。

## **5\. 経済パラメータ要約（実装用）**

| パラメータ名 | 設定値 | 説明 |
| :---- | :---- | :---- |
| ADAPTIVE\_THRESHOLD | 10 | 平均値/中央値を切り替える境界人数 |
| DAILY\_BASE\_PAY | 1,000 pts | 全員への最低保証 |
| BI\_RATE | 0.05 | 底上げ率 (Benchmark に対する比率) |
| DIVIDEND\_RATE | 0.01 | Prime層の資産配当率 |
| SN\_THRESHOLD\_RATE | 0.30 | 再起ライン判定閾値 (Benchmark に対する比率) |
| SN\_DIFF\_RATE | 0.50 | Recovery層の差分補填率 |

