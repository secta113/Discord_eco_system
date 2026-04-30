def calculate_economy_weight(session, needed: int) -> float:
    """
    【経済重み付け計算モジュール】
    AIが「要求されているベット額(コールに必要な額やレイズ目標額)」を提示された際、
    それが現在のテーブルの「参加者全体の平均スタック」に対してどのくらい重いかを評価します。

    Args:
        session (TexasPokerService): 現在のゲームセッション状態
        needed (int): アクションを実行するために必要な追加の支払額

    Returns:
        float: 経済的重み (0.0 ~ 1.0+)。
               1.0 は「テーブル平均スタックと完全に同額の支払いを求められている」非常にプレッシャーのある状況を意味します。

    実装メモ:
        以前はサーバー全体のDBの中央値を計算しようとしていましたが、「参加プレイヤーが全員貧困層の場合にゲームが動かなくなる」
        懸念を考慮し、ローカル（現在稼働中のテーブルの参加者）の平均スタックを参照する設計に変更しています。
    """
    avg_stack = getattr(session, "table_average_stack", 0)
    if avg_stack <= 0:
        return 0.0

    return needed / avg_stack
