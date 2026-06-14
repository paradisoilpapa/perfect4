import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="二車複 必要オッズ表", layout="wide")

st.title("二車複 必要オッズ表")
st.caption("ヴェロビ評価順を入力して、評価1位軸・評価2位軸の二車複必要オッズを車番に変換します。買い目はヒモ車番の若番順で表示します。")

# 評価順位ペアごとの過去的中率（%）
HIT_RATE = {
    "評価1-2": 21.6,
    "評価1-3": 12.2,
    "評価1-4": 9.7,
    "評価1-5": 4.6,
    "評価1-6": 3.1,
    "評価1-7": 1.0,
    "評価2-3": 8.9,
    "評価2-4": 6.9,
    "評価2-5": 5.1,
    "評価2-6": 3.1,
    "評価2-7": 2.3,
}


def required_odds(rate: float) -> float:
    """損益分岐オッズ。期待値100に必要なオッズ。"""
    return round(100.0 / rate, 2) if rate > 0 else 0.0


def normalize_rank_text(text: str) -> list[str]:
    """評価順テキストから1〜7の車番を抽出する。例: '2715364' -> ['2','7','1','5','3','6','4']"""
    nums = re.findall(r"[1-7]", text or "")
    if len(nums) != 7 or len(set(nums)) != 7:
        return []
    return nums


def make_base_table() -> pd.DataFrame:
    rows = []
    for label, rate in HIT_RATE.items():
        rows.append({
            "評価": label,
            "的中率": f"{rate:.1f}%",
            "必要オッズ": f"{required_odds(rate):.2f}倍",
        })
    return pd.DataFrame(rows)


def make_axis_tables(cars: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rank1_car = cars[0]
    rank2_car = cars[1]

    rank1_rows = []
    for rank_idx in range(1, 7):
        label = f"評価1-{rank_idx + 1}"
        rate = HIT_RATE[label]
        himo = cars[rank_idx]
        rank1_rows.append({
            "評価": label,
            "買い目": f"{rank1_car}={himo}",
            "必要オッズ": f"{required_odds(rate):.2f}倍",
            "_ヒモ車番": int(himo),
        })

    rank2_rows = []
    for rank_idx in range(2, 7):
        label = f"評価2-{rank_idx + 1}"
        rate = HIT_RATE[label]
        himo = cars[rank_idx]
        rank2_rows.append({
            "評価": label,
            "買い目": f"{rank2_car}={himo}",
            "必要オッズ": f"{required_odds(rate):.2f}倍",
            "_ヒモ車番": int(himo),
        })

    rank1_df = pd.DataFrame(rank1_rows).sort_values("_ヒモ車番").drop(columns=["_ヒモ車番"])
    rank2_df = pd.DataFrame(rank2_rows).sort_values("_ヒモ車番").drop(columns=["_ヒモ車番"])

    return rank1_df, rank2_df


# 2. 基準となる必要オッズ表は常時表示
st.subheader("基準となる必要オッズ表")
st.caption("この表の『評価1-2』などは、評価順位同士の組み合わせです。実車番は下の計算結果で変換します。")
st.dataframe(make_base_table(), use_container_width=True, hide_index=True)

st.divider()

st.subheader("評価順を入力して計算")
rank_text = st.text_input("ヴェロビ評価順（例：2715364）", value="", placeholder="2715364")
calc = st.button("計算", type="primary")

if calc:
    cars = normalize_rank_text(rank_text)

    if not cars:
        st.error("1〜7の車番を重複なく7つ入力してください。例：2715364")
        st.stop()

    rank1_df, rank2_df = make_axis_tables(cars)

    st.success(f"評価順：{' → '.join(cars)}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### 評価1位軸：{cars[0]}")
        st.dataframe(rank1_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown(f"### 評価2位軸：{cars[1]}")
        st.dataframe(rank2_df, use_container_width=True, hide_index=True)

    st.info("実オッズが必要オッズを超えている買い目だけを買い候補にします。買い目はヒモ車番の若番順です。")
else:
    st.info("評価順を入力して『計算』を押してください。")
