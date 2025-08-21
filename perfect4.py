# -*- coding: utf-8 -*-
"""
ヴェロビ分析優先ツール（7車・全場合算／開催日別） v2.0 〈Streamlit〉

目的：
- 競輪場は区別せず**全体で集計**、ただし**開催日（初日/2日目/3日目/最終日）別**で“ヴェロビの組み方”を可視化。
- 入力は「日次手入力（最大12R）」と「前日までの集計手入力（1～7位×入賞回数）」の2系統。
- 7車限定（4～7）。8車以上は対象外。
- 政春関連の指標・レコメンドは一旦排除（分析特化）。

出すもの：
1) ランク別の **連対率/3着内率**（1～7）
2) **連対ペア**分布（{i,j}：順序なし, 開催日別）
3) **アンカー別**パートナーTop3（P(相手=j | アンカー=iが上位2)）
4) **トリオ（上位3集合）**のランキング
5) 軽量モード指標：高番手ペア率({1,2},{1,3},{2,3})、穴寄りペア率(片方が5～7)、一列棒状率（隊列）

※ 集計手入力（前日まで）は【ランク別入賞回数】をそのまま合算。ペア/トリオ/隊列は**日次手入力分のみ**から算出します。
"""

from collections import defaultdict, Counter
from typing import List, Dict, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ分析（開催日別）", layout="wide")
st.title("ヴェロビの“組み方”分析（7車・開催日別／全場合算） v2.0")

# ----------------------------
# 定数・ユーティリティ
# ----------------------------
DAY_OPTIONS = ["初日", "2日目", "3日目", "最終日"]


def parse_rankline(s: str) -> List[str]:
    """V順位の並び。'14...'(ハイフン無し)を正規とし、'-'や空白は除去。
    戻り値は車番の配列（例: ['1','4','7','3','2','5','6']）。
    条件: 4～7桁、各桁は1～7、重複なし。
    不正なら空リスト。
    """
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    if not s.isdigit():
        return []
    if not (4 <= len(s) <= 7):
        return []
    if any(ch not in "1234567" for ch in s):
        return []
    # 重複チェック
    if len(set(s)) != len(s):
        return []
    return list(s)


def parse_finish(s: str) -> List[str]:
    """着順（上位3まで）。'172' 等を想定。ハイフン等は除去。1～7、重複なし。"""
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    s = "".join(ch for ch in s if ch in "1234567")
    out = []
    for ch in s:
        if ch not in out:
            out.append(ch)
        if len(out) == 3:
            break
    return out


def parse_lineup(s: str) -> List[List[str]]:
    """隊列 '123|45|67' → [['1','2','3'], ['4','5'], ['6','7']]。空なら[]。"""
    if not s:
        return []
    s = s.replace(" ", "")
    blocks = [list(filter(lambda x: x in "1234567", list(b))) for b in s.split("|")]
    blocks = [b for b in blocks if b]
    return blocks


# ----------------------------
# 入力タブ
# ----------------------------
input_tabs = st.tabs(["日次手入力（最大12R）", "前日までの集計（ランク別回数）", "分析結果"])

# 状態保持（集計器）
byrace_rows: List[Dict] = []
agg_counts_manual: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(lambda: {"N": 0, "C1": 0, "C2": 0, "C3": 0})

# ---------- A. 日次手入力 ----------
with input_tabs[0]:
    st.subheader("日次手入力（開催日別・最大12R）")
st.caption(
    "注: 競輪場別の出力は行いません。開催日別のみを全場合算で表示します。
"
    "ペア/トリオ/隊列の集計は日次手入力から計算。ランク別入賞は日次＋前日までの集計手入力を合算します。
"
    "入力は7車限定。V順位は '14...'、着順は上位3桁、隊列は '123|45|67' を想定しています。"
)

"
    "入力は7車限定。V順位は '14...'、着順は上位3桁、隊列は '123|45|67' を想定しています。"
)

