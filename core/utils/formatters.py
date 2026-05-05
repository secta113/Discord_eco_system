from typing import Union


def f_commas(value: Union[int, float, str], signed: bool = False) -> str:
    """
    数値をカンマ区切り文字列に変換します。

    Args:
        value: 変換する数値。
        signed: True の場合、正の数に '+' を付与します。

    Returns:
        str: カマ区切りされた文字列。
    """
    try:
        if isinstance(value, str):
            if value.replace("-", "").isdigit():
                value = int(value)
            else:
                value = float(value)

        if isinstance(value, (int, float)):
            res = f"{value:,}"
            if signed and value > 0:
                return f"+{res}"
            return res
        return str(value)
    except (ValueError, TypeError):
        return str(value)


def f_pts(value: Union[int, float, str], signed: bool = False, bold: bool = False) -> str:
    """
    数値にカンマ区切りを適用し、末尾に ' pts' を付与します。
    """
    res = f_commas(value, signed=signed)
    if bold:
        return f"**{res}** pts"
    return f"{res} pts"


def f_bold_pts(value: Union[int, float, str]) -> str:
    """
    数値にカンマ区切りを適用して太字にし、末尾に ' pts' を付与します。
    例: 1000 -> "**1,000** pts"
    """
    return f"**{f_commas(value)}** pts"
