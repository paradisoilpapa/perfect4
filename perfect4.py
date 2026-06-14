import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="二車複・二車単 必要オッズ表", layout="wide")

st.title("二車複・二車単 必要オッズ表")
st.caption("ヴェロビ評価順を入力して、二車複・二車単の必要オッズを車番に変換します。5〜7車対応。")

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
    5〜7車対応。
    例：
    41325   → ['4', '1', '3', '2', '5']
    2715364 → ['2', '7', '1', '5', '3', '6', '4']
    """
    nums = re.findall(r"[1-7]", text or "")

    if len(nums) < 5 or len(nums) > 7:
        return []

    if len(set(nums)) != len(nums):
        return []

    return nums


def exacta_count(first_rank: int, second_rank: int) -> int:
    if first_rank == second_rank:
        return 0
    return EXACTA_COUNT.get(first_rank, {}).get(second_rank, 0)


def quinella_count(rank_a: int, rank_b: int) -> int:
    return exacta_count(rank_a, rank_b) + exacta_count(rank_b, rank_a)


def hit_rate_from_count(count: int) -> float:
    return count / TOTAL_N * 100 if count > 0 else 0.0


def required_odds_from_count(count: int) -> float | None:
    if count <= 0:
        return None
    return TOTAL_N / count


def fmt_rate(count: int) -> str:
    return f"{hit_rate_from_count(count):.2f}%" if count > 0 else "0.00%"


def fmt_odds(count: int) -> str:
    odds = required_odds_from_count(count)
    return f"{odds:.2f}倍" if odds is not None else "—"


def extract_rank_pair(value: str) -> tuple[int, int] | None:
    nums = re.findall(r"\d+", str(value))
    if len(nums) < 2:
        return None

    a = int(nums[0])
    b = int(nums[1])

    if a == b:
        return None

    return tuple(sorted((a, b)))


def highlight_rank_pair(row):
    """
    色分け：
    評価1-2              → 薄赤
    評価1-3 / 評価2-3   → 薄青
    評価1-4 / 評価2-4   → 薄黄
    評価1-5 / 評価2-5   → 薄緑
    その他              → 白
    """
    target_col = None

    if "評価ペア" in row.index:
        target_col = "評価ペア"
    elif "評価方向" in row.index:
        target_col = "評価方向"

    if target_col is None:
        return [""] * len(row)

    pair = extract_rank_pair(row[target_col])

    if pair == (1, 2):
        return ["background-color: #fde2e2"] * len(row)  # 薄赤

    if pair in [(1, 3), (2, 3)]:
        return ["background-color: #e8f1ff"] * len(row)  # 薄青

    if pair in [(1, 4), (2, 4)]:
        return ["background-color: #fff4cc"] * len(row)  # 薄黄

    if pair in [(1, 5), (2, 5)]:
        return ["background-color: #eaf7f0"] * len(row)  # 薄緑

    return [""] * len(row)


def styled_df(df: pd.DataFrame):
    return df.style.apply(highlight_rank_pair, axis=1)


def make_quinella_axis_tables(cars: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = len(cars)

    rank1_car = cars[0]
    rank2_car = cars[1] if n >= 2 else None

    rank1_rows = []
    for rank_b in range(2, n + 1):
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
    if rank2_car is not None:
        for rank_b in range(3, n + 1):
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
        if rank2_rows else pd.DataFrame()
    )

    return rank1_df, rank2_df


def make_exacta_axis_tables(cars: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = len(cars)

    rank1_car = cars[0]
    rank2_car = cars[1] if n >= 2 else None

    rank1_rows = []
    for rank_b in range(2, n + 1):
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
    if rank2_car is not None:
        tail_rank_list = [1] + list(range(3, n + 1))

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
        if rank2_rows else pd.DataFrame()
    )

    return rank1_df, rank2_df


st.subheader("評価順を入力して計算")

rank_text = st.text_input(
    "ヴェロビ評価順（例：41325 / 2715364）",
    value="",
    placeholder="41325",
)

calc = st.button("計算", type="primary")

if calc:
    cars = normalize_rank_text(rank_text)

    if not cars:
        st.error("1〜7の車番を重複なく5〜7つ入力してください。例：41325 / 2715364")
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
        if not q_rank2_df.empty:
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
        if not e_rank2_df.empty:
            st.dataframe(
                styled_df(e_rank2_df),
                use_container_width=True,
                hide_index=True,
            )

    st.info(
        "赤：評価1-2｜青：評価1-3・評価2-3｜黄：評価1-4・評価2-4｜緑：評価1-5・評価2-5。"
        "二車複は必要オッズを超えた組み合わせを芯候補として確認します。"
    )

else:
    st.info("評価順を入力して『計算』を押してください。")
