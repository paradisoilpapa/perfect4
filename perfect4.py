# -*- coding: utf-8 -*-

from collections import defaultdict
from typing import List, Dict, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ分析（開催区分別）", layout="wide")
st.title("ヴェロビ 組み方分析（7車・開催区分別／全体集計） v2.6")

# -------- 基本設定 --------
# 開催区分の内部キー（順序つき）
DAY_OPTIONS = ["L", "F2", "F1", "G"]

# 表示用ラベル
DAY_LABELS = {
    "L": "ガールズ（L級）",
    "F2": "F2",
    "F1": "F1",
    "G": "G",
}

# ランク表示：1～7 を ◎ 〇 ▲ △ × α β にマッピング（内部計算は数値のまま）
RANK_SYMBOLS = {1: "◎", 2: "〇", 3: "▲", 4: "△", 5: "×", 6: "α", 7: "β"}
def rank_symbol(r: int) -> str:
    return RANK_SYMBOLS.get(r, str(r))

def parse_rankline(s: str) -> List[str]:
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    if not s.isdigit() or not (4 <= len(s) <= 7):
        return []
    if any(ch not in "1234567" for ch in s):
        return []
    if len(set(s)) != len(s):
        return []
    return list(s)

def parse_finish(s: str) -> List[str]:
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    s = "".join(ch for ch in s if ch in "1234567")
    out: List[str] = []
    for ch in s:
        if ch not in out:
            out.append(ch)
        if len(out) == 3:
            break
    return out

# -------- 入力タブ --------
input_tabs = st.tabs(["日次手入力（最大12R）", "前日までの集計（ランク別回数）", "分析結果"])

byrace_rows: List[Dict] = []
agg_counts_manual: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(lambda: {"N": 0, "C1": 0, "C2": 0, "C3": 0})

# A. 日次手入力（開催区分は1回だけ指定→全行に適用）
with input_tabs[0]:
    st.subheader("日次手入力（開催区分別・最大12R）")

    day_global = st.selectbox(
        "開催区分（この選択を全レースに適用）",
        DAY_OPTIONS,
        key="global_day",
        format_func=lambda k: DAY_LABELS.get(k, k),
    )

    cols_hdr = st.columns([1,1,2,1.5])
    cols_hdr[0].markdown("**R**")
    cols_hdr[1].markdown("**頭数**")
    cols_hdr[2].markdown("**V順位(例: 1432...)**")
    cols_hdr[3].markdown("**着順(～3桁)**")

    for i in range(1, 13):
        c1, c2, c3, c4 = st.columns([1,1,2,1.5])
        rid = c1.text_input("", key=f"rid_{i}", value=str(i))
        field = c2.number_input("", min_value=4, max_value=7, value=7, key=f"field_{i}")
        vline = c3.text_input("", key=f"vline_{i}", value="")
        fin = c4.text_input("", key=f"fin_{i}", value="")

        vorder = parse_rankline(vline)
        finish = parse_finish(fin)

        any_input = any([vorder, finish])
        if any_input:
            if vorder and (4 <= field <= 7) and len(vorder) <= field:
                byrace_rows.append({
                    "day": day_global,   # 内部キー（"L","F2","F1","G"）
                    "race": rid,
                    "field": field,
                    "vorder": vorder,
                    "finish": finish,
                })
            else:
                st.warning(f"R{rid}: 入力不整合（V順位/頭数を確認）。V順位は頭数桁以下、4～7車のみ対象。")

# B. 前日までの集計（手入力）
with input_tabs[1]:
    st.subheader("前日までの集計（開催区分 × ランク（◎〜β）の入賞回数）")

    for day in DAY_OPTIONS:
        st.markdown(f"**{DAY_LABELS[day]}**")
        ch = st.columns([1,1,1,1])
        ch[0].markdown("ランク（表示）")
        ch[1].markdown("N_r")
        ch[2].markdown("1着回数")
        ch[3].markdown("2着回数／3着回数")
        for r in range(1, 8):
            c0, c1, c2, c3 = st.columns([1,1,1,1])
            c0.write(rank_symbol(r))
            N = c1.number_input("", key=f"agg_{day}_N_{r}", min_value=0, value=0)
            C1 = c2.number_input("", key=f"agg_{day}_C1_{r}", min_value=0, value=0)
            c3_cols = c3.columns(2)
            C2 = c3_cols[0].number_input("", key=f"agg_{day}_C2_{r}", min_value=0, value=0)
            C3 = c3_cols[1].number_input("", key=f"agg_{day}_C3_{r}", min_value=0, value=0)
            if any([N, C1, C2, C3]):
                rec = agg_counts_manual[(day, r)]
                rec["N"] += int(N)
                rec["C1"] += int(C1)
                rec["C2"] += int(C2)
                rec["C3"] += int(C3)

# -------- 集計構築（開催区分別 + 全体） --------
rank_counts_daily: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(lambda: {"N":0, "C1":0, "C2":0, "C3":0})

for row in byrace_rows:
    day = row["day"]
    vorder = row["vorder"]
    finish = row["finish"]

    car_by_rank = {i+1: vorder[i] for i in range(len(vorder))}

    L = len(vorder)
    for i in range(1, min(L,7)+1):
        rank_counts_daily[(day, i)]["N"] += 1
        car = car_by_rank[i]
        if len(finish) >= 1 and finish[0] == car:
            rank_counts_daily[(day, i)]["C1"] += 1
        if len(finish) >= 2 and finish[1] == car:
            rank_counts_daily[(day, i)]["C2"] += 1
        if len(finish) >= 3 and finish[2] == car:
            rank_counts_daily[(day, i)]["C3"] += 1

for (day, r), rec in agg_counts_manual.items():
    rank_counts_daily[(day, r)]["N"] += rec["N"]
    rank_counts_daily[(day, r)]["C1"] += rec["C1"]
    rank_counts_daily[(day, r)]["C2"] += rec["C2"]
    rank_counts_daily[(day, r)]["C3"] += rec["C3"]

# 全体集計の構築
rank_counts_total: Dict[int, Dict[str, int]] = {r: {"N":0, "C1":0, "C2":0, "C3":0} for r in range(1,8)}
for (day, r), rec in rank_counts_daily.items():
    for k in ("N","C1","C2","C3"):
        rank_counts_total[r][k] += rec[k]

# -------- 出力タブ --------
with input_tabs[2]:
    # 開催区分別：ランク別 入賞テーブル
    st.subheader("開催区分別：ランク別 入賞テーブル（◎〜β）")
    for day in DAY_OPTIONS:
        rows_out = []
        for r in range(1, 8):
            rec = rank_counts_daily.get((day, r), {"N":0,"C1":0,"C2":0,"C3":0})
            N, C1, C2, C3 = rec["N"], rec["C1"], rec["C2"], rec["C3"]
            def rate(x, n): return round(100*x/n, 1) if n>0 else None
            rows_out.append({
                "ランク": rank_symbol(r),
                "出走数N": N,
                "1着回数": C1,
                "2着回数": C2,
                "3着回数": C3,
                "1着率%": rate(C1,N),
                "連対率%": rate(C1+C2,N),
                "3着内率%": rate(C1+C2+C3,N),
            })
        df_day = pd.DataFrame(rows_out)
        st.markdown(f"### {DAY_LABELS[day]}")
        st.dataframe(df_day, use_container_width=True, hide_index=True)

    # 全体：ランク別 入賞テーブル
    rows_total = []
    for r in range(1, 8):
        rec = rank_counts_total.get(r, {"N":0,"C1":0,"C2":0,"C3":0})
        N, C1, C2, C3 = rec["N"], rec["C1"], rec["C2"], rec["C3"]
        def rate(x, n): return round(100*x/n, 1) if n>0 else None
        rows_total.append({
            "ランク": rank_symbol(r),
            "出走数N": N,
            "1着回数": C1,
            "2着回数": C2,
            "3着回数": C3,
            "1着率%": rate(C1,N),
            "連対率%": rate(C1+C2,N),
            "3着内率%": rate(C1+C2+C3,N),
        })
    st.markdown("### 全体")
    st.dataframe(pd.DataFrame(rows_total), use_container_width=True, hide_index=True)
