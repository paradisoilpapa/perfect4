# -*- coding: utf-8 -*-
"""ヴェロビ集計｜◎軸ワイドβ・ε検証版。

元の618行版を基準とした仕様:
- 通常 ◎○▲△× / 妙味 αβγεΩ の印着内率
- 2車単は各軸の表裏8通りだけ（通常◎、妙味α）
- 通常◎→○▲△ / 妙味α→γβε の3点セット集計
- ワイド ◎-β/ε を集計（最大2点）
- 旧通常評価の入力キー・引継ぎキーを維持
- 日次100レース、除外、CSV、日次・累積・レース別確認
"""
from typing import Dict, List, Tuple
import re
from itertools import combinations
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ集計｜◎・α比較", layout="wide")
st.title("ヴェロビ集計｜通常◎・妙味α 比較")
st.caption("通常評価と妙味軸評価を独立集計。◎→×・無印2車も比較。ワイド◎－β／εを検証。各買い目100円平買い換算。")

GROUP_MARKS = {
    "通常": ("◎", "○", "▲", "△", "×"),
    "妙味": ("α", "β", "γ", "ε", "Ω"),
}
SET_TARGETS = {"通常": ("○", "▲", "△"), "妙味": ("γ", "β", "ε")}
GROUP_AXES = {g: marks[0] for g, marks in GROUP_MARKS.items()}
WIDE_TARGETS = ("β", "ε")


def all_axis_pairs(marks: Tuple[str, ...]) -> List[Tuple[str, str]]:
    axis = marks[0]
    result = []
    for other in marks[1:]:
        result.append((axis, other))
        result.append((other, axis))
    return result


BET_PAIRS = {g: all_axis_pairs(marks) for g, marks in GROUP_MARKS.items()}


def parse_wide_payouts(entries, finish, rid, warnings):
    """ワイド的中組の車番と100円払戻を別枠から照合する。"""
    result = {}
    allowed = {frozenset(pair) for pair in ((finish[0], finish[1]), (finish[0], finish[2]), (finish[1], finish[2]))}
    for idx, (raw_pair, raw_money) in enumerate(entries, 1):
        raw_pair = str(raw_pair or "").strip()
        amount = int(raw_money or 0)
        if not raw_pair and amount == 0:
            continue
        if not raw_pair:
            warnings.append(f"R{rid}: ワイド{idx}の車番が未入力です。")
            continue
        m = re.fullmatch(r"\s*([1-9])\s*[-－ー=：:,/]?\s*([1-9])\s*", raw_pair)
        if not m:
            warnings.append(f"R{rid}: ワイド{idx}の車番は『1-2』または『12』で入力してください。")
            continue
        a, b = m.groups()
        pair = frozenset((a, b))
        if len(pair) != 2 or pair not in allowed:
            warnings.append(f"R{rid}: ワイド{idx}の{a}-{b}は着順上位3車の組み合わせではありません。")
            continue
        if pair in result:
            warnings.append(f"R{rid}: ワイド{idx}の{a}-{b}は重複入力です。")
            continue
        if amount <= 0:
            warnings.append(f"R{rid}: ワイド{idx}の{a}-{b}の払戻金を入力してください。")
            continue
        result[pair] = amount
    return result


def blank_bet():
    return {"N": 0, "H": 0, "SUM": 0, "KSUM": 0}


def blank_unmarked():
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
    formats = {col: "{:.1f}" for col in df.columns if "率%" in str(col) or col == "平均的中配当"}
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
        "着順は3着まで。2車単払戻は100円あたりの金額です。"
        "落車・失格等は集計除外にチェックしてください。"
        "車数は7車が初期値です。6車立ては6に変更してください。"
    )
    st.caption("ワイドは最大3組。車番と払戻金を別枠で入力します（例：車番 1-2、払戻 350円）。")
    with st.form("daily_input_form"):
        daily_rows = []
        for i in range(1, 101):
            st.markdown(f"**{i}R**")
            c1, c2, c3 = st.columns([1.0, 2.0, 2.0])
            rid = c1.text_input("R番号", value=str(i), key=f"rid_{i}")
            normal = c2.text_input("通常印順 ◎○▲△×", value="", key=f"mark_{i}")
            alpha = c3.text_input("妙味印順 αβγεΩ", value="", key=f"alpha_mark_{i}")
            c4, c5, c6, c7 = st.columns([1.6, 1.5, 1.0, 0.9])
            finish = c4.text_input("着順（3着まで）", value="", key=f"fin_{i}")
            pay = c5.number_input("2車単払戻", min_value=0, value=0, step=10,
                                  key=f"pay2t_{i}")
            trio_pay = c5.number_input("3連複払戻（100円）", min_value=0, value=0, step=10, key=f"pay3f_{i}")
            quinella_pay = c5.number_input("2車複払戻（100円）", min_value=0, value=0, step=10, key=f"pay2f_{i}")
            st.caption("ワイド的中組（車番・払戻を別入力）")
            wide_entries = []
            for j in range(1, 4):
                wc, wp = st.columns([1.0, 1.0])
                pair = wc.text_input(f"ワイド{j} 車番", key=f"wide_pair{j}_{i}", placeholder="例 12")
                money = wp.number_input(f"ワイド{j} 払戻（円）", min_value=0, value=0, step=10, key=f"wide_pay{j}_{i}")
                wide_entries.append((pair, int(money)))
            field_size = c6.selectbox("車数", options=[7, 6], key=f"field_size_{i}")
            exclude = c7.checkbox("集計除外", value=False, key=f"exclude_{i}")
            daily_rows.append({
                "race": rid, "normal": normal, "alpha": alpha,
                "finish": finish, "pay": int(pay), "trio_pay": int(trio_pay), "quinella_pay": int(quinella_pay), "wide_entries": wide_entries,
                "field_size": int(field_size), "exclude": bool(exclude)
            })
            st.divider()
        st.form_submit_button("日次入力を反映")


# ============================================================
# B. 引継ぎ（旧通常評価の入力キーを維持）
# ============================================================
carry_mark_records = {g: blank_group_marks(g) for g in GROUP_MARKS}
carry_bet_records = {g: blank_group_bets(g) for g in GROUP_MARKS}
carry_unmarked = {name: blank_unmarked() for name in ("◎→×", "◎→無印1", "◎→無印2")}
carry_wides = {mark: blank_bet() for mark in WIDE_TARGETS}

with tab_carry:
    st.subheader("前日までの集計（累積・引継ぎ）")
    st.caption(
        "通常評価は旧版の印別1～3着回数と、◎を含む2車単表裏8通りを転記。"
        "妙味評価はα軸の成績を新規入力。旧版の他の2車単は転記不要です。"
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
        st.markdown("### 通常評価｜◎→×・無印2車（引継ぎ）")
        st.caption("◎→×は上の通常評価2車単から自動引継ぎします。無印1・2の過去分がある場合のみ入力してください。過去の無印実績が不明なら0のまま、新規分から集計します。")
        for label in ("◎→無印1", "◎→無印2"):
            c0, c1, c2, c3 = st.columns([2.4, 1.0, 1.3, 1.3])
            c0.markdown(f"**{label}**")
            n = c1.number_input("対象N", min_value=0, step=1, key=f"unmarked_n_{label}", label_visibility="collapsed")
            h = c2.number_input("的中H", min_value=0, step=1, key=f"unmarked_h_{label}", label_visibility="collapsed")
            summ = c3.number_input("払戻合計", min_value=0, step=10, key=f"unmarked_sum_{label}", label_visibility="collapsed")
            carry_unmarked[label] = {"N": int(n), "H": int(h), "SUM": int(summ), "KSUM": int(n)}
            if h > n:
                st.warning(f"{label}: 的中Hが対象Nを超えています。")
        st.markdown("### ワイド ◎－β／ε（引継ぎ）")
        st.caption("以前のワイド集計がある場合だけ入力してください。なければ0のまま、新規分から集計します。")
        for mark in WIDE_TARGETS:
            a, b, c, d = st.columns([2.4, 1.0, 1.3, 1.3])
            a.markdown(f"**◎－{mark}**")
            prefix = f"wide_carry_{mark}"
            n = b.number_input("対象N", min_value=0, step=1, key=f"{prefix}_n", label_visibility="collapsed")
            h = c.number_input("的中H", min_value=0, step=1, key=f"{prefix}_h", label_visibility="collapsed")
            summ = d.number_input("払戻合計", min_value=0, step=10, key=f"{prefix}_sum", label_visibility="collapsed")
            carry_wides[mark] = {"N": int(n), "H": int(h), "SUM": int(summ), "KSUM": int(n)}
            if h > n:
                st.warning(f"ワイド ◎－{mark}: 的中Hが対象Nを超えています。")
        st.form_submit_button("前日までの集計を反映")


# ============================================================
# C. 日次集計（除外・部分入力・払い戻しチェック）
# ============================================================
daily_mark_records = {g: blank_group_marks(g) for g in GROUP_MARKS}
daily_bet_records = {g: blank_group_bets(g) for g in GROUP_MARKS}
daily_unmarked = {name: blank_unmarked() for name in ("◎→×", "◎→無印1", "◎→無印2")}
daily_wides = {mark: blank_bet() for mark in WIDE_TARGETS}
# ◎－×：通常評価の×を相手とするワイド。既存の払戻入力を再利用。
daily_wide_x = blank_bet()
# 2車複：◎－無印（全無印車）、◎－×。日次入力のみ。
daily_quinella = {name: blank_bet() for name in ("◎－無印合計", "◎－×")}
quinella_missing_payouts = 0
wide_unmarked_names = ("◎－無印1", "◎－無印2", "◎－無印合計", "◎－無印∩β/ε")
daily_wide_unmarked = {name: blank_bet() for name in wide_unmarked_names}
# 3連複：◎軸、相手は通常無印1・2と妙味β・ε（重複車番は1車扱い）。
trio_stats = {"対象R": 0, "購入点数": 0, "的中数": 0, "的中R": 0}
trio_detail = []
trio_symbol_counts = {}
trio_symbol_stakes = {}
trio_symbol_races = {}
trio_normal_counts = {}
trio_symbol_payouts = {}
trio_missing_payouts = 0
trio_total_payout = 0
trio_symbol_details = []
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
    trio_pay = int(entry.get("trio_pay", 0))
    quinella_pay = int(entry.get("quinella_pay", 0))
    wide_entries = entry["wide_entries"]
    field_size = int(entry["field_size"])
    exclude = bool(entry["exclude"])

    if not any([raw_normal, raw_alpha, raw_finish, payout > 0, trio_pay > 0, quinella_pay > 0, any(str(pair).strip() or money > 0 for pair, money in wide_entries), exclude]):
        continue

    if exclude:
        excluded_races += 1
        race_details.append({
            "R": rid, "通常印順": raw_normal, "妙味印順": raw_alpha,
            "着順": raw_finish, "2車単払戻": payout, "ワイド的中組": " / ".join(f"{pair}:{money}" for pair, money in wide_entries if pair or money),
            "集計除外": "除外", "通常的中": "集計除外", "妙味的中": "集計除外"
        })
        continue

    finish = parse_finish(raw_finish)
    if len(finish) < 3:
        warnings.append(f"R{rid}: 着順は3着まで入力してください。例 463 / 4-6-3")
        continue

    detail = {
        "R": rid, "通常印順": raw_normal, "妙味印順": raw_alpha,
        "着順": "-".join(finish[:3]), "2車単払戻": payout, "ワイド的中組": " / ".join(f"{pair}:{money}" for pair, money in wide_entries if pair or money),
        "集計除外": "", "◎→×無無": "未集計"
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
        if group == "通常":
            # 5印のあるレースだけ、残る車番を無印として確定する。
            # 6車なら無印1車、7車なら無印2車。4印では判定しない。
            if len(marks) == 5 and all(1 <= int(v) <= field_size for v in marks.values()) and all(1 <= int(v) <= field_size for v in finish):
                unknown = sorted(set(str(v) for v in range(1, field_size + 1)) - set(marks.values()), key=int)
                targets = [("◎→×", marks["×"])] + [(f"◎→無印{i}", car) for i, car in enumerate(unknown, 1)]
                if len(unknown) == field_size - 5:
                    hit_names = []
                    for name, second_car in targets:
                        if name not in daily_unmarked:
                            continue
                        rec_u = daily_unmarked[name]
                        rec_u["N"] += 1
                        rec_u["KSUM"] += 1
                        if finish[0] == marks["◎"] and finish[1] == second_car:
                            rec_u["H"] += 1
                            rec_u["SUM"] += payout
                            hit_names.append(name)
                            if payout <= 0:
                                warnings.append(f"R{rid}: {name}的中ですが払戻が0です。")
                    detail["◎→×無無"] = " / ".join(hit_names) if hit_names else "なし"
            elif len(marks) == 4:
                detail["◎→×無無"] = "×未入力・対象外"
            else:
                warnings.append(f"R{rid}: 車数と車番が一致しないため◎→×無無を集計しません。")
                detail["◎→×無無"] = "車数不一致・対象外"
    # 3連複は配当未入力でも着順3車だけで判定。◎固定・残り2車の組合せ。
    trio_normal = parse_markline(raw_normal, "通常") if raw_normal else {}
    trio_value = parse_markline(raw_alpha, "妙味") if raw_alpha else {}
    if (len(trio_normal) == 5 and len(trio_value) >= 4
            and all(1 <= int(v) <= field_size for v in trio_normal.values())
            and all(1 <= int(v) <= field_size for v in trio_value.values())
            and all(1 <= int(v) <= field_size for v in finish[:3])):
        trio_unmarked = sorted(set(str(v) for v in range(1, field_size + 1)) - set(trio_normal.values()), key=int)
        if len(trio_unmarked) == field_size - 5:
            trio_axis = trio_normal["◎"]
            trio_others = sorted(({*trio_unmarked, trio_value.get("β"), trio_value.get("ε")} - {None, trio_axis}), key=int)
            trio_tickets = [frozenset((trio_axis, a, b)) for a, b in combinations(
                (str(v) for v in range(1, field_size + 1) if str(v) != trio_axis), 2
            ) if a in trio_others or b in trio_others]
            trio_hit = frozenset(finish[:3]) in trio_tickets
            # 2列目の資格（無・β・ε）と3列目の通常印を混同しない。
            # 2列目の車番を先に確定し、3列目は残りの車番を通常印で表示する。
            # 2列目に複数の該当車があるときは 無 > β > ε の優先順で一意に分類。
            # ◎－○－▲ のように2列目条件を満たさないラベルは生成しない。
            normal_by_car = {car: mark for mark, car in trio_normal.items()}
            candidate_by_car = {}
            for car in trio_unmarked:
                if car != trio_axis:
                    candidate_by_car[car] = "無"
            for candidate_mark in ("β", "ε"):
                car = trio_value.get(candidate_mark)
                if car and car != trio_axis and car not in candidate_by_car:
                    candidate_by_car[car] = candidate_mark

            def third_tag(car):
                return normal_by_car.get(car, "無")

            hit_ticket = frozenset(finish[:3]) if trio_hit else None
            hit_label = ""
            race_labels = set()
            race_ticket_labels = []
            for ticket in trio_tickets:
                others = ticket - {trio_axis}
                eligible = [(car, candidate_by_car[car]) for car in others if car in candidate_by_car]
                if not eligible:
                    raise AssertionError(f"R{rid}: 2列目候補を含まない買い目 {ticket}")
                # 同じ買い目を複数分類しない。無・β・ε の順に代表の2列目を選ぶ。
                candidate_car, candidate_mark = min(eligible, key=lambda t: ({"無": 0, "β": 1, "ε": 2}[t[1]], int(t[0])))
                third_car = next(iter(others - {candidate_car}))
                label = f"◎－{candidate_mark}－{third_tag(third_car)}"
                race_labels.add(label)
                race_ticket_labels.append(label)
                trio_symbol_stakes[label] = trio_symbol_stakes.get(label, 0) + 1
                if ticket == hit_ticket:
                    hit_label = label
                    trio_symbol_counts[label] = trio_symbol_counts.get(label, 0) + 1
                    trio_symbol_payouts[label] = trio_symbol_payouts.get(label, 0) + trio_pay
            # 各購入券がちょうど1つの記号分類に入っていることを検算。
            if len(race_ticket_labels) != len(trio_tickets):
                raise AssertionError(f"R{rid}: 3連複の記号別購入点数が一致しません")
            if trio_hit and not hit_label:
                raise AssertionError(f"R{rid}: 的中買い目の記号分類がありません")
            for label in race_labels:
                trio_symbol_races[label] = trio_symbol_races.get(label, 0) + 1
            if trio_hit:
                trio_total_payout += trio_pay
                if trio_pay == 0:
                    trio_missing_payouts += 1
                trio_symbol_details.append({"R": rid, "着順": "-".join(finish[:3]),
                                            "記号組合せ": hit_label,
                                            "3連複払戻": trio_pay})
            trio_stats["対象R"] += 1
            trio_stats["購入点数"] += len(trio_tickets)
            trio_stats["的中数"] += int(trio_hit)
            trio_stats["的中R"] += int(trio_hit)
            trio_detail.append({"R": rid, "◎": trio_axis, "相手候補": "・".join(trio_others),
                                "購入点数": len(trio_tickets), "着順": "-".join(finish[:3]),
                                "的中": "○" if trio_hit else "×", "3連複払戻": trio_pay if trio_hit else 0})
            detail["3連複 ◎－無無βε－全"] = "的中" if trio_hit else "外れ"
        else:
            detail["3連複 ◎－無無βε－全"] = "車数不一致・対象外"
    else:
        detail["3連複 ◎－無無βε－全"] = "印不足・対象外"
    # 2車複：◎と相手が1・2着なら的中（着順不問）。車番は既存の通常印から算出。
    q_marks = parse_markline(raw_normal, "通常") if raw_normal else {}
    if len(q_marks) == 5 and all(1 <= int(v) <= field_size for v in q_marks.values()):
        q_axis = q_marks["◎"]
        q_unmarked = sorted(set(str(v) for v in range(1, field_size + 1)) - set(q_marks.values()), key=int)
        q_pairs = [("◎－×", q_marks["×"])] + [("◎－無印合計", car) for car in q_unmarked]
        for q_label, q_other in q_pairs:
            q_rec = daily_quinella[q_label]
            q_rec["N"] += 1
            q_rec["KSUM"] += 1
            if {q_axis, q_other} == set(finish[:2]):
                q_rec["H"] += 1
                if quinella_pay > 0:
                    q_rec["SUM"] += quinella_pay
                else:
                    quinella_missing_payouts += 1
                    warnings.append(f"R{rid}: 2車複{q_label}が的中していますが、2車複払戻が未入力です。")
        detail["2車複 ◎－無印"] = "的中" if any({q_axis, car} == set(finish[:2]) for car in q_unmarked) else "外れ"
        detail["2車複 ◎－×"] = "的中" if {q_axis, q_marks["×"]} == set(finish[:2]) else "外れ"
    else:
        detail["2車複 ◎－無印"] = "印不足・対象外"
        detail["2車複 ◎－×"] = "印不足・対象外"
    wide_payout_map = parse_wide_payouts(wide_entries, finish, rid, warnings)
    # ◎－× ワイド：有効な通常印が揃ったレースのみ1点購入。
    x_marks = parse_markline(raw_normal, "通常") if raw_normal else {}
    if len(x_marks) == 5 and all(1 <= int(v) <= field_size for v in x_marks.values()):
        x_axis, x_car = x_marks["◎"], x_marks["×"]
        if x_axis != x_car:
            daily_wide_x["N"] += 1
            daily_wide_x["KSUM"] += 1
            x_hit = x_axis in finish[:3] and x_car in finish[:3]
            if x_hit:
                daily_wide_x["H"] += 1
                x_pair = frozenset((x_axis, x_car))
                if x_pair in wide_payout_map:
                    daily_wide_x["SUM"] += wide_payout_map[x_pair]
                else:
                    warnings.append(f"R{rid}: ワイド◎－×的中（{x_axis}-{x_car}）ですが払戻が未入力です。")
            detail["ワイド ◎－×"] = "的中" if x_hit else "外れ"
        else:
            detail["ワイド ◎－×"] = "不成立"
    else:
        detail["ワイド ◎－×"] = "印不足・対象外"
    # 無印は通常印5車が揃う場合のみ特定できる。◎－無印は1車ごとに100円。
    # ◎－無印∩β/εは無印車番とβまたはεが一致する場合のみ購入。
    um_marks = parse_markline(raw_normal, "通常") if raw_normal else {}
    value_marks = parse_markline(raw_alpha, "妙味") if raw_alpha else {}
    if len(um_marks) == 5 and all(1 <= int(v) <= field_size for v in um_marks.values()):
        um_cars = sorted(set(str(v) for v in range(1, field_size + 1)) - set(um_marks.values()), key=int)
        if len(um_cars) == field_size - 5:
            overlap = set(um_cars) & {value_marks.get("β"), value_marks.get("ε")}
            for idx, car in enumerate(um_cars, 1):
                for name in (f"◎－無印{idx}", "◎－無印合計") + (("◎－無印∩β/ε",) if car in overlap else ()):
                    rec = daily_wide_unmarked[name]
                    rec["N"] += 1
                    rec["KSUM"] += 1
                    if um_marks["◎"] in finish[:3] and car in finish[:3]:
                        rec["H"] += 1
                        pair_key = frozenset((um_marks["◎"], car))
                        if pair_key in wide_payout_map:
                            rec["SUM"] += wide_payout_map[pair_key]
                        else:
                            warnings.append(f"R{rid}: ワイド{name}的中（{um_marks['◎']}-{car}）ですが払戻が未入力です。")

    nm = parse_markline(raw_normal, "通常") if raw_normal else {}
    am = parse_markline(raw_alpha, "妙味") if raw_alpha else {}
    # ワイドは着順上位3車に◎とβ/εが両方入れば的中（順不同）。
    # 同一車番や印不足は不成立として購入点数に含めない。
    for target in WIDE_TARGETS:
        label = f"ワイド ◎－{target}"
        cars = [nm.get("◎"), am.get(target)]
        if any(c is None for c in cars) or len(set(cars)) != 2 or any(not (1 <= int(c) <= field_size) for c in cars):
            detail[label] = "不成立"
            continue
        rec = daily_wides[target]
        rec["N"] += 1
        rec["KSUM"] += 1
        hit = all(c in finish[:3] for c in cars)
        if hit:
            rec["H"] += 1
            pair = frozenset(cars)
            if pair in wide_payout_map:
                rec["SUM"] += wide_payout_map[pair]
            else:
                warnings.append(f"R{rid}: {label} 的中ですが、{cars[0]}-{cars[1]}のワイド払戻が未入力です。")
        detail[label] = "的中" if hit else "外れ"
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


total_wides = {key: add_records(carry_wides[key], daily_wides[key], ("N", "H", "SUM", "KSUM")) for key in daily_wides}

total_unmarked = {
    name: add_records(carry_unmarked[name], daily_unmarked[name], ("N", "H", "SUM", "KSUM"))
    for name in daily_unmarked
}


def unmarked_summary(records):
    """◎→×と無印を合計。実際に対象となった点数を分母にする。"""
    keys = ("◎→×", "◎→無印1", "◎→無印2")
    n = max(int(records[k]["N"]) for k in keys)
    ksum = sum(int(records[k]["KSUM"]) for k in keys)
    h = sum(int(records[k]["H"]) for k in keys)
    summ = sum(int(records[k]["SUM"]) for k in keys)
    return {"評価": "通常・穴相手", "3点セット": "◎→×・無印・無印", "対象R": int(n),
            "購入点数": ksum, "投資額": ksum * 100, "的中数": h,
            "平均的中配当": round(summ / h, 1) if h else None,
            "払戻合計": summ, "回収率%": pct(summ, ksum * 100)}


def unmarked_frame(records):
    return pd.DataFrame([bet_row(k, records[k]) for k in ("◎→×", "◎→無印1", "◎→無印2")])


def wide_unmarked_frame(records):
    return pd.DataFrame([bet_row(name, records[name]) for name in ("◎－無印合計", "◎－無印∩β/ε", "◎－無印1", "◎－無印2")])


def wide_frame(records):
    return pd.DataFrame([bet_row(f"◎－{m}", records[m]) for m in WIDE_TARGETS])


def wide_summary(records):
    selected = [records[m] for m in WIDE_TARGETS]
    n = max((int(r["N"]) for r in selected), default=0)
    ksum = sum(int(r["KSUM"]) for r in selected)
    h = sum(int(r["H"]) for r in selected)
    summ = sum(int(r["SUM"]) for r in selected)
    return {"券種": "ワイド", "買い方": "◎－β／ε", "対象R（最大）": n,
            "購入点数": ksum, "投資額": ksum * 100, "的中数": h,
            "的中率%（対象R比）": pct(h, n), "払戻合計": summ,
            "平均的中配当": round(summ / h, 1) if h else None,
            "回収率%": pct(summ, ksum * 100)}


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
        "対象R": int(n),
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
    # 比較表では◎→×の既存表裏集計を利用。引継ぎを二重入力させない。
    total_unmarked["◎→×"] = dict(total_bet_records["通常"][("◎", "×")])
    summary_df = pd.concat([summary_df, pd.DataFrame([unmarked_summary(total_unmarked)])], ignore_index=True)
    show_full_table(style_roi(summary_df))

    st.subheader("通常評価｜◎→×・無印・無印【累積】")
    st.caption("無印1・2は未評価車番の小さい順。6車立ては無印1車で2点、7車立ては3点。通常印5車が揃ったレースだけ無印を判定します。◎→×は上の既存集計を共用します。")
    show_full_table(style_roi(unmarked_frame(total_unmarked)))

    st.divider()
    st.divider()
    st.subheader("◎軸｜3連複 ◎－無・β・ε－全【本日入力分】")
    st.caption("買い目は◎－無・β・ε－全車。集計では各車の通常印（◎○▲△×）を優先し、通常無印は『無』に統一。3列目も実際の記号で表示します。")
    if sum(trio_symbol_stakes.values()) != trio_stats["購入点数"]:
        st.error("3連複の記号別購入点数が全体と一致しません。")
        st.stop()
    if sum(trio_symbol_counts.values()) != trio_stats["的中数"]:
        st.error("3連複の記号別的中数が全体と一致しません。")
        st.stop()
    if sum(trio_symbol_payouts.values()) != trio_total_payout:
        st.error("3連複の記号別払戻が全体と一致しません。")
        st.stop()
    trio_points = trio_stats["購入点数"]
    trio_races = trio_stats["対象R"]
    trio_cost = trio_points * 100
    trio_summary = pd.DataFrame([{
        "対象R": trio_races, "購入点数": trio_points,
        "的中R": trio_stats["的中R"],
        "的中率%": pct(trio_stats["的中R"], trio_races),
        "投資額": trio_cost, "払戻合計": trio_total_payout,
        "収支": trio_total_payout - trio_cost,
        "回収率%": pct(trio_total_payout, trio_cost),
        "払戻未入力の的中R": trio_missing_payouts,
    }])
    show_full_table(style_roi(trio_summary))
    if trio_missing_payouts:
        st.warning(f"3連複の的中{trio_missing_payouts}Rで払戻が未入力です。回収率は暫定値です。")
    st.markdown("**的中した記号の組み合わせ別集計**")
    st.caption("◎－無・β・ε－全の購入券だけを分類。2列目は無→β→εを優先し、3列目は通常印（○▲△×無）を表示。各券は1分類のみ。回収率は記号分類ごとの投資額（点数×100円）で計算。")
    symbol_table = pd.DataFrame([{
        "記号組合せ": k,
        "対象R": trio_symbol_races.get(k, 0),
        "購入点数": n,
        "投資額": n * 100,
        "的中数": trio_symbol_counts.get(k, 0),
        "的中率%（点数比）": pct(trio_symbol_counts.get(k, 0), n),
        "払戻合計": trio_symbol_payouts.get(k, 0),
        "収支": trio_symbol_payouts.get(k, 0) - n * 100,
        "回収率%": pct(trio_symbol_payouts.get(k, 0), n * 100),
    } for k, n in sorted(trio_symbol_stakes.items(), key=lambda kv: (-trio_symbol_counts.get(kv[0], 0), kv[0]))],
        columns=["記号組合せ", "対象R", "購入点数", "投資額", "的中数", "的中率%（点数比）", "払戻合計", "収支", "回収率%"])
    show_full_table(style_roi(symbol_table))
    with st.expander("3連複・記号組み合わせのレース別内訳"):
        if trio_symbol_details:
            show_full_table(style_roi(pd.DataFrame(trio_symbol_details)))
    with st.expander("3連複のレース別判定を見る"):
        if trio_detail:
            show_full_table(style_roi(pd.DataFrame(trio_detail)))

    st.subheader("◎軸｜2車複 ◎－無印／◎－×【本日入力分】")
    st.caption("◎－無印は通常印5車以外の全車を各100円で購入。◎－×は1点100円。両者が1・2着なら着順不問で的中。2車複払戻は1レース1組の金額を入力します。過去の引継ぎ分は含みません。")
    q_df = pd.DataFrame([bet_row(name, daily_quinella[name]) for name in ("◎－無印合計", "◎－×")])
    show_full_table(style_roi(q_df))
    if quinella_missing_payouts:
        st.warning(f"2車複の的中{quinella_missing_payouts}件で払戻が未入力です。回収率は暫定値です。")

    st.subheader("◎軸｜ワイド β／ε【累積】")
    st.caption("◎－βと◎－εを各100円で検証。◎と相手が同一車番の場合は不成立として除外。ワイド払戻は的中した車番の組ごとに個別入力します。")
    show_full_table(style_roi(pd.DataFrame([wide_summary(total_wides)])))
    show_full_table(style_roi(wide_frame(total_wides)))

    st.subheader("◎軸｜ワイド ◎－×【本日入力分】")
    st.caption("通常評価の◎と×を各レース100円で購入した想定。的中は両車が3着以内。既存のワイド車番・払戻3組を利用します。過去の引継ぎ分は含みません。")
    show_full_table(style_roi(pd.DataFrame([bet_row("◎－×", daily_wide_x)])))

    st.subheader("◎軸｜ワイド 無印・β/ε重複【本日入力分】")
    st.caption("通常印5車から無印を判定。◎－無印合計は無印1・2を各100円で購入した計算。重複抽出は無印とβまたはεが同じ車番の買い目だけ。過去の引継ぎ集計には無印ワイドの項目がないため、この表は日次入力分のみです。")
    show_full_table(style_roi(wide_unmarked_frame(daily_wide_unmarked)))

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
        today_unmarked = dict(daily_unmarked)
        today_df = pd.concat([today_df, pd.DataFrame([unmarked_summary(today_unmarked)])], ignore_index=True)
        st.markdown("#### 3点セット｜本日分")
        show_full_table(style_roi(today_df))
        st.markdown("#### ◎→×・無印・無印｜本日分")
        show_full_table(style_roi(unmarked_frame(today_unmarked)))
        st.markdown("#### ワイド ◎－無印・重複抽出｜本日分")
        show_full_table(style_roi(wide_unmarked_frame(daily_wide_unmarked)))
        st.markdown("#### ワイド ◎－β／ε｜本日分")
        show_full_table(style_roi(pd.DataFrame([wide_summary(daily_wides)])))
        show_full_table(style_roi(wide_frame(daily_wides)))
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
    st.download_button("3連複 記号組合せCSV", data=symbol_table.to_csv(index=False).encode("utf-8-sig"), file_name="velovi_trio_overlap_symbols.csv", mime="text/csv")
    st.download_button("3連複 ◎－無無βε－全 レース別CSV", data=pd.DataFrame(trio_detail, columns=["R", "◎", "相手候補", "購入点数", "着順", "的中", "3連複払戻"]).to_csv(index=False).encode("utf-8-sig"), file_name="velovi_trio_unmarked_beta_epsilon.csv", mime="text/csv")
    st.download_button(
        "◎→×・無印・無印 CSV",
        data=unmarked_frame(total_unmarked).to_csv(index=False).encode("utf-8-sig"),
        file_name="velovi_unmarked_exacta.csv", mime="text/csv"
    )
    st.download_button(
        "◎・α 3点セット比較CSV",
        data=summary_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="velovi_axis_3point_summary.csv", mime="text/csv"
    )
    st.download_button("2車複 ◎－無印／◎－× CSV", data=pd.DataFrame([bet_row(name, daily_quinella[name]) for name in ("◎－無印合計", "◎－×")]).to_csv(index=False).encode("utf-8-sig"), file_name="velovi_quinella_daily.csv", mime="text/csv")
    st.download_button("ワイド ◎－× CSV", data=pd.DataFrame([bet_row("◎－×", daily_wide_x)]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="velovi_wide_x_daily.csv", mime="text/csv")
    st.download_button("ワイド ◎－無印・重複抽出 CSV", data=wide_unmarked_frame(daily_wide_unmarked).to_csv(index=False).encode("utf-8-sig"),
                       file_name="velovi_wide_unmarked_daily.csv", mime="text/csv")
    st.download_button("ワイド ◎－β／ε CSV", data=wide_frame(total_wides).to_csv(index=False).encode("utf-8-sig"),
                       file_name="velovi_wide_beta_epsilon.csv", mime="text/csv")
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
