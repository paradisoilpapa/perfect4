# streamlit run app.py
import io
from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="基礎見積（属人化防止版）", layout="wide")

# =========================
# 外部マスター（CSV）読込
# =========================
@st.cache_data
def load_master(path: str = "unit_prices.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    # 必須列: 区分, 品目, 単位, 単価, 備考
    need = {"区分","品目","単位","単価"}
    if not need.issubset(df.columns):
        raise ValueError(f"unit_prices.csv に列 {need} が必要です")
    return df

MASTER = load_master()

def price_of(item: str) -> float:
    row = MASTER.loc[MASTER["品目"] == item]
    return float(row["単価"].iloc[0]) if not row.empty else 0.0

# =========================
# モデル
# =========================
@dataclass
class InputsCommon:
    perimeter: float   # 周長 m
    base_t: float      # ベース厚 m
    up_h: float        # 立上り高さ m
    up_t: float        # 立上り厚 m

@dataclass
class InputsRaft:      # ベタ
    area: float        # スラブ面積 m2
    slab_t: float      # スラブ厚 m
    up_h: float        # 基礎梁(立上り)高さ m
    up_t: float        # 基礎梁(立上り)厚 m
    beam_len: float    # 梁延長 m（周長相当・グリッド合計など）

@dataclass
class InputsFooting:   # 独立
    n: int             # 基礎個数
    bx: float          # 基礎平面（X） m
    by: float          # 基礎平面（Y） m
    t: float           # 厚さ m
    up_h: float        # 柱型枠高さ m（必要なら）
    up_t: float        # 柱型枠厚 m（必要なら）

# 係数（社内規定で後からCSV化可）
REBAR_RATIO_RC   = 0.012   # 鉄筋比(1.2%)
STEEL_DENSITY    = 7850    # kg/m3
LABOR_PER_M3     = 0.25    # 人工/㎥（目安）
FORM_BOTH_SIDES  = True    # 型枠は基本両面

# ==============
# 数量ロジック
# ==============
def qty_strip_foundation(inp: InputsCommon) -> Dict[str, float]:
    """布基礎（ベース＋立上り）"""
    vol_base = inp.perimeter * inp.base_t * inp.up_t * 0 + inp.perimeter * inp.base_t * 1.0  # 誤入力防止
    vol_base = inp.perimeter * inp.base_t * (0.60)  # 幅は単価側に持たない場合、ここで指定（必要ならUIに幅を出す）
    # →幅を入力にしたい場合はUIで base_w を追加し、 vol_base = perimeter * base_w * base_t に置換

    vol_up   = inp.perimeter * inp.up_h * inp.up_t
    vol      = vol_base + vol_up

    form = inp.perimeter * inp.up_h * (2 if FORM_BOTH_SIDES else 1)
    rebar = vol * REBAR_RATIO_RC * STEEL_DENSITY
    labor = vol * LABOR_PER_M3
    return {
        "コンクリ(m3)": vol,
        "型枠(m2)": form,
        "鉄筋(kg)": rebar,
        "人工(人)": labor,
    }

def qty_raft(inp: InputsRaft) -> Dict[str, float]:
    """ベタ基礎（スラブ＋立上り梁）"""
    vol_slab = inp.area * inp.slab_t
    vol_beam = inp.beam_len * inp.up_h * inp.up_t
    vol      = vol_slab + vol_beam

    form = inp.beam_len * inp.up_h * (2 if FORM_BOTH_SIDES else 1)
    rebar = vol * REBAR_RATIO_RC * STEEL_DENSITY
    labor = vol * LABOR_PER_M3
    return {
        "コンクリ(m3)": vol,
        "型枠(m2)": form,
        "鉄筋(kg)": rebar,
        "人工(人)": labor,
    }

def qty_footing(inp: InputsFooting) -> Dict[str, float]:
    """独立基礎（n個）"""
    vol1 = inp.bx * inp.by * inp.t
    vol  = vol1 * inp.n

    # 側面型枠（4面×周長×高さ）
    form1 = 2*(inp.bx + inp.by) * inp.t * (1 if not FORM_BOTH_SIDES else 2/2)  # 独立基礎は外周一発なので片面扱いでもOK
    form  = form1 * inp.n

    rebar = vol * REBAR_RATIO_RC * STEEL_DENSITY
    labor = vol * LABOR_PER_M3
    return {
        "コンクリ(m3)": vol,
        "型枠(m2)": form,
        "鉄筋(kg)": rebar,
        "人工(人)": labor,
    }

# =========
# UI
# =========
st.title("基礎見積（独立／ベタ／布）— 属人化防止テンプレ")
st.caption("数量ロジックは型ごとの関数に分離・単価はCSV外部化。新人は値を入れるだけ。")

type_sel = st.selectbox("基礎タイプを選択", ["布（立上り＋ベース）", "ベタ", "独立"])

tax_rate   = st.number_input("消費税率(%)", value=10.0, step=0.1)
profit_rt  = st.number_input("利益率(販売=原価×(1+利益率))", value=0.20, step=0.01, min_value=0.0)
round_to_k = st.checkbox("最終金額を千円単位で丸める", value=True)

colL, colR = st.columns([1.2, 1])

# =========
# 入力パネル
# =========
with colL:
    if type_sel == "布（立上り＋ベース）":
        st.subheader("入力（布基礎）")
        perimeter = st.number_input("周長 L (m)", value=40.0, step=0.1, min_value=0.0)
        base_t    = st.number_input("ベース厚 t_base (m)", value=0.15, step=0.01, min_value=0.0)
        up_h      = st.number_input("立上り高さ h_up (m)", value=0.5, step=0.01, min_value=0.0)
        up_t      = st.number_input("立上り厚 t_up (m)", value=0.12, step=0.01, min_value=0.0)
        # 幅を固定せず入力にしたい場合 → ここに base_w 追加して qty関数を調整
        inp = InputsCommon(perimeter, base_t, up_h, up_t)
        qty = qty_strip_foundation(inp)

    elif type_sel == "ベタ":
        st.subheader("入力（ベタ基礎）")
        area   = st.number_input("スラブ面積 A (m²)", value=64.0, step=0.5, min_value=0.0)
        slab_t = st.number_input("スラブ厚 t_slab (m)", value=0.15, step=0.01, min_value=0.0)
        up_h   = st.number_input("基礎梁高さ h_beam (m)", value=0.45, step=0.01, min_value=0.0)
        up_t   = st.number_input("基礎梁厚 t_beam (m)", value=0.12, step=0.01, min_value=0.0)
        beamL  = st.number_input("梁延長 (m)（外周＋内部グリッド合計）", value=40.0, step=0.1, min_value=0.0)
        inp = InputsRaft(area, slab_t, up_h, up_t, beamL)
        qty = qty_raft(inp)

    else:  # 独立
        st.subheader("入力（独立基礎）")
        n  = st.number_input("個数 n", value=8, step=1, min_value=0)
        bx = st.number_input("平面 X (m)", value=0.9, step=0.01, min_value=0.0)
        by = st.number_input("平面 Y (m)", value=0.9, step=0.01, min_value=0.0)
        t  = st.number_input("厚さ t (m)", value=0.4, step=0.01, min_value=0.0)
        up_h = st.number_input("（任意）柱型枠高さ h (m)", value=0.0, step=0.01, min_value=0.0)
        up_t = st.number_input("（任意）柱型枠厚 t (m)", value=0.0, step=0.01, min_value=0.0)
        inp = InputsFooting(int(n), bx, by, t, up_h, up_t)
        qty = qty_footing(inp)

# =========
# 見積計算・出力
# =========
def build_df(qty: Dict[str, float]) -> Tuple[pd.DataFrame, float, float, float, float]:
    rows = []
    for item, q in qty.items():
        unit_price = price_of(item)
        amount = q * unit_price
        rows.append([item, q, MASTER.loc[MASTER["品目"]==item, "単位"].iloc[0] if not MASTER.loc[MASTER["品目"]==item].empty else "", unit_price, amount])
    df = pd.DataFrame(rows, columns=["品目","数量","単位","単価(円)","金額(円)"])
    cost_subtotal = float(df["金額(円)"].sum())
    sales = cost_subtotal * (1.0 + profit_rt)
    tax   = sales * (tax_rate / 100.0)
    total = sales + tax
    if round_to_k:
        total = np.rint(total/1000)*1000
    return df, cost_subtotal, sales, tax, total

df, cost_sub, sales, tax, total = build_df(qty)

with colR:
    st.subheader("合計")
    st.metric("原価小計", f"{cost_sub:,.0f} 円")
    st.metric("販売（税別）", f"{sales:,.0f} 円")
    st.metric("消費税", f"{tax:,.0f} 円")
    st.metric("税込合計", f"{total:,.0f} 円")

st.subheader("明細")
st.dataframe(df.style.format({"数量":"{:.3f}","単価(円)":"{:.0f}","金額(円)":"{:.0f}"}), use_container_width=True)

# Excel出力
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
    df.to_excel(xw, sheet_name="明細", index=False)
    pd.DataFrame([
        ["原価小計", cost_sub],
        ["販売（税別）", sales],
        ["消費税", tax],
        ["税込合計", total],
    ], columns=["項目","金額(円)"]).to_excel(xw, sheet_name="合計", index=False)
st.download_button("Excelをダウンロード", buf.getvalue(), file_name="foundation_estimate.xlsx")
