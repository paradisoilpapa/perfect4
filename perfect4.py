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
    ("2車単 ◎-△", ("◎", "△")),
    ("2車単 ◎-×", ("◎", "×")),
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
    印順を解析する。

    4車入力：◎○▲△
      例 4163 = ◎4 / ○1 / ▲6 / △3
      → ×は未入力として扱い、×を使う買い目・×の印着内率だけ当該Rを対象外にする。

    5車入力：◎○▲△×
      例 41632 = ◎4 / ○1 / ▲6 / △3 / ×2
    """
    s = clean_digits(value)
    if len(s) not in (4, 5) or len(set(s)) != len(s):
        return {}
    if any(ch == "0" for ch in s):
        return {}
    return dict(zip(VELOVI_MARKS[:len(s)], list(s)))


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


def add_rec(dst: Dict[str, int], src: Dict[str, int]) -> None:
    for key in ("N", "H", "SUM", "KSUM"):
        dst[key] = int(dst.get(key, 0)) + int(src.get(key, 0))


def new_mark_rec() -> Dict[str, int]:
    return {"N": 0, "C1": 0, "C2": 0, "C3": 0}


def add_mark_rec(dst: Dict[str, int], src: Dict[str, int]) -> None:
    for key in ("N", "C1", "C2", "C3"):
        dst[key] = int(dst.get(key, 0)) + int(src.get(key, 0))


def pct(num: int, den: int):
    return round(100.0 * int(num) / int(den), 1) if int(den) > 0 else None


def mark_rec_to_row(mark: str, rec: Dict[str, int]) -> Dict:
    n = int(rec.get("N", 0))
    c1 = int(rec.get("C1", 0))
    c2 = int(rec.get("C2", 0))
    c3 = int(rec.get("C3", 0))
    return {
        "印": mark,
        "対象N": n,
        "1着回数": c1,
        "2着回数": c2,
        "3着回数": c3,
        "1着率%": pct(c1, n),
        "連対率%": pct(c1 + c2, n),
        "印着内率%": pct(c1 + c2 + c3, n),
    }


def is_hit(order_marks: Tuple[str, ...], marks: Dict[str, str], finish: List[str]) -> bool:
    if not marks or len(finish) < len(order_marks):
        return False
    # 未入力印（例：×）を含む買い目は判定不能なのでFalse。
    if any(m not in marks for m in order_marks):
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


def combine_recs(records: Dict[str, Dict[str, int]], labels: List[str]) -> Dict[str, int]:
    """
    同一レース群に対するセット集計。
    Nは各買い目の最大Nを使用し、購入点数・的中数・払戻を合算する。
    """
    recs = [records[label] for label in labels]
    out = new_rec()
    out["N"] = max((int(r.get("N", 0)) for r in recs), default=0)
    out["KSUM"] = sum(int(r.get("KSUM", 0)) for r in recs)
    out["H"] = sum(int(r.get("H", 0)) for r in recs)
    out["SUM"] = sum(int(r.get("SUM", 0)) for r in recs)
    return out


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

    return (
        df.style
        .format(
            {
                "的中率%": "{:.1f}",
                "回収率%": "{:.1f}",
                "平均的中配当": "{:.1f}",
            },
            na_rep="—",
        )
        .map(color_roi, subset=["回収率%"])
    )


def show_full_table(data, *, hide_index=True):
    """集計表を行数に合わせて表示し、表内の縦スクロールをなくす。"""
    row_count = len(data.data) if isinstance(data, pd.io.formats.style.Styler) else len(data)
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=hide_index,
        height=max(110, 39 + row_count * 36),
    )


# ============================================================
# 画面
# ============================================================
tab_daily, tab_carry, tab_result = st.tabs(
    ["日次入力", "前日までの集計（引継ぎ）", "集計結果"]
)

# ============================================================
# A. 日次入力
# ============================================================
with tab_daily:
    st.caption(
        "日次入力は『印順・着順・2車単・3連単』が基本です。"
        " 印順は ◎○▲△ の4車でも、◎○▲△× の5車でも入力できます。"
        " 例：4163 = ◎4 / ○1 / ▲6 / △3、41632 = ×2まで入力。"
        " ×未入力時は、×を使う集計だけ当該Rを対象外にします。"
        " 払戻は100円あたりの実払戻額です。"
        " 落車・失格などで通常評価から外したいレースは『集計除外』にチェックしてください。"
    )

    with st.form("daily_input_form"):
        header = st.columns([0.55, 1.6, 1.1, 1.0, 1.0, 0.85])
        for col, title in zip(header, ["R", "印順 ◎○▲△（×任意）", "着順", "2車単", "3連単", "集計除外"]):
            col.markdown(f"**{title}**")

        daily_rows = []
        for i in range(1, 101):
            c1, c2, c3, c4, c5, c6 = st.columns([0.55, 1.6, 1.1, 1.0, 1.0, 0.85])
            rid = c1.text_input("R", value=str(i), key=f"rid_{i}", label_visibility="collapsed")
            markline = c2.text_input("印順", value="", key=f"mark_{i}", label_visibility="collapsed")
            finish = c3.text_input("着順", value="", key=f"fin_{i}", label_visibility="collapsed")
            pay_2t = c4.number_input(
                "2車単", min_value=0, value=0, step=10, key=f"pay2t_{i}", label_visibility="collapsed"
            )
            pay_3t = c5.number_input(
                "3連単", min_value=0, value=0, step=10, key=f"pay3t_{i}", label_visibility="collapsed"
            )
            exclude = c6.checkbox(
                "除外", value=False, key=f"exclude_{i}", label_visibility="collapsed"
            )
            daily_rows.append(
                {
                    "race": rid,
                    "markline": markline,
                    "finish_raw": finish,
                    "pay_2t": int(pay_2t),
                    "pay_3t": int(pay_3t),
                    "exclude": bool(exclude),
                }
            )

        st.form_submit_button("日次入力を反映")

# ============================================================
# B. 前日までの累積引継ぎ
# ============================================================
carry_records = {label: new_rec() for label in ALL_LABELS}
carry_mark_records = {mark: new_mark_rec() for mark in VELOVI_MARKS}

with tab_carry:
    st.subheader("前日までの集計（累積・引継ぎ）")
    st.caption(
        "前日までの各買い目の『対象N・的中H・払戻合計SUM』を入力します。"
        "各買い目は1レース1点100円として、購入点数と投資額はNから自動計算します。"
    )

    with st.form("carryover_form"):
        hdr = st.columns([2.4, 1.0, 1.3, 1.0])
        for col, title in zip(hdr, ["買い目", "対象N", "的中H", "払戻合計SUM"]):
            col.markdown(f"**{title}**")

        carry_inputs = []
        for label in ALL_LABELS:
            c0, c1, c2, c3 = st.columns([2.4, 1.0, 1.3, 1.0])
            c0.markdown(f"**{label}**")
            n = c1.number_input(
                "N", min_value=0, value=0, step=1,
                key=f"carry_n_{label}", label_visibility="collapsed"
            )
            h = c2.number_input(
                "H", min_value=0, value=0, step=1,
                key=f"carry_h_{label}", label_visibility="collapsed"
            )
            payout_sum = c3.number_input(
                "SUM", min_value=0, value=0, step=10,
                key=f"carry_sum_{label}", label_visibility="collapsed"
            )
            carry_inputs.append((label, int(n), int(payout_sum), int(h)))

        st.markdown("---")
        st.markdown("### 印別 入賞回数（累積・引継ぎ）")
        st.caption(
            "印着内率を継続するため、前日までの◎○▲△×ごとの対象N・1着・2着・3着回数を入力します。"
        )
        mhdr = st.columns([1.2, 1.0, 1.0, 1.0, 1.0])
        for col, title in zip(mhdr, ["印", "対象N", "1着", "2着", "3着"]):
            col.markdown(f"**{title}**")

        carry_mark_inputs = []
        for mark in VELOVI_MARKS:
            m0, m1, m2, m3, m4 = st.columns([1.2, 1.0, 1.0, 1.0, 1.0])
            m0.markdown(f"**{mark}**")
            n = m1.number_input("対象N", min_value=0, value=0, step=1, key=f"carry_mark_n_{mark}", label_visibility="collapsed")
            c1 = m2.number_input("1着", min_value=0, value=0, step=1, key=f"carry_mark_c1_{mark}", label_visibility="collapsed")
            c2 = m3.number_input("2着", min_value=0, value=0, step=1, key=f"carry_mark_c2_{mark}", label_visibility="collapsed")
            c3 = m4.number_input("3着", min_value=0, value=0, step=1, key=f"carry_mark_c3_{mark}", label_visibility="collapsed")
            carry_mark_inputs.append((mark, int(n), int(c1), int(c2), int(c3)))

        st.form_submit_button("前日までの集計を反映")

    for label, n, payout_sum, h in carry_inputs:
        carry_records[label]["N"] = int(n)
        carry_records[label]["KSUM"] = int(n)
        carry_records[label]["SUM"] = int(payout_sum)
        carry_records[label]["H"] = int(h)

        if h > n:
            st.warning(f"{label}: 的中H({h}) が対象N({n})を超えています。")

    for mark, n, c1, c2, c3 in carry_mark_inputs:
        carry_mark_records[mark]["N"] = n
        carry_mark_records[mark]["C1"] = c1
        carry_mark_records[mark]["C2"] = c2
        carry_mark_records[mark]["C3"] = c3
        if c1 + c2 + c3 > n:
            st.warning(f"{mark}: 1〜3着回数合計({c1 + c2 + c3}) が対象N({n})を超えています。")

# ============================================================
# C. 日次集計
# ============================================================
daily_records = {label: new_rec() for label in ALL_LABELS}
daily_mark_records = {mark: new_mark_rec() for mark in VELOVI_MARKS}
valid_races = 0
excluded_races = 0
warnings: List[str] = []
race_details: List[Dict] = []

for row in daily_rows:
    rid = str(row["race"]).strip()
    mark_raw = str(row["markline"]).strip()
    finish_raw = str(row["finish_raw"]).strip()
    pay_2t = int(row["pay_2t"])
    pay_3t = int(row["pay_3t"])
    exclude = bool(row.get("exclude", False))

    if not any([mark_raw, finish_raw, pay_2t > 0, pay_3t > 0, exclude]):
        continue

    # 落車・失格などの集計除外レースは、入力内容をレース別確認に残すが、
    # 対象N・的中率・回収率・印着内率・セット集計のすべてから除外する。
    if exclude:
        excluded_races += 1
        finish_ex = parse_finish(finish_raw)
        race_details.append(
            {
                "R": rid,
                "印順": mark_raw,
                "着順": "-".join(finish_ex[:3]) if finish_ex else finish_raw,
                "2車単払戻": pay_2t,
                "3連単払戻": pay_3t,
                "集計除外": "除外",
                "的中買い目": "集計除外",
            }
        )
        continue

    marks = parse_markline(mark_raw)
    finish = parse_finish(finish_raw)

    if not marks:
        warnings.append(f"R{rid}: 印順は◎○▲△の4車、または◎○▲△×の5車を重複なしで入力してください。例 4163 / 41632")
        continue
    if len(finish) < 3:
        warnings.append(f"R{rid}: 着順は3着まで入力してください。例 463 または 4-6-3")
        continue

    valid_races += 1
    hit_labels: List[str] = []

    # 印別の1着・2着・3着・着内率を自動集計。
    # ×未入力時は×だけ対象Nに加えず、◎○▲△は通常どおり集計する。
    car_to_mark = {car: mark for mark, car in marks.items()}
    for mark in marks.keys():
        daily_mark_records[mark]["N"] += 1
    for pos, car in enumerate(finish[:3], start=1):
        mark = car_to_mark.get(car)
        if mark in daily_mark_records:
            daily_mark_records[mark][f"C{pos}"] += 1

    for label, order_marks in ALL_BETS:
        # ×など、そのレースで未入力の印を使う買い目は対象Nにも入れない。
        if any(mark not in marks for mark in order_marks):
            continue

        rec = daily_records[label]
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
            "集計除外": "",
            "的中買い目": " / ".join(hit_labels) if hit_labels else "なし",
        }
    )

# ============================================================
# D. 累積 = 引継ぎ + 日次
# ============================================================
total_records = {label: new_rec() for label in ALL_LABELS}
for label in ALL_LABELS:
    add_rec(total_records[label], carry_records[label])
    add_rec(total_records[label], daily_records[label])

total_mark_records = {mark: new_mark_rec() for mark in VELOVI_MARKS}
for mark in VELOVI_MARKS:
    add_mark_rec(total_mark_records[mark], carry_mark_records[mark])
    add_mark_rec(total_mark_records[mark], daily_mark_records[mark])

# ============================================================
# E. 集計結果
# ============================================================
with tab_result:
    st.subheader("買い目別｜累積 的中率・回収率")
    st.caption(
        f"本日有効入力 {valid_races}R／集計除外 {excluded_races}R。前日までの引継ぎと本日入力を合算した累積成績です。"
        "集計除外にチェックしたレースは対象N・的中率・回収率・印着内率・セット集計のすべてから除外します。"
        "各買い目は1レース1点100円で計算します。"
    )

    st.subheader("印別 入賞率｜累積")
    st.caption("◎○▲△×それぞれについて、前日までの引継ぎ＋本日入力から1着率・連対率・印着内率を集計します。")
    mark_df = pd.DataFrame([mark_rec_to_row(mark, total_mark_records[mark]) for mark in VELOVI_MARKS])
    mark_style = mark_df.style.format(
        {"1着率%": "{:.1f}", "連対率%": "{:.1f}", "印着内率%": "{:.1f}"},
        na_rep="—",
    )
    show_full_table(mark_style)

    st.divider()
    st.subheader("買い目別｜累積 的中率・回収率")
    total_df = pd.DataFrame([rec_to_row(label, total_records[label]) for label in ALL_LABELS])
    show_full_table(style_roi(total_df))

    st.subheader("セット集計｜累積 的中率・回収率")
    set_rows = []
    for set_label, labels in SET_SPECS:
        rec = combine_recs(total_records, labels)
        row = rec_to_row(set_label, rec)
        row["1R点数"] = len(labels)
        set_rows.append(row)

    set_df = pd.DataFrame(set_rows)
    set_cols = [
        "買い目", "対象R", "1R点数", "購入点数", "投資額",
        "的中数", "的中率%", "払戻合計", "平均的中配当", "回収率%"
    ]
    show_full_table(style_roi(set_df[set_cols]))

    with st.expander("本日分だけの成績を見る"):
        st.markdown("#### 印別 入賞率（本日分）")
        daily_mark_df = pd.DataFrame([mark_rec_to_row(mark, daily_mark_records[mark]) for mark in VELOVI_MARKS])
        show_full_table(
            daily_mark_df.style.format(
                {"1着率%": "{:.1f}", "連対率%": "{:.1f}", "印着内率%": "{:.1f}"},
                na_rep="—",
            )
        )
        st.markdown("#### 買い目別（本日分）")
        daily_df = pd.DataFrame([rec_to_row(label, daily_records[label]) for label in ALL_LABELS])
        show_full_table(style_roi(daily_df))

    if warnings:
        st.warning("\n".join(warnings[:20]) + ("\n…" if len(warnings) > 20 else ""))

    if race_details:
        with st.expander("本日のレース別判定を確認"):
            st.dataframe(pd.DataFrame(race_details), use_container_width=True, hide_index=True)

    if not total_df.empty:
        st.download_button(
            "累積・買い目別集計CSVをダウンロード",
            data=total_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="velovi_bet_summary_total.csv",
            mime="text/csv",
        )
