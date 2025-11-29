# -*- coding: utf-8 -*- 

from collections import defaultdict
from typing import List, Dict, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ分析（開催区分別）", layout="wide")
st.title("ヴェロビ 組み方分析（可変頭数・開催区分別／全体集計） v2.7")

# -------- 基本設定 --------
# 最大頭数（7→9へ拡張）
MAX_FIELD = 9

# 開催区分の内部キー（順序つき）
DAY_OPTIONS = ["L", "F2", "F1", "G"]

# 表示用ラベル
DAY_LABELS = {
    "L": "ガールズ（L級）",
    "F2": "F2",
    "F1": "F1",
    "G": "G",
}

# ランク表示：1～MAX_FIELD（7位以降は無）
RANK_SYMBOLS = {
    1: "carFR順位１位", 2: "carFR順位２位", 3: "carFR順位３位", 4: "carFR順位４位", 5: "carFR順位５位", 6: "carFR順位６位",
    7: "carFR順位７～位", 8: "carFR順位７～位", 9: "carFR順位７～位",
}
def rank_symbol(r: int) -> str:
    return RANK_SYMBOLS.get(r, "carFR順位７～位")


def parse_rankline(s: str) -> List[str]:
    """
    V順位（例: '1432...'）をパース。
    - 許容文字: 1～9
    - 4～MAX_FIELD 桁
    - 重複なし
    """
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    if not s.isdigit() or not (4 <= len(s) <= MAX_FIELD):
        return []
    if any(ch not in "123456789" for ch in s):
        return []
    if len(set(s)) != len(s):
        return []
    return list(s)

def parse_finish(s: str) -> List[str]:
    """
    着順（～3桁まで使用、余分は切り捨て）
    - 許容文字: 1～9
    - 重複は先着優先で無視
    """
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    s = "".join(ch for ch in s if ch in "123456789")
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
        field = c2.number_input("", min_value=4, max_value=MAX_FIELD, value=min(7, MAX_FIELD), key=f"field_{i}")
        vline = c3.text_input("", key=f"vline_{i}", value="")
        fin = c4.text_input("", key=f"fin_{i}", value="")

        vorder = parse_rankline(vline)
        finish = parse_finish(fin)

        any_input = any([vorder, finish])
        if any_input:
            # V順位は頭数以下の桁であること（例外: 未入力は許容）
            if vorder and (4 <= field <= MAX_FIELD) and len(vorder) <= field:
                byrace_rows.append({
                    "day": day_global,   # 内部キー（"L","F2","F1","G"）
                    "race": rid,
                    "field": field,
                    "vorder": vorder,
                    "finish": finish,
                })
            else:
                st.warning(f"R{rid}: 入力不整合（V順位/頭数を確認）。V順位は頭数桁以下、4～{MAX_FIELD}車のみ対象。")

# B. 前日までの集計（手入力）
with input_tabs[1]:
    st.subheader("前日までの集計（開催区分 × ランク（◎〜無）の入賞回数）")

    MU_BIN_R = 7  # 無 まとめ先のランク番号（内部は7に集約）
    def add_rec(day: str, r: int, N: int, C1: int, C2: int, C3: int):
        rec = agg_counts_manual[(day, r)]
        rec["N"]  += int(N)
        rec["C1"] += int(C1)
        rec["C2"] += int(C2)
        rec["C3"] += int(C3)

    for day in DAY_OPTIONS:
        st.markdown(f"**{DAY_LABELS[day]}**")
        ch = st.columns([1,1,1,1])
        ch[0].markdown("ランク（表示）")
        ch[1].markdown("N_r")
        ch[2].markdown("1着回数")
        ch[3].markdown("2着回数／3着回数")

        # 1～6を個別入力
        for r in range(1, 7):
            c0, c1, c2, c3 = st.columns([1,1,1,1])
            c0.write(rank_symbol(r))
            N  = c1.number_input("", key=f"agg_{day}_N_{r}",  min_value=0, value=0)
            C1 = c2.number_input("", key=f"agg_{day}_C1_{r}", min_value=0, value=0)
            c3_cols = c3.columns(2)
            C2 = c3_cols[0].number_input("", key=f"agg_{day}_C2_{r}", min_value=0, value=0)
            C3 = c3_cols[1].number_input("", key=f"agg_{day}_C3_{r}", min_value=0, value=0)
            if any([N, C1, C2, C3]):
                add_rec(day, r, N, C1, C2, C3)

        # 無（β以降をここに一本化）
        c0, c1, c2, c3 = st.columns([1,1,1,1])
        c0.write("carFR順位７～位")
        N_mu  = c1.number_input("", key=f"agg_{day}_N_{MU_BIN_R}",  min_value=0, value=0)
        C1_mu = c2.number_input("", key=f"agg_{day}_C1_{MU_BIN_R}", min_value=0, value=0)
        c3_cols = c3.columns(2)
        C2_mu = c3_cols[0].number_input("", key=f"agg_{day}_C2_{MU_BIN_R}", min_value=0, value=0)
        C3_mu = c3_cols[1].number_input("", key=f"agg_{day}_C3_{MU_BIN_R}", min_value=0, value=0)
        if any([N_mu, C1_mu, C2_mu, C3_mu]):
            add_rec(day, MU_BIN_R, N_mu, C1_mu, C2_mu, C3_mu)


# -------- 集計構築（開催区分別 + 全体） --------
rank_counts_daily: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(lambda: {"N":0, "C1":0, "C2":0, "C3":0})

for row in byrace_rows:
    day = row["day"]
    vorder = row["vorder"]
    finish = row["finish"]

    car_by_rank = {i+1: vorder[i] for i in range(len(vorder))}

    L = len(vorder)
    for i in range(1, min(L, MAX_FIELD) + 1):
        rank_counts_daily[(day, i)]["N"] += 1
        car = car_by_rank[i]
        if len(finish) >= 1 and finish[0] == car:
            rank_counts_daily[(day, i)]["C1"] += 1
        if len(finish) >= 2 and finish[1] == car:
            rank_counts_daily[(day, i)]["C2"] += 1
        if len(finish) >= 3 and finish[2] == car:
            rank_counts_daily[(day, i)]["C3"] += 1

# 手入力の前日まで集計を合算
for (day, r), rec in agg_counts_manual.items():
    rank_counts_daily[(day, r)]["N"]  += rec["N"]
    rank_counts_daily[(day, r)]["C1"] += rec["C1"]
    rank_counts_daily[(day, r)]["C2"] += rec["C2"]
    rank_counts_daily[(day, r)]["C3"] += rec["C3"]

# 全体集計の構築
rank_counts_total: Dict[int, Dict[str, int]] = {r: {"N":0, "C1":0, "C2":0, "C3":0} for r in range(1, MAX_FIELD + 1)}
for (day, r), rec in rank_counts_daily.items():
    for k in ("N","C1","C2","C3"):
        rank_counts_total[r][k] += rec[k]

# -------- 出力タブ --------
with input_tabs[2]:
    st.subheader("開催区分別：ランク別 入賞テーブル（◎〜無）")
    for day in DAY_OPTIONS:
        rows_out = []
        # 1～6位は個別
        for r in range(1, 7):
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

        # 7位以降を「無」にまとめる
        N=C1=C2=C3=0
        for r in range(7, MAX_FIELD+1):
            rec = rank_counts_daily.get((day, r), {"N":0,"C1":0,"C2":0,"C3":0})
            N  += rec["N"]
            C1 += rec["C1"]
            C2 += rec["C2"]
            C3 += rec["C3"]
        def rate(x, n): return round(100*x/n, 1) if n>0 else None
        rows_out.append({
            "ランク": "無",
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

    # 全体集計も同じ処理
    rows_total = []
    for r in range(1, 7):
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

    # 無にまとめる
    N=C1=C2=C3=0
    for r in range(7, MAX_FIELD+1):
        rec = rank_counts_total.get(r, {"N":0,"C1":0,"C2":0,"C3":0})
        N  += rec["N"]
        C1 += rec["C1"]
        C2 += rec["C2"]
        C3 += rec["C3"]
    def rate(x, n): return round(100*x/n, 1) if n>0 else None
    rows_total.append({
        "ランク": "無",
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





