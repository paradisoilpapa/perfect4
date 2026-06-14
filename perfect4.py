import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="二車複・二車単 必要オッズ表", layout="wide")

st.title("二車複・二車単 必要オッズ表")
st.caption(
    "ヴェロビ評価順を入力して、評価順位ベースの二車複・二車単必要オッズを車番に変換します。"
    "必要オッズは、総数394 ÷ 回数で計算します。"
)

TOTAL_N = 394

# 2車単の実回数表
# 行：1着の評価順位
# 列：2着の評価順位
EXACTA_COUNT = {
    1: {2: 48, 3: 31, 4: 22, 5: 8, 6: 8, 7: 3},
    2: {1: 37, 3: 21, 4: 16, 5: 13, 6: 7, 7: 8},
    3: {1: 17, 2: 14, 4: 14, 5: 11, 6: 10, 7: 1},
    4: {1: 16, 2: 11, 3: 10, 5: 7, 6: 2, 7: 1},
    5: {1: 10, 2: 7, 3: 8, 4: 4, 6: 3, 7: 2},
    6: {1: 12, 2: 5, 3: 3, 4: 3, 5: 3, 7: 1},
    7: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 0},
}


def normalize_rank_text(text: str) -> list[str]:
    """評価順テキストから1〜7の車番を抽出する。例: '2715364' -> ['2','7','1','5','3','6','4']"""
    nums = re.findall(r"[1-7]", text or "")
    if len(nums) != 7 or len(set(nums)) != 7:
        return []
    return nums


def exacta_count(first_rank: int, second_rank: int) -> int:
    """評価順位ベースの2車単回数"""
    if first_rank == second_rank:
        return 0
    return EXACTA_COUNT.get(first_rank, {}).get(second_rank, 0)


def quinella_count(rank_a: int, rank_b: int) -> int:
    """評価順位ベースの2車複回数。双方向合算。"""
    return exacta_count(rank_a, rank_b) + exacta_count(rank_b, rank_a)


def hit_rate_from_count(count: int) -> float:
    """総数394に対する的中率%"""
    return count / TOTAL_N * 100 if count > 0 else 0.0


def required_odds_from_count(count: int) -> float | None:
    """損益分岐オッズ。期待値100に必要なオッズ。"""
    if count <= 0:
        return None
    return TOTAL_N / count


def fmt_rate(count: int) -> str:
    return f"{hit_rate_from_count(count):.2f}%" if count > 0 else "0.00%"


def fmt_odds(count: int) -> str:
    odds = required_odds_from_count(count)
    return f"{odds:.2f}倍" if odds is not None else "—"


def make_quinella_base_table() -> pd.DataFrame:
    """基準となる2車複必要オッズ表。評価1位軸・評価2位軸のみ。"""
    pairs = []

    for b in range(2, 8):
        pairs.append((1, b))

    for b in range(3, 8):
        pairs.append((2, b))

    rows = []
    for a, b in pairs:
        count = quinella_count(a, b)
        rows.append({
            "評価ペア": f"評価{a}-{b}",
            "回数": count,
            "的中率": fmt_rate(count),
            "必要オッズ": fmt_odds(count),
        })

    return pd.DataFrame(rows)


def make_exacta_base_table() -> pd.DataFrame:
    """基準となる2車単必要オッズ表。評価1位頭・評価2位頭を中心に表示。"""
    pairs = []

    # 評価1位 → 評価2〜7位
    for b in range(2, 8):
        pairs.append((1, b))

    # 評価2位 → 評価1位、評価3〜7位
    pairs.append((2, 1))
    for b in range(3, 8):
        pairs.append((2, b))

    rows = []
    for a, b in pairs:
        count = exacta_count(a, b)
        rows.append({
            "評価方向": f"評価{a}→{b}",
            "回数": count,
            "的中率": fmt_rate(count),
            "必要オッズ": fmt_odds(count),
        })

    return pd.DataFrame(rows)


def make_quinella_axis_tables(cars: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """入力された評価順を車番に変換した2車複表"""
    rank1_car = cars[0]
    rank2_car = cars[1]

    rank1_rows = []
    for rank_b in range(2, 8):
        himo = cars[rank_b - 1]
        count = quinella_count(1, rank_b)
        rank1_rows.append({
            "買い目": f"{rank1_car}={himo}",
            "評価ペア": f"評価1-{rank_b}",
            "回数": count,
            "的中率": fmt_rate(count),
            "必要オッズ": fmt_odds(count),
            "_ヒモ車番": int(himo),
        })

    rank2_rows = []
    for rank_b in range(3, 8):
        himo = cars[rank_b - 1]
        count = quinella_count(2, rank_b)
        rank2_rows.append({
            "買い目": f"{rank2_car}={himo}",
            "評価ペア": f"評価2-{rank_b}",
            "回数": count,
            "的中率": fmt_rate(count),
            "必要オッズ": fmt_odds(count),
            "_ヒモ車番": int(himo),
        })

    rank1_df = (
        pd.DataFrame(rank1_rows)
        .sort_values("_ヒモ車番")
        .drop(columns=["_ヒモ車番"])
    )

    rank2_df = (
        pd.DataFrame(rank2_rows)
        .sort_values("_ヒモ車番")
        .drop(columns=["_ヒモ車番"])
    )

    return rank1_df, rank2_df


def make_exacta_axis_tables(cars: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """入力された評価順を車番に変換した2車単表"""
    rank1_car = cars[0]
    rank2_car = cars[1]

    # 評価1位頭
    rank1_rows = []
    for rank_b in range(2, 8):
        tail = cars[rank_b - 1]
        count = exacta_count(1, rank_b)
        rank1_rows.append({
            "買い目": f"{rank1_car}-{tail}",
            "評価方向": f"評価1→{rank_b}",
            "回数": count,
            "的中率": fmt_rate(count),
            "必要オッズ": fmt_odds(count),
            "_ヒモ車番": int(tail),
        })

    # 評価2位頭
    # 評価2→1も含める
    rank2_rows = []

    tail_rank_list = [1, 3, 4, 5, 6, 7]

    for rank_b in tail_rank_list:
        tail = cars[rank_b - 1]
        count = exacta_count(2, rank_b)
        rank2_rows.append({
            "買い目": f"{rank2_car}-{tail}",
            "評価方向": f"評価2→{rank_b}",
            "回数": count,
            "的中率": fmt_rate(count),
            "必要オッズ": fmt_odds(count),
            "_ヒモ車番": int(tail),
        })

    rank1_df = (
        pd.DataFrame(rank1_rows)
        .sort_values("_ヒモ車番")
        .drop(columns=["_ヒモ車番"])
    )

    rank2_df = (
        pd.DataFrame(rank2_rows)
        .sort_values("_ヒモ車番")
        .drop(columns=["_ヒモ車番"])
    )

    return rank1_df, rank2_df


st.subheader("基準：二車複 必要オッズ表")
st.caption("二車複は、評価順位同士の双方向合算です。例：評価1-2 = 評価1→2 + 評価2→1。")
st.dataframe(make_quinella_base_table(), use_container_width=True, hide_index=True)

st.subheader("基準：二車単 必要オッズ表")
st.caption("二車単は方向別です。例：評価1→2 と 評価2→1 は別物です。")
st.dataframe(make_exacta_base_table(), use_container_width=True, hide_index=True)

st.divider()

st.subheader("評価順を入力して計算")

rank_text = st.text_input("ヴェロビ評価順（例：2715364）", value="", placeholder="2715364")
calc = st.button("計算", type="primary")

if calc:
    cars = normalize_rank_text(rank_text)

    if not cars:
        st.error("1〜7の車番を重複なく7つ入力してください。例：2715364")
        st.stop()

    q_rank1_df, q_rank2_df = make_quinella_axis_tables(cars)
    e_rank1_df, e_rank2_df = make_exacta_axis_tables(cars)

    st.success(f"評価順：{' → '.join(cars)}")

    st.markdown("## 二車複 必要オッズ")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### 評価1位軸：{cars[0]}")
        st.dataframe(q_rank1_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown(f"### 評価2位軸：{cars[1]}")
        st.dataframe(q_rank2_df, use_container_width=True, hide_index=True)

    st.markdown("## 二車単 必要オッズ")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"### 評価1位頭：{cars[0]}")
        st.dataframe(e_rank1_df, use_container_width=True, hide_index=True)

    with col4:
        st.markdown(f"### 評価2位頭：{cars[1]}")
        st.dataframe(e_rank2_df, use_container_width=True, hide_index=True)

    st.info(
        "二車複は評価順位ペアの期待値確認用。"
        "二車単は評価上位が頭になる方向の上乗せ確認用。"
        "実オッズが必要オッズを超えている買い目だけを買い候補にします。"
    )

else:
    st.info("評価順を入力して『計算』を押してください。")
