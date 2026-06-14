import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="二車複・二車単 必要オッズ表", layout="wide")

st.title("二車複・二車単 必要オッズ表")
st.caption(
    "ヴェロビ評価順を入力して、評価順位ベースの二車複・二車単必要オッズを車番に変換します。"
)

TOTAL_N = 394

# 行：1着評価順位
# 列：2着評価順位
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
    """
    評価順テキストから1〜7の車番を抽出する。
    例：2715364 → ['2', '7', '1', '5', '3', '6', '4']
    """
    nums = re.findall(r"[1-7]", text or "")
    if len(nums) != 7 or len(set(nums)) != 7:
        return []
    return nums


def exacta_count(first_rank: int, second_rank: int) -> int:
    """評価順位ベースの二車単回数"""
    if first_rank == second_rank:
        return 0
    return EXACTA_COUNT.get(first_rank, {}).get(second_rank, 0)


def quinella_count(rank_a: int, rank_b: int) -> int:
    """評価順位ベースの二車複回数。双方向合算。"""
    return exacta_count(rank_a, rank_b) + exacta_count(rank_b, rank_a)


def hit_rate_from_count(count: int) -> float:
    """総数に対する的中率%"""
    if count <= 0:
        return 0.0
    return count / TOTAL_N * 100


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


def max_rank_in_text(value: str) -> int:
    """
    評価1-5 / 評価2→4 などから最大評価順位を取り出す。
    """
    nums = re.findall(r"\d+", str(value))
    if not nums:
        return 99
    return max(int(n) for n in nums)


def highlight_rank_1_to_5(row):
    """
    評価1〜5位までの組み合わせ・方向に薄緑を付ける。
    評価6・7絡みは白のまま。
    """
    target_col = None

    if "評価ペア" in row.index:
        target_col = "評価ペア"
    elif "評価方向" in row.index:
        target_col = "評価方向"

    if target_col is None:
        return [""] * len(row)

    max_rank = max_rank_in_text(row[target_col])

    if max_rank <= 5:
        return ["background-color: #eaf7f0"] * len(row)

    return [""] * len(row)


def styled_df(df: pd.DataFrame):
    return df.style.apply(highlight_rank_1_to_5, axis=1)


def make_quinella_axis_tables(cars: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    入力された評価順を車番に変換した二車複表。
    買い目はヒモ車番の若番順。
    """
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
    """
    入力された評価順を車番に変換した二車単表。
    評価1位頭・評価2位頭を表示。
    買い目はヒモ車番の若番順。
    """
    rank1_car = cars[0]
    rank2_car = cars[1]

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

    rank2_rows = []
    for rank_b in [1, 3, 4, 5, 6, 7]:
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


st.subheader("評価順を入力して計算")

rank_text = st.text_input(
    "ヴェロビ評価順（例：2715364）",
    value="",
    placeholder="2715364",
)

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
        st.dataframe(
            styled_df(q_rank1_df),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.markdown(f"### 評価2位軸：{cars[1]}")
        st.dataframe(
            styled_df(q_rank2_df),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("## 二車単 必要オッズ")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"### 評価1位頭：{cars[0]}")
        st.dataframe(
            styled_df(e_rank1_df),
            use_container_width=True,
            hide_index=True,
        )

    with col4:
        st.markdown(f"### 評価2位頭：{cars[1]}")
        st.dataframe(
            styled_df(e_rank2_df),
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        "実オッズが必要オッズを超えている買い目だけを買い候補にします。"
        "二車複は期待値の芯、二車単は評価上位が頭になる方向の上乗せ確認用です。"
        "評価6・7絡みは慎重に扱います。"
    )

else:
    st.info("評価順を入力して『計算』を押してください。")
