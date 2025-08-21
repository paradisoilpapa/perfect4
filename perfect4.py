# -*- coding: utf-8 -*-
"""
ヴェロビ分析優先ツール（7車・全場合算／開催日別） v2.1 〈Streamlit〉

目的：
- 競輪場は区別せず**全体で集計**、ただし**開催日（初日/2日目/3日目/最終日）別**で“ヴェロビの組み方”を可視化。
- 入力は「日次手入力（最大12R）」と「前日までの集計手入力（1～7位×入賞回数）」の2系統。
- 7車限定（4～7）。8車以上は対象外。
- 政春関連の指標・レコメンドは排除（分析特化）。

出すもの：
1) ランク別の **連対率/3着内率**（1～7）
2) **連対ペア**分布（{i,j}：順序なし, 開催日別）
3) **アンカー別**パートナーTop3（P(相手=j | アンカー=iが上位2)）
4) **トリオ（上位3集合）**のランキング
5) 軽量モード指標：高番手ペア率({1,2},{1,3},{2,3})、穴寄りペア率(片方が5～7)、一列棒状率（隊列）

※ 集計手入力（前日まで）は【ランク別入賞回数】をそのまま合算。ペア/トリオ/隊列は**日次手入力分のみ**から算出します。
"""

from collections import defaultdict
from typing import List, Dict, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ分析（開催日別）", layout="wide")
st.title("ヴェロビの“組み方”分析（7車・開催日別／全場合算） v2.1")

# ----------------------------
# 定数・ユーティリティ
# ----------------------------
DAY_OPTIONS = ["初日", "2日目", "3日目", "最終日"]


def parse_rankline(s: str) -> List[str]:
    """V順位の並び。'14...'(ハイフン無し)を正規とし、'-'や空白は除去。
    戻り値は車番の配列（例: ['1','4','7','3','2','5','6']）。
    条件: 4～7桁、各桁は1～7、重複なし。 不正なら []。
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
    if len(set(s)) != len(s):
        return []
    return list(s)


def parse_finish(s: str) -> List[str]:
    """着順（上位3まで）。'172' 等を想定。ハイフン等は除去。1～7、重複なし。"""
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
    st.caption("注: 競輪場別の出力は行いません。開催日別のみを全場合算で表示します。
ペア/トリオ/隊列の集計は日次手入力から計算。ランク別入賞は日次＋前日までの集計手入力を合算します。
入力は7車限定。V順位は '14...'、着順は上位3桁、隊列は '123|45|67' を想定しています。")

    cols_hdr = st.columns([1,1.2,1,2,1.2,2])
    cols_hdr[0].markdown("**R**")
    cols_hdr[1].markdown("**開催日**")
    cols_hdr[2].markdown("**頭数**")
    cols_hdr[3].markdown("**V順位(14...)**")
    cols_hdr[4].markdown("**着順(～3桁)**")
    cols_hdr[5].markdown("**隊列(任意)**")

    for i in range(1, 13):
        c1, c2, c3, c4, c5, c6 = st.columns([1,1.2,1,2,1.2,2])
        rid = c1.text_input("", key=f"rid_{i}", value=str(i))
        day = c2.selectbox("", DAY_OPTIONS + [""], index=len(DAY_OPTIONS), key=f"day_{i}")
        field = c3.number_input("", min_value=4, max_value=7, value=7, key=f"field_{i}")
        vline = c4.text_input("", key=f"vline_{i}", value="")
        fin = c5.text_input("", key=f"fin_{i}", value="")
        lineup = c6.text_input("", key=f"line_{i}", value="")

        vorder = parse_rankline(vline)
        finish = parse_finish(fin)
        blocks = parse_lineup(lineup)

        # バリデーション（何かしら入力がある行のみ判定）
        any_input = any([day, vorder, finish, blocks])
        if any_input:
            if day and vorder and (4 <= field <= 7) and len(vorder) <= field:
                byrace_rows.append({
                    "day": day,
                    "race": rid,
                    "field": field,
                    "vorder": vorder,
                    "finish": finish,
                    "lineup": blocks,
                })
            else:
                st.warning(f"R{rid}: 入力不整合（開催日/V順位/頭数を確認）。V順位は頭数桁以下、4～7車のみ対象。")

# ---------- B. 前日までの集計手入力 ----------
with input_tabs[1]:
    st.subheader("前日までの集計（開催日×ランク1～7の入賞回数）")
    st.caption(
        "分母 N_r（その開催日にVランク r が存在したレース数）と、1/2/3着回数を入力。未入力は0として扱います。"
    )

    for day in DAY_OPTIONS:
        st.markdown(f"**{day}**")
        ch = st.columns([1,1,1,1,1,1,1,1])
        ch[0].markdown("ランク")
        ch[1].markdown("N_r")
        ch[2].markdown("1着回数")
        ch[3].markdown("2着回数")
        ch[4].markdown("3着回数")
        ch[5].markdown("備考1")
        ch[6].markdown("備考2")
        ch[7].markdown("メモ")
        for r in range(1, 8):
            c0, c1, c2, c3, c4, c5, c6, c7 = st.columns([1,1,1,1,1,1,1,1])
            c0.write(str(r))
            N = c1.number_input("", key=f"agg_{day}_N_{r}", min_value=0, value=0)
            C1 = c2.number_input("", key=f"agg_{day}_C1_{r}", min_value=0, value=0)
            C2 = c3.number_input("", key=f"agg_{day}_C2_{r}", min_value=0, value=0)
            C3 = c4.number_input("", key=f"agg_{day}_C3_{r}", min_value=0, value=0)
            _ = c5.text_input("", key=f"agg_{day}_dummy1_{r}", value="")
            _ = c6.text_input("", key=f"agg_{day}_dummy2_{r}", value="")
            _ = c7.text_input("", key=f"agg_{day}_memo_{r}", value="")
            if any([N, C1, C2, C3]):
                rec = agg_counts_manual[(day, r)]
                rec["N"] += int(N)
                rec["C1"] += int(C1)
                rec["C2"] += int(C2)
                rec["C3"] += int(C3)

# ----------------------------
# 分析（集計器の構築）
# ----------------------------
# A) 日次手入力 → ランク別入賞回数、連対ペア、トリオ、隊列
rank_counts_daily: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(lambda: {"N":0, "C1":0, "C2":0, "C3":0})
pair_counts: Dict[Tuple[str, int, int], int] = defaultdict(int)  # key=(day,i,j) i<j（Vランク）
trio_counts: Dict[Tuple[str, Tuple[int,int,int]], int] = defaultdict(int)  # key=(day,(i,j,k)) sorted
anchor_totals: Dict[Tuple[str, int], int] = defaultdict(int)  # (day,i): アンカーiが上位2に来た回数
anchor_partner: Dict[Tuple[str, int, int], int] = defaultdict(int)  # (day,i,j): iが上位2のとき相手j

line_oneblock_total: Dict[str, int] = defaultdict(int)  # day→隊列入力あり件数
line_oneline_count: Dict[str, int] = defaultdict(int)   # day→一列棒状件数

for row in byrace_rows:
    day = row["day"]
    vorder = row["vorder"]
    finish = row["finish"]
    field = row["field"]

    # ランク→車番、車番→ランク
    car_by_rank = {i+1: vorder[i] for i in range(len(vorder))}
    rank_by_car = {car: i+1 for i, car in enumerate(vorder)}

    # ランク別入賞カウント
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

    # 連対ペア・アンカー分布（順序なし：二車複相当）
    if len(finish) >= 2 and all(f in rank_by_car for f in finish[:2]):
        i = rank_by_car[finish[0]]
        j = rank_by_car[finish[1]]
        a, b = sorted((i, j))
        pair_counts[(day, a, b)] += 1
        anchor_totals[(day, i)] += 1
        anchor_totals[(day, j)] += 1
        anchor_partner[(day, i, j)] += 1
        anchor_partner[(day, j, i)] += 1

    # トリオ（上位3の集合）
    if len(finish) >= 3 and all(f in rank_by_car for f in finish[:3]):
        i = rank_by_car[finish[0]]
        j = rank_by_car[finish[1]]
        k = rank_by_car[finish[2]]
        trio_counts[(day, tuple(sorted((i, j, k))))] += 1

    # 隊列
    blocks = row.get("lineup", [])
    if blocks:
        line_oneblock_total[day] += 1
        if len(blocks) == 1:
            line_oneline_count[day] += 1

# B) 手入力集計（前日まで）を合流（ランク別入賞のみ）
for (day, r), rec in agg_counts_manual.items():
    rank_counts_daily[(day, r)]["N"] += rec["N"]
    rank_counts_daily[(day, r)]["C1"] += rec["C1"]
    rank_counts_daily[(day, r)]["C2"] += rec["C2"]
    rank_counts_daily[(day, r)]["C3"] += rec["C3"]

# ----------------------------
# 出力タブ
# ----------------------------
with input_tabs[2]:
    st.subheader("開催日別：ランク別 入賞テーブル（1～7）")
    for day in DAY_OPTIONS:
        rows_out = []
        for r in range(1, 8):
            rec = rank_counts_daily.get((day, r), {"N":0,"C1":0,"C2":0,"C3":0})
            N, C1, C2, C3 = rec["N"], rec["C1"], rec["C2"], rec["C3"]
            def rate(x, n):
                return round(100*x/n, 1) if n>0 else None
            rows_out.append({
                "ランク": r,
                "出走数N": N,
                "1着回数": C1,
                "2着回数": C2,
                "3着回数": C3,
                "1着率%": rate(C1,N),
                "連対率%": rate(C1+C2,N),
                "3着内率%": rate(C1+C2+C3,N),
            })
        df_day = pd.DataFrame(rows_out)
        st.markdown(f"### {day}")
        st.dataframe(df_day, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("開催日別：連対ペア分布（{i,j}：順序なし／件数と構成比%）")
    for day in DAY_OPTIONS:
        denom = sum(v for (d, i, j), v in pair_counts.items() if d == day)
        if denom == 0:
            st.markdown(f"**{day}**：データ不足")
            continue
        pairs = []
        for i in range(1,8):
            for j in range(i+1,8):
                cnt = pair_counts.get((day, i, j), 0)
                if cnt>0:
                    pairs.append({"ペア": f"{{{i},{j}}}", "件数": cnt, "構成比%": round(100*cnt/denom,1)})
        df_pairs = pd.DataFrame(pairs).sort_values(["件数"], ascending=False)
        st.markdown(f"**{day}**")
        st.dataframe(df_pairs, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("開催日別：アンカー別パートナーTop3（P(相手|アンカー)）")
    for day in DAY_OPTIONS:
        blocks = []
        for i in range(1,8):
            total = anchor_totals.get((day, i), 0)
            if total == 0:
                continue
            partners = []
            for j in range(1,8):
                if j == i:
                    continue
                cnt = anchor_partner.get((day, i, j), 0)
                if cnt>0:
                    partners.append((j, cnt/total))
            partners.sort(key=lambda x: x[1], reverse=True)
            partners = partners[:3]
            blocks.append({
                "アンカー": i,
                "相手1": partners[0][0] if len(partners)>0 else None,
                "P1%": round(100*partners[0][1],1) if len(partners)>0 else None,
                "相手2": partners[1][0] if len(partners)>1 else None,
                "P2%": round(100*partners[1][1],1) if len(partners)>1 else None,
                "相手3": partners[2][0] if len(partners)>2 else None,
                "P3%": round(100*partners[2][1],1) if len(partners)>2 else None,
            })
        if blocks:
            st.markdown(f"**{day}**")
            st.dataframe(pd.DataFrame(blocks), use_container_width=True, hide_index=True)
        else:
            st.markdown(f"**{day}**：データ不足")

    st.divider()
    st.subheader("開催日別：トリオ（上位3集合）のランキング")
    for day in DAY_OPTIONS:
        denom3 = sum(v for (d, tri), v in trio_counts.items() if d == day)
        if denom3 == 0:
            st.markdown(f"**{day}**：データ不足")
            continue
        tri_rows = []
        for i in range(1,6):
            for j in range(i+1,7):
                for k in range(j+1,8):
                    cnt = trio_counts.get((day, (i,j,k)), 0)
                    if cnt>0:
                        tri_rows.append({"トリオ": f"{{{i},{j},{k}}}", "件数": cnt, "構成比%": round(100*cnt/denom3,1)})
        df_tri = pd.DataFrame(tri_rows).sort_values(["件数"], ascending=False)
        st.markdown(f"**{day}**")
        st.dataframe(df_tri, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("開催日別：モード指標（高番手/穴ペア率・一列棒状率）")
    mode_rows = []
    for day in DAY_OPTIONS:
        denom_pairs = sum(v for (d, i, j), v in pair_counts.items() if d == day)
        high = sum(pair_counts.get((day, i, j), 0) for (i, j) in [(1,2),(1,3),(2,3)])
        hole = sum(v for (d, i, j), v in pair_counts.items() if d==day and ((i>=5) or (j>=5)))
        denom_line = line_oneblock_total.get(day, 0)
        one_line = line_oneline_count.get(day, 0)
        mode_rows.append({
            "開催日": day,
            "高番手ペア率%": round(100*high/denom_pairs,1) if denom_pairs>0 else None,
            "穴寄りペア率%": round(100*hole/denom_pairs,1) if denom_pairs>0 else None,
            "一列棒状率%": round(100*one_line/denom_line,1) if denom_line>0 else None,
            "分母(ペア)": denom_pairs,
            "分母(隊列)": denom_line,
        })
    st.dataframe(pd.DataFrame(mode_rows), use_container_width=True, hide_index=True)

st.caption("注: 競輪場別の出力は行いません。開催日別のみを全場合算で表示します。
ペア/トリオ/隊列の集計は日次手入力から計算。ランク別入賞は日次＋前日までの集計手入力を合算します。
入力は7車限定。V順位は '14...'、着順は上位3桁、隊列は '123|45|67' を想定しています。")
