# -*- coding: utf-8 -*-

from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ集計｜現行印ベース", layout="wide")
st.title("ヴェロビ集計｜現行印ベース")

# ============================================================
# 現行ヴェロビ買い目
# ============================================================
VELOVI_MARKS = ("◎", "○", "▲", "△", "×")

CURRENT_2T_BETS: List[Tuple[str, Tuple[str, ...]]] = [
    ("2車単 ◎-▲", ("◎", "▲")),
    ("2車単 ○-◎", ("○", "◎")),
    ("2車単 ▲-◎", ("▲", "◎")),
    ("2車単 ◎-○", ("◎", "○")),
]

CURRENT_3T_BETS: List[Tuple[str, Tuple[str, ...]]] = [
    ("3連単 ◎-▲-△", ("◎", "▲", "△")),
    ("3連単 ◎-▲-×", ("◎", "▲", "×")),
    ("3連単 ◎-○-▲", ("◎", "○", "▲")),
    ("3連単 ◎-○-△", ("◎", "○", "△")),
    ("3連単 ◎-○-×", ("◎", "○", "×")),
    ("3連単 ◎-▲-○", ("◎", "▲", "○")),
]

ALL_BETS = CURRENT_2T_BETS + CURRENT_3T_BETS
ALL_LABELS = [label for label, _ in ALL_BETS]

CURRENT_2T_MAIN_LABELS = [
    "2車単 ◎-▲",
    "2車単 ○-◎",
    "2車単 ▲-◎",
]
CURRENT_2T_ALL_LABELS = CURRENT_2T_MAIN_LABELS + ["2車単 ◎-○"]

CURRENT_3T_MAIN_LABELS = [
    "3連単 ◎-▲-△",
    "3連単 ◎-▲-×",
]
CURRENT_3T_CIRCLE_LABELS = [
    "3連単 ◎-○-▲",
    "3連単 ◎-○-△",
    "3連単 ◎-○-×",
]
CURRENT_3T_ALL_LABELS = CURRENT_3T_MAIN_LABELS + CURRENT_3T_CIRCLE_LABELS + ["3連単 ◎-▲-○"]

SET_SPECS = [
    ("2車単 推奨3点｜◎-▲ / ○-◎ / ▲-◎", CURRENT_2T_MAIN_LABELS),
    ("2車単 全4点｜推奨3点 + ◎-○", CURRENT_2T_ALL_LABELS),
    ("3連単 基本2点｜◎-▲-△ / ◎-▲-×", CURRENT_3T_MAIN_LABELS),
    ("3連単 ◎-○流し3点｜◎-○-▲ / ◎-○-△ / ◎-○-×", CURRENT_3T_CIRCLE_LABELS),
    ("3連単 全6点｜基本2点 + ◎-○流し3点 + ◎-▲-○", CURRENT_3T_ALL_LABELS),
]


def clean_digits(value: str) -> str:
    """区切り記号を除き、数字だけを残す。"""
    if value is None:
        return ""
    s = str(value).strip()
    for ch in ("-", " ", "/", ",", "、", "→"):
        s = s.replace(ch, "")
    return "".join(ch for ch in s if ch.isdigit())


def parse_markline(value: str) -> Dict[str, str]:
    """
    ◎○▲△×の順に5車を入力。
    例：41632 = ◎4 / ○1 / ▲6 / △3 / ×2
    """
    s = clean_digits(value)
    if len(s) != 5 or len(set(s)) != 5:
        return {}
    if any(ch == "0" for ch in s):
        return {}
    return dict(zip(VELOVI_MARKS, list(s)))


def parse_finish(value: str) -> List[str]:
    """着順から先頭3車を取得。例：4-6-3 / 463 のどちらも可。"""
    s = clean_digits(value)
    out: List[str] = []
    for ch in s:
        if ch == "0":
            continue
        if ch not in out:
            out.append(ch)
        if len(out) == 3:
            break
    return out


def new_rec() -> Dict[str, int]:
    return {"N": 0, "H": 0, "SUM": 0, "KSUM": 0}


def is_hit(order_marks: Tuple[str, ...], marks: Dict[str, str], finish: List[str]) -> bool:
    if not marks or len(finish) < len(order_marks):
        return False
    expected = [marks[m] for m in order_marks]
    return finish[: len(order_marks)] == expected


def rec_to_row(label: str, rec: Dict[str, int]) -> Dict:
    n = int(rec.get("N", 0))
    h = int(rec.get("H", 0))
    payout_sum = int(rec.get("SUM", 0))
    ksum = int(rec.get("KSUM", 0))
    investment = ksum * 100

    return {
        "買い目": label,
        "対象R": n,
        "購入点数": ksum,
        "投資額": investment,
        "的中数": h,
        "的中率%": round(h / n * 100.0, 1) if n else None,
        "払戻合計": payout_sum,
        "平均的中配当": round(payout_sum / h, 1) if h else None,
        "回収率%": round(payout_sum / investment * 100.0, 1) if investment else None,
    }


def style_roi(df: pd.DataFrame):
    def color_roi(v):
        try:
            x = float(v)
        except Exception:
            return ""
        if x >= 100.0:
            return "background-color: #d9ead3; font-weight: 700;"
        if x >= 90.0:
            return "background-color: #fff2cc; font-weight: 600;"
        return ""

    return df.style.format({"的中率%": "{:.1f}", "回収率%": "{:.1f}", "平均的中配当": "{:.1f}"}, na_rep="—").map(
        color_roi, subset=["回収率%"]
    )


# ============================================================
# 入力
# ============================================================
st.caption(
    "入力は『印順・着順・2車単・3連単』だけです。"
    " 印順は ◎○▲△× の順に5車を入力します。例：41632 = ◎4 / ○1 / ▲6 / △3 / ×2。"
    " 払戻は100円あたりの実払戻額を入力してください。"
)

with st.form("daily_input_form"):
    header = st.columns([0.55, 1.6, 1.1, 1.0, 1.0])
    for col, title in zip(header, ["R", "印順 ◎○▲△×", "着順", "2車単", "3連単"]):
        col.markdown(f"**{title}**")

    rows = []
    for i in range(1, 101):
        c1, c2, c3, c4, c5 = st.columns([0.55, 1.6, 1.1, 1.0, 1.0])
        rid = c1.text_input("R", value=str(i), key=f"rid_{i}", label_visibility="collapsed")
        markline = c2.text_input("印順", value="", key=f"mark_{i}", label_visibility="collapsed")
        finish = c3.text_input("着順", value="", key=f"fin_{i}", label_visibility="collapsed")
        pay_2t = c4.number_input(
            "2車単", min_value=0, value=0, step=10, key=f"pay2t_{i}", label_visibility="collapsed"
        )
        pay_3t = c5.number_input(
            "3連単", min_value=0, value=0, step=10, key=f"pay3t_{i}", label_visibility="collapsed"
        )
        rows.append(
            {
                "race": rid,
                "markline": markline,
                "finish_raw": finish,
                "pay_2t": int(pay_2t),
                "pay_3t": int(pay_3t),
            }
        )

    submitted = st.form_submit_button("集計する")


# ============================================================
# 集計
# ============================================================
records = {label: new_rec() for label in ALL_LABELS}
valid_races = 0
warnings: List[str] = []
race_details: List[Dict] = []

for row in rows:
    rid = str(row["race"]).strip()
    mark_raw = str(row["markline"]).strip()
    finish_raw = str(row["finish_raw"]).strip()
    pay_2t = int(row["pay_2t"])
    pay_3t = int(row["pay_3t"])

    # 完全未入力行は無視。
    if not any([mark_raw, finish_raw, pay_2t > 0, pay_3t > 0]):
        continue

    marks = parse_markline(mark_raw)
    finish = parse_finish(finish_raw)

    if not marks:
        warnings.append(f"R{rid}: 印順は◎○▲△×の順に、重複なし5車で入力してください。例 41632")
        continue
    if len(finish) < 3:
        warnings.append(f"R{rid}: 着順は3着まで入力してください。例 463 または 4-6-3")
        continue

    # 印に使った車番と実着順の車番が矛盾していても、無印車が3着内に入ることはあるため許容。
    valid_races += 1

    hit_labels: List[str] = []
    for label, order_marks in ALL_BETS:
        rec = records[label]
        rec["N"] += 1
        rec["KSUM"] += 1

        hit = is_hit(order_marks, marks, finish)
        if hit:
            rec["H"] += 1
            hit_labels.append(label)
            if label.startswith("2車単"):
                rec["SUM"] += pay_2t
                if pay_2t <= 0:
                    warnings.append(f"R{rid}: {label} 的中ですが2車単払戻が0です。")
            else:
                rec["SUM"] += pay_3t
                if pay_3t <= 0:
                    warnings.append(f"R{rid}: {label} 的中ですが3連単払戻が0です。")

    race_details.append(
        {
            "R": rid,
            "印順": mark_raw,
            "着順": "-".join(finish[:3]),
            "2車単払戻": pay_2t,
            "3連単払戻": pay_3t,
            "的中買い目": " / ".join(hit_labels) if hit_labels else "なし",
        }
    )


# ============================================================
# 結果
# ============================================================
st.divider()
st.subheader("買い目別｜的中率・回収率")
st.caption(f"有効入力 {valid_races}R。各買い目を毎レース1点100円で購入したものとして集計します。")

individual_df = pd.DataFrame([rec_to_row(label, records[label]) for label in ALL_LABELS])
st.dataframe(style_roi(individual_df), use_container_width=True, hide_index=True)

st.subheader("セット集計｜的中率・回収率")
set_rows = []
for set_label, labels in SET_SPECS:
    n = valid_races
    points_per_race = len(labels)
    ksum = n * points_per_race
    investment = ksum * 100
    payout_sum = sum(records[label]["SUM"] for label in labels)

    # 同一券種・完全一致型なので、同じレースでセット内複数点が同時的中することはない。
    hits = sum(records[label]["H"] for label in labels)

    set_rows.append(
        {
            "買い目": set_label,
            "対象R": n,
            "1R点数": points_per_race,
            "購入点数": ksum,
            "投資額": investment,
            "的中数": hits,
            "的中率%": round(hits / n * 100.0, 1) if n else None,
            "払戻合計": payout_sum,
            "平均的中配当": round(payout_sum / hits, 1) if hits else None,
            "回収率%": round(payout_sum / investment * 100.0, 1) if investment else None,
        }
    )

set_df = pd.DataFrame(set_rows)
st.dataframe(style_roi(set_df), use_container_width=True, hide_index=True)

if warnings:
    st.warning("\n".join(warnings[:20]) + ("\n…" if len(warnings) > 20 else ""))

if race_details:
    with st.expander("レース別判定を確認"):
        st.dataframe(pd.DataFrame(race_details), use_container_width=True, hide_index=True)

# CSV出力
if not individual_df.empty:
    st.download_button(
        "買い目別集計CSVをダウンロード",
        data=individual_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="velovi_bet_summary.csv",
        mime="text/csv",
    )
