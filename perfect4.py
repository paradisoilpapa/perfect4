# -*- coding: utf-8 -*-
# Streamlit: pip install streamlit pandas numpy xlsxwriter
import io
from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="基礎見積（独立/ベタ/布）", layout="wide")

# ===========
# 入力モデル
# ===========
@dataclass
class StripInput:     # 布基礎（立上り＋ベース）
    perimeter: float  # 周長 L [m]
    base_w: float     # ベース幅 B [m]
    base_t: float     # ベース厚 t_base [m]
    up_h: float       # 立上り高さ h_up [m]
    up_t: float       # 立上り厚 t_up [m]

@dataclass
class RaftInput:      # ベタ（スラブ＋基礎梁）
    slab_area: float  # スラブ面積 A [m2]
    slab_t: float     # スラブ厚 t_slab [m]
    beam_len: float   # 梁延長（外周＋内部グリッド）[m]
    beam_h: float     # 梁高さ [m]
    beam_t: float     # 梁厚（腹厚）[m]

@dataclass
class FootingInput:   # 独立基礎（同一形状×n）
    n: int            # 個数
    bx: float         # 平面寸法X [m]
    by: float         # 平面寸法Y [m]
    t: float          # 厚さ [m]

# =================
# 計算パラメータ
# =================
REBAR_RATIO = 0.012     # 鉄筋比 1.2%（体積×鉄筋比×比重）
STEEL_DENS  = 7850.0    # 鉄比重 kg/m3
LABOR_PER_M3 = 0.25     # 人工係数 [人/㎥]
FORM_BOTH_SIDES = True  # 型枠は両面想定

# =================
# 数量算定（厳密）
# =================
def qty_strip(inp: StripInput) -> Dict[str, float]:
    # 体積 = ベース(L×B×t) + 立上り(L×h×t_up)
    vol_base = inp.perimeter * inp.base_w * inp.base_t
    vol_up   = inp.perimeter * inp.up_h   * inp.up_t
    vol      = vol_base + vol_up
    # 型枠 = 立上り両面(L×h×2)  ※ベースは地中で型枠不要前提
    form = inp.perimeter * inp.up_h * (2 if FORM_BOTH_SIDES else 1)
    # 鉄筋・人工
    rebar = vol * REBAR_RATIO * STEEL_DENS
    labor = vol * LABOR_PER_M3
    return {"コンクリ(m3)": vol, "型枠(m2)": form, "鉄筋(kg)": rebar, "人工(人)": labor}

def qty_raft(inp: RaftInput) -> Dict[str, float]:
    vol_slab = inp.slab_area * inp.slab_t
    vol_beam = inp.beam_len * inp.beam_h * inp.beam_t
    vol      = vol_slab + vol_beam
    form     = inp.beam_len * inp.beam_h * (2 if FORM_BOTH_SIDES else 1)
    rebar    = vol * REBAR_RATIO * STEEL_DENS
    labor    = vol * LABOR_PER_M3
    return {"コンクリ(m3)": vol, "型枠(m2)": form, "鉄筋(kg)": rebar, "人工(人)": labor}

def qty_footing(inp: FootingInput) -> Dict[str, float]:
    vol1 = inp.bx * inp.by * inp.t
    vol  = vol1 * max(inp.n, 0)
    # 側面型枠（独立基礎は外周： (2*(bx+by))×t ）×個数
    form = (2*(inp.bx + inp.by) * inp.t) * max(inp.n, 0)
    rebar = vol * REBAR_RATIO * STEEL_DENS
    labor = vol * LABOR_PER_M3
    return {"コンクリ(m3)": vol, "型枠(m2)": form, "鉄筋(kg)": rebar, "人工(人)": labor}

# =================
# 単価（プレースホルダ）
# 0円でも動く。右側で一時変更可能。
# =================
DEFAULT_PRICES = pd.DataFrame([
    {"品目":"コンクリ(m3)","単位":"m3","単価":0},
    {"品目":"型枠(m2)","単位":"m2","単価":0},
    {"品目":"鉄筋(kg)","単位":"kg","単価":0},
    {"品目":"人工(人)","単位":"人","単価":0},
])

@st.cache_data
def get_master() -> pd.DataFrame:
    return DEFAULT_PRICES.copy()

MASTER = get_master()

def price_of(item: str) -> Tuple[str, float]:
    row = MASTER.loc[MASTER["品目"] == item]
    if row.empty:
        return "", 0.0
    return str(row["単位"].iloc[0]), float(row["単価"].iloc[0])

# =========
# UI
# =========
st.title("基礎見積（独立／ベタ／布）— 単価未設定でも動作")
left, right = st.columns([1.3, 1])

with left:
    typ = st.selectbox("基礎タイプ", ["布（立上り＋ベース）", "ベタ", "独立"])

    if typ == "布（立上り＋ベース）":
        L  = st.number_input("周長 L [m]", value=40.0, step=0.1, min_value=0.0)
        Bw = st.number_input("ベース幅 B [m]", value=0.60, step=0.01, min_value=0.0)
        Bt = st.number_input("ベース厚 t_base [m]", value=0.15, step=0.01, min_value=0.0)
        Uh = st.number_input("立上り高さ h_up [m]", value=0.50, step=0.01, min_value=0.0)
        Ut = st.number_input("立上り厚 t_up [m]", value=0.12, step=0.01, min_value=0.0)
        qty = qty_strip(StripInput(L, Bw, Bt, Uh, Ut))

    elif typ == "ベタ":
        A  = st.number_input("スラブ面積 A [m²]", value=64.0, step=0.5, min_value=0.0)
        Ts = st.number_input("スラブ厚 t_slab [m]", value=0.15, step=0.01, min_value=0.0)
        BL = st.number_input("梁延長（外周+内部）[m]", value=40.0, step=0.1, min_value=0.0)
        Bh = st.number_input("梁高さ [m]", value=0.45, step=0.01, min_value=0.0)
        Bt = st.number_input("梁厚（腹厚）[m]", value=0.12, step=0.01, min_value=0.0)
        qty = qty_raft(RaftInput(A, Ts, BL, Bh, Bt))

    else:
        n  = st.number_input("個数 n", value=8, step=1, min_value=0)
        bx = st.number_input("平面X [m]", value=0.90, step=0.01, min_value=0.0)
        by = st.number_input("平面Y [m]", value=0.90, step=0.01, min_value=0.0)
        t  = st.number_input("厚さ t [m]", value=0.40, step=0.01, min_value=0.0)
        qty = qty_footing(FootingInput(int(n), bx, by, t))

    st.subheader("数量（計）")
    qdf = pd.DataFrame(
        [{"品目":k, "数量":v} for k, v in qty.items()]
    )
    st.dataframe(qdf.style.format({"数量":"{:.3f}"}), use_container_width=True)

with right:
    st.subheader("単価（後で入れる想定）")
    # ここで一時的に単価を入れてもOK（未入力=0）
    master_edit = st.data_editor(
        MASTER, num_rows="fixed", use_container_width=True, key="unit_edit"
    )
    # 反映
    MASTER.update(master_edit)

    tax = st.number_input("消費税率(%)", value=10.0, step=0.1, min_value=0.0)
    profit = st.number_input("利益率(販売=原価×(1+利益率))", value=0.20, step=0.01, min_value=0.0)
    round_k = st.checkbox("税込合計を千円丸め", value=True)

# =========
# 見積計算（単価0でも可）
# =========
rows = []
for item, q in qty.items():
    unit, up = price_of(item)
    rows.append([item, q, unit, up, q*up])

df = pd.DataFrame(rows, columns=["品目","数量","単位","単価(円)","金額(円)"])
cost_sub = float(df["金額(円)"].sum())
sales = cost_sub * (1.0 + profit)
tax_amt = sales * (tax/100.0)
total = sales + tax_amt
if round_k:
    total = np.rint(total/1000.0)*1000.0

st.subheader("明細")
st.dataframe(df.style.format({"数量":"{:.3f}","単価(円)":"{:.0f}","金額(円)":"{:.0f}"}), use_container_width=True)

col1, col2, col3, col4 = st.columns(4)
col1.metric("原価小計", f"{cost_sub:,.0f} 円")
col2.metric("販売（税別）", f"{sales:,.0f} 円")
col3.metric("消費税", f"{tax_amt:,.0f} 円")
col4.metric("税込合計", f"{total:,.0f} 円")

# Excel出力（任意）
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
    df.to_excel(xw, sheet_name="明細", index=False)
    pd.DataFrame([
        ["原価小計", cost_sub],
        ["販売（税別）", sales],
        ["消費税", tax_amt],
        ["税込合計", total],
    ], columns=["項目","金額(円)"]).to_excel(xw, sheet_name="合計", index=False)
st.download_button("Excelダウンロード", buf.getvalue(), file_name="estimate_foundation.xlsx")
