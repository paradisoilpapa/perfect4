# -*- coding: utf-8 -*-

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ復習｜2車複集計版", layout="wide")
st.title("ヴェロビ 復習（全体累積）｜2車複・評価分布 集計版")

FIELD_SIZE = 7
WINNER_RANKS = tuple(range(1, FIELD_SIZE + 1))

# 個別2車複 引継ぎ用累積表の対象。
# 既存の1・2軸に、評価3・4軸の下位絡みを追加。
NISHAFUKU_PAIRS: List[Tuple[int, int]] = [
    (1, 2), (1, 3), (1, 4),
    (1, 5), (1, 6), (1, 7),
    (2, 3), (2, 4),
    (2, 5), (2, 6), (2, 7),
    (3, 4), (3, 5), (3, 6), (3, 7),
    (4, 5), (4, 6), (4, 7),
]

PairKey = Tuple[int, int]


def rank_symbol(r: int) -> str:
    return f"評価{int(r)}"


def nishafuku_label(a: int, b: int) -> str:
    a, b = sorted((int(a), int(b)))
    return f"2車複 {a}-{b}"


def new_payout_rec() -> Dict[str, int]:
    # Z10/Z20/Z20P は「的中した2車複払戻」の倍率帯別本数。
    # Z10   : 10.0倍以下
    # Z20   : 10.1〜20.0倍
    # Z20P  : 20.1倍以上
    return {"N": 0, "KSUM": 0, "H": 0, "SUM": 0, "Z10": 0, "Z20": 0, "Z20P": 0}


def add_rec(dst: Dict[str, int], src: Dict[str, int]) -> None:
    for k in ("N", "KSUM", "H", "SUM", "Z10", "Z20", "Z20P"):
        dst[k] = int(dst.get(k, 0)) + int(src.get(k, 0))


def parse_rankline(s: str, expected_len: int) -> List[str]:
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    if not s.isdigit() or len(s) != expected_len:
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


def rate(x: int, n: int):
    return round(100.0 * x / n, 1) if n > 0 else None


def ksum_nishafuku_pair(a: int, b: int, field_n: int) -> int:
    if field_n < 2:
        return 0
    if a == b:
        return 0
    if a > field_n or b > field_n:
        return 0
    return 1


def hit_nishafuku_pair(a: int, b: int, win_rank: int, sec_rank: int, field_n: int) -> bool:
    if ksum_nishafuku_pair(a, b, field_n) <= 0:
        return False
    return {int(win_rank), int(sec_rank)} == {int(a), int(b)}


def payout_zone_key(pay: int) -> str | None:
    """2車複払戻（100円あたり）を的中ゾーンへ分類する。"""
    try:
        pay = int(pay)
    except Exception:
        return None
    if pay <= 0:
        return None
    odds = pay / 100.0
    if odds <= 10.0:
        return "Z10"
    if odds <= 20.0:
        return "Z20"
    return "Z20P"


def zone_text(count: int, total_h: int) -> str:
    """例：7/70.0% の表示。"""
    count = int(count or 0)
    total_h = int(total_h or 0)
    if total_h <= 0:
        return "0/0%"
    return f"{count}/{round(100.0 * count / total_h, 1)}%"


def build_conditional_tables(pair_counts: Dict[PairKey, int], left_label: str, col_prefix: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = list(range(1, FIELD_SIZE + 1))
    count_rows = []
    pct_rows = []

    for wr in WINNER_RANKS:
        total = 0
        for rr in cols:
            if rr == wr:
                continue
            total += int(pair_counts.get((wr, rr), 0))

        row_c = {left_label: wr, "N": total}
        row_p = {left_label: wr, "N": total}

        for rr in cols:
            col = f"{col_prefix}{rr}"
            if rr == wr:
                row_c[col] = None
                row_p[col] = None
            else:
                v = int(pair_counts.get((wr, rr), 0))
                row_c[col] = v
                row_p[col] = round(100.0 * v / total, 1) if total > 0 else 0.0

        count_rows.append(row_c)
        pct_rows.append(row_p)

    return pd.DataFrame(count_rows), pd.DataFrame(pct_rows)


def payout_row(label: str, rec: Dict[str, int]) -> Dict:
    N = int(rec.get("N", 0))
    KSUM = int(rec.get("KSUM", 0))
    H = int(rec.get("H", 0))
    SUM = int(rec.get("SUM", 0))
    invest = KSUM * 100
    z10 = int(rec.get("Z10", 0))
    z20 = int(rec.get("Z20", 0))
    z20p = int(rec.get("Z20P", 0))
    zsum = z10 + z20 + z20p
    return {
        "型": label,
        "対象N": N,
        "総点数KSUM": KSUM,
        "投資額換算": invest,
        "払戻合計SUM": SUM,
        "的中H": H,
        "的中率%": rate(H, N),
        "平均配当": round(SUM / H, 1) if H > 0 else None,
        "回収率%": round(100.0 * SUM / invest, 1) if invest > 0 else None,
    }


def zone_row(pair: str, rec: Dict[str, int]) -> Dict:
    """個別2車複の的中配当ゾーンを、累積表とは別表で表示する。"""
    H = int(rec.get("H", 0))
    z10 = int(rec.get("Z10", 0))
    z20 = int(rec.get("Z20", 0))
    z20p = int(rec.get("Z20P", 0))
    zsum = z10 + z20 + z20p
    return {
        "ペア": pair,
        "的中H": H,
        "〜10倍": zone_text(z10, H),
        "10.1〜20倍": zone_text(z20, H),
        "20.1倍〜": zone_text(z20p, H),
        "〜10本数": z10,
        "10.1〜20本数": z20,
        "20.1〜本数": z20p,
        "ゾーン確認": "OK" if (H == 0 or zsum == H) else f"不一致({zsum}/{H})",
    }


def table_auto_height(df: pd.DataFrame, row_px: int = 35, header_px: int = 38, pad_px: int = 12, min_px: int = 120) -> int:
    """行数に合わせてdataframeの高さを出す。縦スクロールを出しにくくする。"""
    if df is None:
        return min_px
    try:
        n = max(1, len(df))
    except Exception:
        n = 1
    return max(min_px, int(header_px + row_px * n + pad_px))


def render_table(df: pd.DataFrame, height: int | None = None) -> None:
    if df is None or df.empty:
        st.info("表示するデータがありません。")
        return

    # height=Noneを渡すとCloud環境でエラーになることがある。
    # さらに、デフォルト表示だと表の中に縦スクロールが出るため、
    # 行数から高さを自動計算して全行を見せる。
    h = table_auto_height(df) if height is None else int(height)
    st.dataframe(df, use_container_width=True, hide_index=True, height=h)


tabs = st.tabs(["日次手入力", "前日までの集計", "分析結果"])

byrace_rows: List[Dict] = []

# 前日までの手入力保持用
pair12_manual: Dict[PairKey, int] = defaultdict(int)
pair13_manual: Dict[PairKey, int] = defaultdict(int)
agg_rank_manual: Dict[int, Dict[str, int]] = defaultdict(lambda: {"N": 0, "C1": 0, "C2": 0, "C3": 0})
agg_payout_nishafuku_manual: Dict[str, Dict[str, int]] = {
    nishafuku_label(a, b): new_payout_rec() for a, b in NISHAFUKU_PAIRS
}

# =========================
# A. 日次手入力
# =========================
with tabs[0]:
    st.subheader("日次手入力（7車ベース・欠車対応・最大100R）")
    st.caption("V評価は頭数ぶんの桁数で入力。着順は3桁まで。2車複払戻のみ入力します。")

    with st.form("daily_input_form"):
        cols_hdr = st.columns([0.7, 0.8, 2.8, 1.0, 1.0])
        cols_hdr[0].markdown("**R**")
        cols_hdr[1].markdown("**頭数**")
        cols_hdr[2].markdown("**V評価（頭数ぶん）**")
        cols_hdr[3].markdown("**着順(〜3桁)**")
        cols_hdr[4].markdown("**2車複払戻**")

        daily_inputs = []
        for i in range(1, 101):
            c1, c2, c3, c4, c5 = st.columns([0.7, 0.8, 2.8, 1.0, 1.0])
            rid = c1.text_input("", key=f"rid_{i}", value=str(i))
            field_n = c2.selectbox("", options=[7, 6, 5], index=0, key=f"field_n_{i}")
            vline = c3.text_input("", key=f"vline_{i}", value="")
            fin = c4.text_input("", key=f"fin_{i}", value="")
            pay_2f = c5.number_input("", key=f"pay2f_{i}", min_value=0, value=0, step=10)
            daily_inputs.append({"rid": rid, "field_n": field_n, "vline": vline, "fin": fin, "pay_2f": pay_2f})

        st.form_submit_button("日次入力を反映")

    for item in daily_inputs:
        rid = item["rid"]
        field_n = int(item["field_n"])
        vorder = parse_rankline(item["vline"], field_n)
        finish = parse_finish(item["fin"])
        pay_2f = int(item["pay_2f"])

        any_input = bool(item["vline"].strip() or item["fin"].strip() or pay_2f > 0)
        if any_input and not vorder:
            st.warning(f"R{rid}: 頭数{field_n}なので、V評価は{field_n}桁で入力してください。")
            continue
        if any_input:
            invalid_finish = [x for x in finish if x not in set(vorder)]
            if invalid_finish:
                st.warning(f"R{rid}: 着順 {''.join(invalid_finish)} がV評価に含まれていません。")
            byrace_rows.append({"race": rid, "field_n": field_n, "vorder": vorder, "finish": finish, "pay_2f": pay_2f})

# =========================
# B. 前日までの集計
# =========================
with tabs[1]:
    st.subheader("前日までの集計（累積・全体）")
    st.caption("必要な3表だけ入力します。1→2、1→3、評価別入賞、個別2車複引継ぎ。")

    with st.form("prev_aggregate_form"):
        cols_all = list(range(1, FIELD_SIZE + 1))

        st.markdown("## 1→2 着評価分布（累積・回数）")
        h = st.columns([1.8] + [1] * len(cols_all))
        h[0].markdown("**1着評価**")
        for j, rr in enumerate(cols_all, start=1):
            h[j].markdown(f"**2着={rr}**")
        pair12_inputs = []
        for wr in WINNER_RANKS:
            row_cols = st.columns([1.8] + [1] * len(cols_all))
            row_cols[0].write(f"評価{wr}が1着")
            for j, rr in enumerate(cols_all, start=1):
                if rr == wr:
                    row_cols[j].write("")
                    continue
                v = row_cols[j].number_input("", key=f"pair12_prev_wr{wr}_rr{rr}", min_value=0, value=0)
                pair12_inputs.append((wr, rr, int(v)))

        st.divider()

        st.markdown("## 1→3 着評価分布（累積・回数）")
        h = st.columns([1.8] + [1] * len(cols_all))
        h[0].markdown("**1着評価**")
        for j, rr in enumerate(cols_all, start=1):
            h[j].markdown(f"**3着={rr}**")
        pair13_inputs = []
        for wr in WINNER_RANKS:
            row_cols = st.columns([1.8] + [1] * len(cols_all))
            row_cols[0].write(f"評価{wr}が1着")
            for j, rr in enumerate(cols_all, start=1):
                if rr == wr:
                    row_cols[j].write("")
                    continue
                v = row_cols[j].number_input("", key=f"pair13_prev_wr{wr}_rr{rr}", min_value=0, value=0)
                pair13_inputs.append((wr, rr, int(v)))

        st.divider()

        st.markdown("## 評価別 入賞回数（累積）")
        hdr = st.columns([1.5, 1, 1, 1, 1])
        hdr[0].markdown("**評価**")
        hdr[1].markdown("**出走数N**")
        hdr[2].markdown("**1着**")
        hdr[3].markdown("**2着**")
        hdr[4].markdown("**3着**")
        rank_inputs = []
        for r in range(1, FIELD_SIZE + 1):
            c0, c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1, 1])
            c0.write(rank_symbol(r))
            N = c1.number_input("", key=f"aggN_{r}", min_value=0, value=0)
            C1 = c2.number_input("", key=f"aggC1_{r}", min_value=0, value=0)
            C2 = c3.number_input("", key=f"aggC2_{r}", min_value=0, value=0)
            C3 = c4.number_input("", key=f"aggC3_{r}", min_value=0, value=0)
            rank_inputs.append((r, int(N), int(C1), int(C2), int(C3)))

        st.divider()

        st.markdown("## 個別2車複 引継ぎ用累積表")
        st.caption("ここは基本集計だけ。的中ゾーンは下の独立入力に分けます。")
        h = st.columns([1.5, 0.8, 1, 0.8])
        h[0].markdown("**2車複**")
        h[1].markdown("**対象N**")
        h[2].markdown("**払戻SUM**")
        h[3].markdown("**的中H**")
        nishafuku_basic_inputs = []
        for a, b in NISHAFUKU_PAIRS:
            label = nishafuku_label(a, b)
            c0, c1, c2, c3 = st.columns([1.5, 0.8, 1, 0.8])
            c0.write(label)
            N = c1.number_input("", key=f"nf_prev_N_{a}_{b}", min_value=0, value=0)
            SUM = c2.number_input("", key=f"nf_prev_SUM_{a}_{b}", min_value=0, value=0, step=10)
            H = c3.number_input("", key=f"nf_prev_H_{a}_{b}", min_value=0, value=0)
            nishafuku_basic_inputs.append((label, int(N), int(SUM), int(H)))

        st.markdown("## 個別2車複 的中ゾーン入力")
        st.caption("的中した2車複の配当帯だけを入力。累積表とは別管理・別表示にします。")
        hz = st.columns([1.5, 0.9, 0.9, 0.9])
        hz[0].markdown("**2車複**")
        hz[1].markdown("**〜10倍**")
        hz[2].markdown("**10.1〜20**")
        hz[3].markdown("**20.1〜**")
        nishafuku_zone_inputs = []
        for a, b in NISHAFUKU_PAIRS:
            label = nishafuku_label(a, b)
            c0, c1, c2, c3 = st.columns([1.5, 0.9, 0.9, 0.9])
            c0.write(label)
            Z10 = c1.number_input("", key=f"nf_prev_Z10_{a}_{b}", min_value=0, value=0)
            Z20 = c2.number_input("", key=f"nf_prev_Z20_{a}_{b}", min_value=0, value=0)
            Z20P = c3.number_input("", key=f"nf_prev_Z20P_{a}_{b}", min_value=0, value=0)
            nishafuku_zone_inputs.append((label, int(Z10), int(Z20), int(Z20P)))

        st.form_submit_button("前日までの集計を反映")

    for wr, rr, v in pair12_inputs:
        if v:
            pair12_manual[(wr, rr)] += int(v)

    for wr, rr, v in pair13_inputs:
        if v:
            pair13_manual[(wr, rr)] += int(v)

    for r, N, C1, C2, C3 in rank_inputs:
        if any([N, C1, C2, C3]):
            rec = agg_rank_manual[r]
            rec["N"] += N
            rec["C1"] += C1
            rec["C2"] += C2
            rec["C3"] += C3

    for label, N, SUM, H in nishafuku_basic_inputs:
        if any([N, SUM, H]) and label in agg_payout_nishafuku_manual:
            rec = agg_payout_nishafuku_manual[label]
            rec["N"] += N
            rec["KSUM"] += N
            rec["SUM"] += SUM
            rec["H"] += H

    for label, Z10, Z20, Z20P in nishafuku_zone_inputs:
        if any([Z10, Z20, Z20P]) and label in agg_payout_nishafuku_manual:
            rec = agg_payout_nishafuku_manual[label]
            rec["Z10"] += Z10
            rec["Z20"] += Z20
            rec["Z20P"] += Z20P

# =========================
# 集計：日次 + 前日まで累積
# =========================
rank_daily: Dict[int, Dict[str, int]] = {r: {"N": 0, "C1": 0, "C2": 0, "C3": 0} for r in range(1, FIELD_SIZE + 1)}
pair12_daily: Dict[PairKey, int] = defaultdict(int)
pair13_daily: Dict[PairKey, int] = defaultdict(int)
payout_nishafuku_daily: Dict[str, Dict[str, int]] = {nishafuku_label(a, b): new_payout_rec() for a, b in NISHAFUKU_PAIRS}

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    field_n = int(row.get("field_n", len(vorder) or 0))
    pay_2f = int(row.get("pay_2f", 0))
    if not vorder:
        continue

    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}

    for r in range(1, len(vorder) + 1):
        rank_daily[r]["N"] += 1
        car = vorder[r - 1]
        if len(finish) >= 1 and finish[0] == car:
            rank_daily[r]["C1"] += 1
        if len(finish) >= 2 and finish[1] == car:
            rank_daily[r]["C2"] += 1
        if len(finish) >= 3 and finish[2] == car:
            rank_daily[r]["C3"] += 1

    if len(finish) >= 2:
        win_rank = car_to_rank.get(finish[0])
        sec_rank = car_to_rank.get(finish[1])
        if win_rank is not None and sec_rank is not None:
            pair12_daily[(int(win_rank), int(sec_rank))] += 1
            for a, b in NISHAFUKU_PAIRS:
                label = nishafuku_label(a, b)
                ksum = ksum_nishafuku_pair(a, b, field_n)
                if ksum <= 0:
                    continue
                rec = payout_nishafuku_daily[label]
                rec["N"] += 1
                rec["KSUM"] += ksum
                if hit_nishafuku_pair(a, b, int(win_rank), int(sec_rank), field_n) and pay_2f > 0:
                    rec["H"] += 1
                    rec["SUM"] += pay_2f
                    zkey = payout_zone_key(pay_2f)
                    if zkey:
                        rec[zkey] += 1

    if len(finish) >= 3:
        win_rank = car_to_rank.get(finish[0])
        third_rank = car_to_rank.get(finish[2])
        if win_rank is not None and third_rank is not None:
            pair13_daily[(int(win_rank), int(third_rank))] += 1

rank_total: Dict[int, Dict[str, int]] = {r: {"N": 0, "C1": 0, "C2": 0, "C3": 0} for r in range(1, FIELD_SIZE + 1)}
for r in range(1, FIELD_SIZE + 1):
    for k in ("N", "C1", "C2", "C3"):
        rank_total[r][k] = int(rank_daily[r].get(k, 0)) + int(agg_rank_manual[r].get(k, 0))

pair12_total: Dict[PairKey, int] = defaultdict(int)
pair13_total: Dict[PairKey, int] = defaultdict(int)
for k, v in pair12_daily.items():
    pair12_total[k] += int(v)
for k, v in pair12_manual.items():
    pair12_total[k] += int(v)
for k, v in pair13_daily.items():
    pair13_total[k] += int(v)
for k, v in pair13_manual.items():
    pair13_total[k] += int(v)

payout_nishafuku_total: Dict[str, Dict[str, int]] = {nishafuku_label(a, b): new_payout_rec() for a, b in NISHAFUKU_PAIRS}
for label in payout_nishafuku_total:
    add_rec(payout_nishafuku_total[label], payout_nishafuku_daily[label])
    add_rec(payout_nishafuku_total[label], agg_payout_nishafuku_manual[label])

# =========================
# 出力：分析結果
# =========================
with tabs[2]:
    st.subheader("1→2 着評価分布（全体累積）｜1着が評価1〜7のとき（欠車対応）")
    df12_count, df12_pct = build_conditional_tables(pair12_total, "1着の評価", "2着=")
    st.markdown("### 回数（Nは条件付き総数）")
    render_table(df12_count)
    st.markdown("### 割合%（同評価セルは空欄）")
    render_table(df12_pct)

    st.divider()

    st.subheader("1→3 着評価分布（全体累積）｜1着が評価1〜7のとき（欠車対応）")
    df13_count, df13_pct = build_conditional_tables(pair13_total, "1着の評価", "3着=")
    st.markdown("### 回数（Nは条件付き総数）")
    render_table(df13_count)
    st.markdown("### 割合%（同評価セルは空欄）")
    render_table(df13_pct)

    st.divider()

    st.subheader("評価別 入賞テーブル（全体累積）｜欠車対応")
    rank_rows = []
    for r in range(1, FIELD_SIZE + 1):
        rec = rank_total[r]
        N, C1, C2, C3 = rec["N"], rec["C1"], rec["C2"], rec["C3"]
        rank_rows.append({
            "評価": rank_symbol(r),
            "出走数N": N,
            "1着回数": C1,
            "2着回数": C2,
            "3着回数": C3,
            "1着率%": rate(C1, N),
            "連対率%": rate(C1 + C2, N),
            "3着内率%": rate(C1 + C2 + C3, N),
        })
    render_table(pd.DataFrame(rank_rows))

    st.divider()

    st.subheader("個別2車複 引継ぎ用累積表")
    st.caption("3-4 / 3-5 / 3-6 / 3-7 / 4-5 / 4-6 / 4-7 を追加済み。ここは基本集計だけを表示します。")
    nf_rows = []
    zone_rows = []
    for a, b in NISHAFUKU_PAIRS:
        label = nishafuku_label(a, b)
        row = payout_row(label, payout_nishafuku_total[label])
        row["ペア"] = f"{a}-{b}"
        nf_rows.append(row)
        zone_rows.append(zone_row(f"{a}-{b}", payout_nishafuku_total[label]))
    df_nf = pd.DataFrame(nf_rows)
    cols = ["ペア", "型", "対象N", "総点数KSUM", "投資額換算", "払戻合計SUM", "的中H", "的中率%", "平均配当", "回収率%"]
    render_table(df_nf[[c for c in cols if c in df_nf.columns]])

    st.divider()

    st.subheader("個別2車複 的中ゾーン分布")
    st.caption("的中時の払戻倍率帯。累積表とは独立表示にして、文字が小さくならないように分けています。")
    df_zone = pd.DataFrame(zone_rows)
    zone_cols = ["ペア", "的中H", "〜10倍", "10.1〜20倍", "20.1倍〜", "ゾーン確認"]
    render_table(df_zone[[c for c in zone_cols if c in df_zone.columns]])
