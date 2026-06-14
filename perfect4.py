import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="二車複 必要オッズ表", layout="wide")

st.title("二車複 必要オッズ表")
st.caption("ヴェロビ評価順を貼るだけで、評価1位軸・評価2位軸の二車複必要オッズを表示します。")

# 評価順位ペアごとの過去的中率（%）
HIT_RATE = {
    "1-2": 21.6,
    "1-3": 12.2,
    "1-4": 9.7,
    "1-5": 4.6,
    "1-6": 3.1,
    "1-7": 1.0,
    "2-3": 8.9,
    "2-4": 6.9,
    "2-5": 5.1,
    "2-6": 3.1,
    "2-7": 2.3,
}


def normalize_rank_text(text: str) -> list[str]:
    """評価順テキストから1〜7の車番を抽出する。例: '2715364' -> ['2','7','1','5','3','6','4']"""
    nums = re.findall(r"[1-7]", text or "")
    # 重複をそのまま通すと誤変換するため、7車が1回ずつ出ているか確認
    if len(nums) != 7 or len(set(nums)) != 7:
        return []
    return nums


def required_odds(rate: float) -> float:
    return round(100.0 / rate, 2) if rate > 0 else 0.0


def make_rows(cars: list[str]) -> pd.DataFrame:
    rows = []

    # 評価1位軸：評価2〜7位へ
    rank1_car = cars[0]
    for rank_idx in range(1, 7):
        eval_pair = f"1-{rank_idx + 1}"
        rate = HIT_RATE[eval_pair]
        rows.append({
            "軸": f"評価1位軸：{rank1_car}",
            "買い目": f"{rank1_car}={cars[rank_idx]}",
            "必要オッズ": required_odds(rate),
        })

    # 評価2位軸：評価3〜7位へ
    rank2_car = cars[1]
    for rank_idx in range(2, 7):
        eval_pair = f"2-{rank_idx + 1}"
        rate = HIT_RATE[eval_pair]
        rows.append({
            "軸": f"評価2位軸：{rank2_car}",
            "買い目": f"{rank2_car}={cars[rank_idx]}",
            "必要オッズ": required_odds(rate),
        })

    df = pd.DataFrame(rows)
    # 買いすぎ防止：必要オッズが安い上位3点だけ※
    top3_idx = df.nsmallest(3, "必要オッズ").index
    df.insert(0, "※", "")
    df.loc[top3_idx, "※"] = "※"
    return df


rank_text = st.text_input("ヴェロビ評価順（例：2715364）", value="2715364")
cars = normalize_rank_text(rank_text)

if not cars:
    st.warning("1〜7の車番を重複なく7つ入力してください。例：2715364")
    st.stop()

df = make_rows(cars)

st.subheader("必要オッズ表")
st.caption("※は、必要オッズが安い上位3点です。買い確定ではなく、まず見る優先候補です。")

for axis_name, part in df.groupby("軸", sort=False):
    st.markdown(f"### {axis_name}")
    st.dataframe(
        part[["※", "買い目", "必要オッズ"]],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("※ 優先候補")
st.dataframe(
    df[df["※"] == "※"][["買い目", "必要オッズ"]].sort_values("必要オッズ"),
    use_container_width=True,
    hide_index=True,
)

st.info("実オッズが必要オッズを超えている買い目だけを買い候補にします。")
