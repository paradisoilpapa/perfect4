# -*- coding: utf-8 -*-
"""ヴェロビ集計｜通常◎と妙味αの独立集計・引継ぎ対応版。

元の618行版を基準とした仕様:
- 通常 ◎○▲△× / 妙味 αβγεΩ の印着内率
- 2車単は各軸の表裏8通りだけ（通常◎、妙味α）
- 通常◎→○▲△ / 妙味α→γβε の3点セット集計
- 3連単・2車複は入力・集計から削除
- 旧通常評価の入力キー・引継ぎキーを維持
- 日次100レース、除外、CSV、日次・累積・レース別確認
"""
from typing import Dict, List, Tuple
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ集計｜◎・α比較", layout="wide")
st.title("ヴェロビ集計｜通常◎・妙味α 比較")
st.caption("通常評価と妙味軸評価を独立集計。2車単は軸の表裏のみ、3連単なし。各買い目100円平買い換算。")

GROUP_MARKS = {
    "通常": ("◎", "○", "▲", "△", "×"),
    "妙味": ("α", "β", "γ", "ε", "Ω"),
}
SET_TARGETS = {"通常": ("○", "▲", "△"), "妙味": ("γ", "β", "ε")}
GROUP_AXES = {g: marks[0] for g, marks in GROUP_MARKS.items()}


def all_axis_pairs(marks: Tuple[str, ...]) -> List[Tuple[str, str]]:
    axis = marks[0]
    result = []
    for other in marks[1:]:
        result.append((axis, other))
        result.append((other, axis))
    return result


BET_PAIRS = {g: all_axis_pairs(marks) for g, marks in GROUP_MARKS.items()}


def blank_bet():
    return {"N": 0, "H": 0, "SUM": 0, "KSUM": 0}


def blank_mark():
    return {"N": 0, "C1": 0, "C2": 0, "C3": 0}


def blank_group_bets(g):
    return {pair: blank_bet() for pair in BET_PAIRS[g]}


def blank_group_marks(g):
    return {mark: blank_mark() for mark in GROUP_MARKS[g]}


def add_records(left, right, fields):
    return {f: int(left.get(f, 0)) + int(right.get(f, 0)) for f in fields}


def pct(num, den):
    return round(100 * num / den, 1) if den else None


def clean_digits(value: str) -> str:
    """元コードと同じく区切りを無視して車番数字を取得する。"""
    return "".join(c for c in str(value or "") if c.isdigit())


def parse_markline(value: str, group: str) -> Dict[str, str]:
    """4車または5車。通常は◎○▲△×、妙味はαβγεΩ。"""
    s = clean_digits(value)
    if len(s) not in (4, 5) or len(set(s)) != len(s) or "0" in s:
        return {}
    return dict(zip(GROUP_MARKS[group][:len(s)], list(s)))


def parse_finish(value: str) -> List[str]:
    """上位3着を取得。旧版同様、後続の余分な数字は無視する。"""
    s = clean_digits(value)
    result = []
    for c in s:
        if c == "0":
            continue
        if c not in result:
            result.append(c)
        if len(result) == 3:
            break
    return result


def mark_row(mark: str, rec: Dict[str, int]) -> Dict:
    n = int(rec["N"])
    c1, c2, c3 = (int(rec[f"C{i}"]) for i in (1, 2, 3))
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


def bet_row(name: str, rec: Dict[str, int]) -> Dict:
    n, h, summ = int(rec["N"]), int(rec["H"]), int(rec["SUM"])
    ksum = int(rec.get("KSUM", n))
    invest = ksum * 100
    return {
        "買い目": name,
        "対象R": n,
        "購入点数": ksum,
        "投資額": invest,
        "的中数": h,
        "的中率%": pct(h, n),
        "払戻合計": summ,
        "平均的中配当": round(summ / h, 1) if h else None,
        "回収率%": pct(summ, invest),
    }


def style_roi(df):
    def color_roi(value):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return ""
        if v >= 100:
            return "background-color: #d9ead3; font-weight: 700;"
        if v >= 90:
            return "background-color: #fff2cc; font-weight: 600;"
        return ""
    if "回収率%" not in df.columns:
        return df
    formats = {col: "{:.1f}" for col in ("的中率%", "回収率%", "平均的中配当") if col in df.columns}
    return df.style.format(formats, na_rep="—").map(color_roi, subset=["回収率%"])


def show_full_table(data, *, hide_index=True):
    rows = len(data.data) if isinstance(data, pd.io.formats.style.Styler) else len(data)
    st.dataframe(data, use_container_width=True, hide_index=hide_index,
                 height=max(110, 39 + rows * 36))


def pair_label(a, b):
    return f"2車単 {a}-{b}"


def carry_keys(group, a, b):
    """旧版の入力キーを可能な限り維持する。

    旧 CURRENT_2T_BETS に存在したものは carry_*、
    旧追加全20通りは pair_carry_* に保存されていた。
    """
    label = pair_label(a, b)
    legacy_direct = {
        "2車単 ◎-○", "2車単 ◎-▲", "2車単 ◎-△", "2車単 ◎-×",
        "2車単 ○-◎", "2車単 ○-▲", "2車単 △-◎", "2車単 △-○",
        "2車単 △-▲", "2車単 ▲-◎",
    }
    if group == "通常":
        prefix = "carry" if label in legacy_direct else "pair_carry"
        return tuple(f"{prefix}_{f}_{label}" for f in ("n", "h", "sum"))
    return tuple(f"alpha_carry_{f}_{a}_{b}" for f in ("n", "h", "sum"))


# ============================================================
# A. 日次入力（旧版と同じ100R、旧通常入力キーを保持）
# ============================================================
tab_daily, tab_carry, tab_result = st.tabs(
    ["日次入力", "前日までの集計（引継ぎ）", "集計結果"]
)

with tab_daily:
    st.caption(
        "通常印順：◎○▲△（×任意）、妙味印順：αβγε（Ω任意）。"
        "印は各グループ4～5車を入力。片方だけの入力も可。"
        "着順は3着まで。払戻は100円あたりの2車単払戻金です。"
        "落車・失格等は集計除外にチェックしてください。"
    )
    with st.form("daily_input_form"):
        cols = st.columns([0.55, 1.5, 1.5, 1.0, 1.0, 0.85])
        for col, title in zip(cols, [
            "R", "通常印順 ◎○▲△×", "妙味印順 αβγεΩ", "着順", "2車単", "集計除外"
        ]):
            col.markdown(f"**{title}**")
        daily_rows = []
        for i in range(1, 101):
            c1, c2, c3, c4, c5, c6 = st.columns([0.55, 1.5, 1.5, 1.0, 1.0, 0.85])
            rid = c1.text_input("R", value=str(i), key=f"rid_{i}", label_visibility="collapsed")
            normal = c2.text_input("通常印順", value="", key=f"mark_{i}", label_visibility="collapsed")
            alpha = c3.text_input("妙味印順", value="", key=f"alpha_mark_{i}", label_visibility="collapsed")
            finish = c4.text_input("着順", value="", key=f"fin_{i}", label_visibility="collapsed")
            pay = c5.number_input("2車単", min_value=0, value=0, step=10,
                                  key=f"pay2t_{i}", label_visibility="collapsed")
            exclude = c6.checkbox("除外", value=False, key=f"exclude_{i}",
                                  label_visibility="collapsed")
            daily_rows.append({
                "race": rid, "normal": normal, "alpha": alpha,
                "finish": finish, "pay": int(pay), "exclude": bool(exclude)
            })
        st.form_submit_button("日次入力を反映")


# ============================================================
# B. 引継ぎ（旧通常評価の入力キーを維持）
# ============================================================
carry_mark_records = {g: blank_group_marks(g) for g in GROUP_MARKS}
carry_bet_records = {g: blank_group_bets(g) for g in GROUP_MARKS}

with tab_carry:
    st.subheader("前日までの集計（累積・引継ぎ）")
    st.caption(
        "通常評価は旧版の印別1～3着回数と、◎を含む2車単表裏8通りを転記。"
        "妙味評価はα軸の成績を新規入力。旧版の3連単・他の2車単は転記不要です。"
        "引継ぎ対象Nは各印・買い目ごとに入力できます。"
    )
    with st.form("carryover_form"):
        for group, marks in GROUP_MARKS.items():
            st.markdown(f"### {group}評価｜印別 入賞回数（引継ぎ）")
            h = st.columns([1.2, 1.0, 1.0, 1.0, 1.0])
            for col, title in zip(h, ["印", "対象N", "1着", "2着", "3着"]):
                col.markdown(f"**{title}**")
            for mark in marks:
                c0, c1, c2, c3, c4 = st.columns([1.2, 1.0, 1.0, 1.0, 1.0])
                c0.markdown(f"**{mark}**")
                prefix = "carry_mark" if group == "通常" else "alpha_carry_mark"
                n = c1.number_input("対象N", min_value=0, value=0, step=1,
                                    key=f"{prefix}_n_{mark}", label_visibility="collapsed")
                x1 = c2.number_input("1着", min_value=0, value=0, step=1,
                                     key=f"{prefix}_c1_{mark}", label_visibility="collapsed")
                x2 = c3.number_input("2着", min_value=0, value=0, step=1,
                                     key=f"{prefix}_c2_{mark}", label_visibility="collapsed")
                x3 = c4.number_input("3着", min_value=0, value=0, step=1,
                                     key=f"{prefix}_c3_{mark}", label_visibility="collapsed")
                carry_mark_records[group][mark] = {"N": int(n), "C1": int(x1),
                                                    "C2": int(x2), "C3": int(x3)}
                if x1 + x2 + x3 > n:
                    st.warning(f"{group}{mark}: 1～3着回数合計が対象Nを超えています。")

            st.markdown(f"### {group}評価｜2車単・軸の表裏8通り（引継ぎ）")
            h = st.columns([2.4, 1.0, 1.3, 1.3])
            for col, title in zip(h, ["買い目", "対象N", "的中H", "払戻合計SUM"]):
                col.markdown(f"**{title}**")
            for a, b in BET_PAIRS[group]:
                c0, c1, c2, c3 = st.columns([2.4, 1.0, 1.3, 1.3])
                c0.markdown(f"**{a}→{b}**")
                key_n, key_h, key_sum = carry_keys(group, a, b)
                n = c1.number_input("対象N", min_value=0, value=0, step=1,
                                    key=key_n, label_visibility="collapsed")
                h = c2.number_input("的中H", min_value=0, value=0, step=1,
                                    key=key_h, label_visibility="collapsed")
                summ = c3.number_input("払戻合計", min_value=0, value=0, step=10,
                                       key=key_sum, label_visibility="collapsed")
                carry_bet_records[group][(a, b)] = {
                    "N": int(n), "H": int(h), "SUM": int(summ), "KSUM": int(n)
                }
                if h > n:
                    st.warning(f"{group} {a}→{b}: 的中Hが対象Nを超えています。")
        st.form_submit_button("前日までの集計を反映")


# ============================================================
# C. 日次集計（除外・部分入力・払い戻しチェック）
# ============================================================
daily_mark_records = {g: blank_group_marks(g) for g in GROUP_MARKS}
daily_bet_records = {g: blank_group_bets(g) for g in GROUP_MARKS}
valid_races = {g: 0 for g in GROUP_MARKS}
excluded_races = 0
warnings: List[str] = []
race_details: List[Dict] = []

for entry in daily_rows:
    rid = str(entry["race"]).strip()
    raw_normal = str(entry["normal"]).strip()
    raw_alpha = str(entry["alpha"]).strip()
    raw_finish = str(entry["finish"]).strip()
    payout = int(entry["pay"])
    exclude = bool(entry["exclude"])

    if not any([raw_normal, raw_alpha, raw_finish, payout > 0, exclude]):
        continue

    if exclude:
        excluded_races += 1
        race_details.append({
            "R": rid, "通常印順": raw_normal, "妙味印順": raw_alpha,
            "着順": raw_finish, "2車単払戻": payout,
            "集計除外": "除外", "通常的中": "集計除外", "妙味的中": "集計除外"
        })
        continue

    finish = parse_finish(raw_finish)
    if len(finish) < 3:
        warnings.append(f"R{rid}: 着順は3着まで入力してください。例 463 / 4-6-3")
        continue

    detail = {
        "R": rid, "通常印順": raw_normal, "妙味印順": raw_alpha,
        "着順": "-".join(finish[:3]), "2車単払戻": payout,
        "集計除外": ""
    }
    for group, raw in (("通常", raw_normal), ("妙味", raw_alpha)):
        if not raw:
            detail[f"{group}的中"] = "未入力"
            continue
        marks = parse_markline(raw, group)
        if not marks:
            warnings.append(f"R{rid}: {group}印順は4車または5車、重複なしで入力してください。")
            detail[f"{group}的中"] = "入力不正"
            continue
        valid_races[group] += 1

        # 印別の1着、2着、3着回数。
        # 5番目の印が省略された場合、その印だけ対象Nから除外する。
        car_to_mark = {car: mark for mark, car in marks.items()}
        for mark in marks:
            daily_mark_records[group][mark]["N"] += 1
        for pos, car in enumerate(finish[:3], 1):
            mark = car_to_mark.get(car)
            if mark:
                daily_mark_records[group][mark][f"C{pos}"] += 1

        # 2車単は軸を含む表裏のみ。
        hits = []
        for a, b in BET_PAIRS[group]:
            if a not in marks or b not in marks:
                continue
            rec = daily_bet_records[group][(a, b)]
            rec["N"] += 1
            rec["KSUM"] += 1
            if finish[0] == marks[a] and finish[1] == marks[b]:
                rec["H"] += 1
                rec["SUM"] += payout
                hits.append(f"{a}→{b}")
                if payout <= 0:
                    warnings.append(f"R{rid}: {group} {a}→{b} 的中ですが払戻が0です。")
        detail[f"{group}的中"] = " / ".join(hits) if hits else "なし"
    race_details.append(detail)


# ============================================================
# D. 累積 = 引継ぎ + 日次
# ============================================================
total_mark_records = {}
total_bet_records = {}
for group, marks in GROUP_MARKS.items():
    total_mark_records[group] = {
        m: add_records(carry_mark_records[group][m], daily_mark_records[group][m],
                       ("N", "C1", "C2", "C3")) for m in marks
    }
    total_bet_records[group] = {
        pair: add_records(carry_bet_records[group][pair], daily_bet_records[group][pair],
                          ("N", "H", "SUM", "KSUM")) for pair in BET_PAIRS[group]
    }


def mark_frame(group, records):
    return pd.DataFrame([mark_row(m, records[group][m]) for m in GROUP_MARKS[group]])


def bet_frame(group, records):
    return pd.DataFrame([
        bet_row(f"{a}→{b}", records[group][(a, b)]) for a, b in BET_PAIRS[group]
    ])


def set_summary(group, records):
    """指定3点の実購入点数合計から回収率を算出。欠損印は対象外。"""
    axis = GROUP_AXES[group]
    selected = [records[group][(axis, m)] for m in SET_TARGETS[group]]
    n = min(int(r["N"]) for r in selected) if selected else 0
    ksum = sum(int(r["KSUM"]) for r in selected)
    h = sum(int(r["H"]) for r in selected)
    summ = sum(int(r["SUM"]) for r in selected)
    return {
        "評価": group,
        "3点セット": f"{axis}→{'・'.join(SET_TARGETS[group])}",
        "対象R（共通下限）": n,
        "購入点数": ksum,
        "投資額": ksum * 100,
        "的中数": h,
        "払戻合計": summ,
        "平均的中配当": round(summ / h, 1) if h else None,
        "回収率%": pct(summ, ksum * 100),
    }


# ============================================================
# E. 結果・CSV・本日分・レース別判定
# ============================================================
with tab_result:
    st.subheader("◎軸とα軸｜累積比較")
    st.caption(
        f"本日有効入力 通常{valid_races['通常']}R／妙味{valid_races['妙味']}R／"
        f"集計除外{excluded_races}R。引継ぎ＋日次を合算。"
        "印未入力の場合は、その評価側だけ集計しません。"
    )
    summary_df = pd.DataFrame([
        set_summary(group, total_bet_records) for group in GROUP_MARKS
    ])
    show_full_table(style_roi(summary_df))

    for group in GROUP_MARKS:
        st.divider()
        st.subheader(f"{group}評価｜印別 入賞率【累積】")
        show_full_table(mark_frame(group, total_mark_records).style.format({
            "1着率%": "{:.1f}", "連対率%": "{:.1f}", "印着内率%": "{:.1f}"
        }, na_rep="—"))

        st.subheader(f"{group}評価｜2車単 軸の表裏8通り【累積】")
        st.caption("矢印の左が1着、右が2着。各買い目100円で回収率を計算します。")
        show_full_table(style_roi(bet_frame(group, total_bet_records)))

    with st.expander("本日分だけの成績を見る"):
        today_df = pd.DataFrame([
            set_summary(group, daily_bet_records) for group in GROUP_MARKS
        ])
        st.markdown("#### 3点セット｜本日分")
        show_full_table(style_roi(today_df))
        for group in GROUP_MARKS:
            st.markdown(f"#### {group}評価｜印別入賞率（本日分）")
            show_full_table(mark_frame(group, daily_mark_records).style.format({
                "1着率%": "{:.1f}", "連対率%": "{:.1f}", "印着内率%": "{:.1f}"
            }, na_rep="—"))
            st.markdown(f"#### {group}評価｜2車単・軸の表裏（本日分）")
            show_full_table(style_roi(bet_frame(group, daily_bet_records)))

    if warnings:
        st.warning("\n".join(warnings[:25]) + ("\n…" if len(warnings) > 25 else ""))
    if race_details:
        with st.expander("本日のレース別判定を確認"):
            show_full_table(pd.DataFrame(race_details).fillna(""))

    st.divider()
    st.subheader("CSVダウンロード")
    st.download_button(
        "◎・α 3点セット比較CSV",
        data=summary_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="velovi_axis_3point_summary.csv", mime="text/csv"
    )
    for group in GROUP_MARKS:
        export = bet_frame(group, total_bet_records)
        st.download_button(
            f"{group}評価・2車単累積成績CSV",
            data=export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"velovi_2t_{'normal' if group == '通常' else 'alpha'}.csv",
            mime="text/csv"
        )
        mark_export = mark_frame(group, total_mark_records)
        st.download_button(
            f"{group}評価・印着内率CSV",
            data=mark_export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"velovi_marks_{'normal' if group == '通常' else 'alpha'}.csv",
            mime="text/csv"
        )
