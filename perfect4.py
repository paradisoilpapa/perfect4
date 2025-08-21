# -*- coding: utf-8 -*-

from collections import defaultdict
from typing import List, Dict, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ分析（開催日別）", layout="wide")
st.title("ヴェロビ 組み方分析（7車・開催日別／全体集計） v2.4")

# -------- 基本設定 --------
DAY_OPTIONS = ["初日", "2日目", "3日目"]  # 最終日を除外


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

# A. 日次手入力（開催日は1回だけ指定→全行に適用）
with input_tabs[0]:
    st.subheader("日次手入力（開催日別・最大12R）")

    day_global = st.selectbox("開催日（この選択を全レースに適用）", DAY_OPTIONS, key="global_day")

    cols_hdr = st.columns([1,1,2,1.5])
    cols_hdr[0].markdown("**R**")
    cols_hdr[1].markdown("**頭数**")
    cols_hdr[2].markdown("**V順位(14...)**")
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
                    "day": day_global,
                    "race": rid,
                    "field": field,
                    "vorder": vorder,
                    "finish": finish,
                })
            else:
                st.warning(f"R{rid}: 入力不整合（V順位/頭数を確認）。V順位は頭数桁以下、4～7車のみ対象。")

# B. 前日までの集計（手入力）
with input_tabs[1]:
    st.subheader("前日までの集計（開催日×ランク1～7の入賞回数）")

    for day in DAY_OPTIONS:
        st.markdown(f"**{day}**")
        ch = st.columns([1,1,1,1])
        ch[0].markdown("ランク")
        ch[1].markdown("N_r")
        ch[2].markdown("1着回数")
        ch[3].markdown("2着回数／3着回数")
        for r in range(1, 8):
            c0, c1, c2, c3 = st.columns([1,1,1,1])
            c0.write(str(r))
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

# -------- 集計構築（開催日別 + 全体） --------
rank_counts_daily: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(lambda: {"N":0, "C1":0, "C2":0, "C3":0})
pair_counts: Dict[Tuple[str, int, int], int] = defaultdict(int)
trio_counts: Dict[Tuple[str, Tuple[int,int,int]], int] = defaultdict(int)
anchor_totals: Dict[Tuple[str, int], int] = defaultdict(int)
anchor_partner: Dict[Tuple[str, int, int], int] = defaultdict(int)

for row in byrace_rows:
    day = row["day"]
    vorder = row["vorder"]
    finish = row["finish"]

    car_by_rank = {i+1: vorder[i] for i in range(len(vorder))}
    rank_by_car = {car: i+1 for i, car in enumerate(vorder)}

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

    if len(finish) >= 2 and all(f in rank_by_car for f in finish[:2]):
        i = rank_by_car[finish[0]]
        j = rank_by_car[finish[1]]
        a, b = sorted((i, j))
        pair_counts[(day, a, b)] += 1
        anchor_totals[(day, i)] += 1
        anchor_totals[(day, j)] += 1
        anchor_partner[(day, i, j)] += 1
        anchor_partner[(day, j, i)] += 1

    if len(finish) >= 3 and all(f in rank_by_car for f in finish[:3]):
        i = rank_by_car[finish[0]]
        j = rank_by_car[finish[1]]
        k = rank_by_car[finish[2]]
        trio_counts[(day, tuple(sorted((i, j, k))))] += 1

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

pair_counts_total: Dict[Tuple[int,int], int] = defaultdict(int)
for (day, i, j), v in pair_counts.items():
    pair_counts_total[(i, j)] += v

trio_counts_total: Dict[Tuple[int,int,int], int] = defaultdict(int)
for (day, tri), v in trio_counts.items():
    trio_counts_total[tri] += v

anchor_totals_total: Dict[int, int] = defaultdict(int)
for (day, i), v in anchor_totals.items():
    anchor_totals_total[i] += v

anchor_partner_total: Dict[Tuple[int,int], int] = defaultdict(int)
for (day, i, j), v in anchor_partner.items():
    anchor_partner_total[(i, j)] += v

# -------- 出力タブ --------
with input_tabs[2]:
    # 1) ランク別 入賞テーブル
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

    # 全体
    rows_total = []
    for r in range(1, 8):
        rec = rank_counts_total.get(r, {"N":0,"C1":0,"C2":0,"C3":0})
        N, C1, C2, C3 = rec["N"], rec["C1"], rec["C2"], rec["C3"]
        def rate(x, n):
            return round(100*x/n, 1) if n>0 else None
        rows_total.append({
            "ランク": r,
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

    st.divider()
    # 2) 連対ペア分布
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

    # 全体
    denom_all = sum(pair_counts_total.values())
    st.markdown("**全体**")
    if denom_all == 0:
        st.markdown("全体：データ不足")
    else:
        pairs_all = []
        for i in range(1,8):
            for j in range(i+1,8):
                cnt = pair_counts_total.get((i, j), 0)
                if cnt>0:
                    pairs_all.append({"ペア": f"{{{i},{j}}}", "件数": cnt, "構成比%": round(100*cnt/denom_all,1)})
        df_pairs_all = pd.DataFrame(pairs_all).sort_values(["件数"], ascending=False)
        st.dataframe(df_pairs_all, use_container_width=True, hide_index=True)

    st.divider()
    # 3) アンカー別パートナーTop3
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

    # 全体
    blocks_all = []
    for i in range(1,8):
        total = anchor_totals_total.get(i, 0)
        if total == 0:
            continue
        partners = []
        for j in range(1,8):
            if j == i:
                continue
            cnt = anchor_partner_total.get((i, j), 0)
            if cnt>0:
                partners.append((j, cnt/total))
        partners.sort(key=lambda x: x[1], reverse=True)
        partners = partners[:3]
        blocks_all.append({
            "アンカー": i,
            "相手1": partners[0][0] if len(partners)>0 else None,
            "P1%": round(100*partners[0][1],1) if len(partners)>0 else None,
            "相手2": partners[1][0] if len(partners)>1 else None,
            "P2%": round(100*partners[1][1],1) if len(partners)>1 else None,
            "相手3": partners[2][0] if len(partners)>2 else None,
            "P3%": round(100*partners[2][1],1) if len(partners)>2 else None,
        })
    st.markdown("**全体**")
    if blocks_all:
        st.dataframe(pd.DataFrame(blocks_all), use_container_width=True, hide_index=True)
    else:
        st.markdown("全体：データ不足")

    st.divider()
    # 4) トリオ（上位3集合）
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

    # 全体
    denom3_all = sum(trio_counts_total.values())
    st.markdown("**全体**")
    if denom3_all == 0:
        st.markdown("全体：データ不足")
    else:
        tri_rows_all = []
        for i in range(1,6):
            for j in range(i+1,7):
                for k in range(j+1,8):
                    cnt = trio_counts_total.get((i,j,k), 0)
                    if cnt>0:
                        tri_rows_all.append({"トリオ": f"{{{i},{j},{k}}}", "件数": cnt, "構成比%": round(100*cnt/denom3_all,1)})
        df_tri_all = pd.DataFrame(tri_rows_all).sort_values(["件数"], ascending=False)
        st.dataframe(df_tri_all, use_container_width=True, hide_index=True)

    st.divider()
    # 5) モード指標（高番手/穴）
    st.subheader("開催日別：モード指標（高番手(1–4)/穴(5–7)ペア率）")
    mode_rows = []
    for day in DAY_OPTIONS:
        denom_pairs = sum(v for (d, i, j), v in pair_counts.items() if d == day)
        high = sum(v for (d, i, j), v in pair_counts.items() if d == day and i <= 4 and j <= 4)
        hole = sum(v for (d, i, j), v in pair_counts.items() if d == day and (i >= 5 or j >= 5))
        mode_rows.append({
            "開催日": day,
            "高番手(1–4)ペア率%": round(100*high/denom_pairs,1) if denom_pairs>0 else None,
            "穴(5–7)絡み率%": round(100*hole/denom_pairs,1) if denom_pairs>0 else None,
            "分母(ペア)": denom_pairs,
        })
    st.dataframe(pd.DataFrame(mode_rows), use_container_width=True, hide_index=True)

    # 全体
    denom_pairs_all = sum(pair_counts_total.values())
    high_all = sum(v for (i, j), v in pair_counts_total.items() if i <= 4 and j <= 4)
    hole_all = sum(v for (i, j), v in pair_counts_total.items() if (i >= 5 or j >= 5))
    mode_total = pd.DataFrame([{
        "集計": "全体",
        "高番手(1–4)ペア率%": round(100*high_all/denom_pairs_all,1) if denom_pairs_all>0 else None,
        "穴(5–7)絡み率%": round(100*hole_all/denom_pairs_all,1) if denom_pairs_all>0 else None,
        "分母(ペア)": denom_pairs_all,
    }])
    st.dataframe(mode_total, use_container_width=True, hide_index=True)
