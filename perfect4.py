# -*- coding: utf-8 -*-
"""ヴェロビ集計｜通常◎・妙味α 集計版。

元の618行版を基準とした仕様:
- 通常 ◎○▲△× / 妙味 αβγεΩ の印着内率
- 2車単は各軸の表裏8通りだけ（通常◎、妙味α）
- 通常◎→○▲△ / 妙味α→γβε の3点セット集計
- 旧通常評価の入力キー・引継ぎキーを維持
- 日次100レース、除外、CSV、日次・累積レース別確認
"""
from typing import Dict, List, Tuple
import re
from itertools import combinations
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ集計｜◎・α比較", layout="wide")
st.title("ヴェロビ集計｜通常◎・妙味α 比較")
st.caption("通常評価と妙味軸評価を独立集計。◎→×・無印2車も比較。各買い目100円平買い換算。")

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

# 100Rの入力欄を50Rずつ描画する。ページ間の値はウィジェットとは別に保持。
import json

def _empty_race(i):
    return {"race": str(i), "normal": "", "alpha": "", "finish": "",
            "pay": 0, "quinella_pay": 0,
            "wide_entries": [["", 0] for _ in range(3)],
            "field_size": 7, "exclude": False}

if "velovi_saved_daily_50" not in st.session_state:
    _prior = [_empty_race(i) for i in range(1, 101)]
    # 旧100R画面から同じStreamlitセッションで切替えた場合、旧キーを引き継ぐ。
    for _i in range(1, 101):
        _r = _prior[_i - 1]
        for _field, _prefix in (("race", "rid"), ("normal", "mark"), ("alpha", "alpha_mark"), ("finish", "fin"), ("pay", "pay2t"), ("quinella_pay", "pay2f"), ("field_size", "field_size"), ("exclude", "exclude")):
            _r[_field] = st.session_state.get(f"{_prefix}_{_i}", _r[_field])
        for _j in range(1, 4):
            _r["wide_entries"][_j-1] = [st.session_state.get(f"wide_pair{_j}_{_i}", ""), st.session_state.get(f"wide_pay{_j}_{_i}", 0)]
    st.session_state["velovi_saved_daily_50"] = _prior

with tab_daily:
    st.caption("100Rの枠はそのまま、50Rずつ表示します。切り替える前に『この50Rを反映』を押してください。")
    page = st.radio("入力範囲", [0, 1], format_func=lambda p: "1～50R" if p == 0 else "51～100R", horizontal=True, key="velovi_50_page")
    start, end = page * 50, (page + 1) * 50
    page_rows = []
    with st.form(f"daily_input_form_50_{page}"):
        for i in range(start + 1, end + 1):
            old = st.session_state["velovi_saved_daily_50"][i-1]
            st.markdown(f"**{i}R**")
            c1, c2, c3 = st.columns([1.0, 2.0, 2.0])
            rid = c1.text_input("R番号", value=str(old["race"]), key=f"p{page}_rid_{i}")
            normal = c2.text_input("通常印順 ◎○▲△×", value=str(old["normal"]), key=f"p{page}_mark_{i}")
            alpha = c3.text_input("妙味印順 αβγεΩ", value=str(old["alpha"]), key=f"p{page}_alpha_{i}")
            c4, c5, c6, c7 = st.columns([1.6, 1.5, 1.0, 0.9])
            finish = c4.text_input("着順（3着まで）", value=str(old["finish"]), key=f"p{page}_fin_{i}")
            pay = c5.number_input("2車単払戻", min_value=0, value=int(old["pay"]), step=10, key=f"p{page}_pay2t_{i}")
            quinella_pay = c5.number_input("2車複払戻（100円）", min_value=0, value=int(old["quinella_pay"]), step=10, key=f"p{page}_pay2f_{i}")
            field_size = c6.selectbox("車数", [7, 6], index=0 if int(old["field_size"]) == 7 else 1, key=f"p{page}_field_size_{i}")
            exclude = c7.checkbox("集計除外", value=bool(old["exclude"]), key=f"p{page}_exclude_{i}")
            page_rows.append({"race": rid, "normal": normal, "alpha": alpha,
                "finish": finish, "pay": int(pay),
                "quinella_pay": int(quinella_pay), "wide_entries": old.get("wide_entries", [["", 0] for _ in range(3)]),
                "field_size": int(field_size), "exclude": bool(exclude)})
            st.divider()
        submitted_50 = st.form_submit_button("この50Rを反映")
    if submitted_50:
        st.session_state["velovi_saved_daily_50"][start:end] = page_rows
        st.success(f"{start+1}～{end}Rを反映しました。")
    daily_rows = st.session_state["velovi_saved_daily_50"]
    st.download_button("入力内容をバックアップ（JSON）", data=json.dumps({"daily_rows": daily_rows}, ensure_ascii=False).encode("utf-8"), file_name="velovi_input_backup.json", mime="application/json")
    upload = st.file_uploader("入力バックアップを復元（JSON）", type=["json"], key="velovi_restore_50")
    if st.button("バックアップを復元", disabled=upload is None):
        try:
            payload = json.loads(upload.getvalue().decode("utf-8"))
            rows = payload["daily_rows"]
            if not isinstance(rows, list) or len(rows) != 100:
                raise ValueError("100R分のデータではありません")
            st.session_state["velovi_saved_daily_50"] = [{**_empty_race(i), **r} for i, r in enumerate(rows, 1)]
            # 既存ウィジェットキーを破棄し、復元データから入力欄を再生成する。
            for key in list(st.session_state.keys()):
                if key.startswith(("p0_", "p1_")):
                    del st.session_state[key]
            st.rerun()
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            st.error(f"復元できません: {exc}")


# ============================================================
# B. 引継ぎ（旧通常評価の入力キーを維持）
# ============================================================
carry_mark_records = {g: blank_group_marks(g) for g in GROUP_MARKS}
carry_bet_records = {g: blank_group_bets(g) for g in GROUP_MARKS}
carry_unmarked = {name: blank_unmarked() for name in ("◎→×", "◎→無印1", "◎→無印2")}

daily_quinella_labels = ('◎－○', '◎－▲', '◎－△', '◎－×', '◎－無印合計', '◎－β', '◎－ε')
carry_quinella_all = {g:{} for g in GROUP_MARKS}
carry_quinella_named = {}

# 保存・復元はセッション外でも使える明示的なJSONバックアップで行う。
# Streamlit Cloudではローカルファイルの永続性を保証できないため、
# サーバー内ファイルへの自動保存だけに依存しない。
CARRY_KEY_PREFIXES = (
    "carry_mark_", "alpha_carry_mark_", "carry_", "pair_carry_",
    "alpha_carry_", "unmarked_", "wide_carry_", "carry_qall_",
    "carry_qnamed_", "carry_wextra_",
)


def export_complete_backup():
    carry = {}
    for key, value in st.session_state.items():
        if isinstance(key, str) and key.startswith(CARRY_KEY_PREFIXES) and isinstance(value, (int, float, str, bool)):
            carry[key] = int(value) if isinstance(value, (int, float)) else value
    return {
        "format": "velovi_complete_backup_v1",
        "daily_rows": st.session_state["velovi_saved_daily_50"],
        "carry_values": carry,
    }


def restore_complete_backup(payload):
    if not isinstance(payload, dict):
        raise ValueError("バックアップ形式が不正です")
    rows = payload.get("daily_rows")
    carry = payload.get("carry_values")
    if not isinstance(rows, list) or len(rows) != 100:
        raise ValueError("日次データが100R分ありません")
    if not isinstance(carry, dict):
        raise ValueError("引継ぎ値が含まれていません。日次のみの旧バックアップです")
    clean_carry = {}
    for key, value in carry.items():
        if not isinstance(key, str) or not key.startswith(CARRY_KEY_PREFIXES):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
            raise ValueError(f"引継ぎ値が不正です: {key}")
        clean_carry[key] = int(value)
    new_rows = []
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"日次{i}Rの形式が不正です")
        new_rows.append({**_empty_race(i), **row})
    st.session_state["velovi_saved_daily_50"] = new_rows
    # 復元ファイルにない過去値が混ざらないように初期化する。
    for key in list(st.session_state):
        if isinstance(key, str) and (key.startswith(CARRY_KEY_PREFIXES) or key.startswith(("p0_", "p1_"))):
            del st.session_state[key]
    st.session_state.update(clean_carry)


with tab_carry:
    st.subheader("前日までの集計（累積・引継ぎ）")
    st.warning("引継ぎ値はセッション内だけでは永続保存されません。入力後に下部の『日次＋引継ぎをまとめてバックアップ』を保存し、次回はここから復元してください。")
    restored_file = st.file_uploader("日次＋前日までの集計を復元（完全バックアップJSON）", type=["json"], key="velovi_complete_restore_file")
    if st.button("完全バックアップを復元", disabled=restored_file is None, key="velovi_complete_restore_button"):
        try:
            restore_complete_backup(json.loads(restored_file.getvalue().decode("utf-8")))
            st.rerun()
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            st.error(f"完全バックアップを復元できません: {exc}")
    st.caption(
        "通常評価は旧版の印別1～3着回数と、◎を含む2車単表裏8通りを転記。"
        "妙味評価はα軸の成績を新規入力。旧版の他の2車単は転記不要です。"
        "引継ぎ対象Nは各印・買い目ごとに入力できます。"
    )
    st.markdown("""#### まず入力する数字の意味
**過去分**とは、今回の「日次入力」に入っていないレースの集計です。日次欄にも同じレースを残している場合、引継ぎにも入れると二重計上になります。

| 項目 | 入力する値 | 例：過去44Rで◎－▲が7回的中、払戻計1,920円 |
|---|---|---|
| 対象R（対象N） | その買い目を判定できた過去レース数 | **44** |
| 購入点数 | 対象期間にその買い目を各100円で買ったと仮定した合計口数 | **44**（毎R1点なら対象Rと同じ） |
| 的中数（的中H） | その買い目が当たった回数 | **7** |
| 払戻合計（SUM） | 当たり券の**100円あたりの払戻金を合計**した金額 | **1,920** |

上の例は「**通常評価・2車複の◎－▲**」の欄に **44 / 7 / 1920** と入れます。回収率は自動計算されるので入力不要です。

**入力元：** 以前の集計アプリに表示された「対象R・購入点数・的中数・払戻合計」を、**同じ券種・同じ印の組み合わせ**の欄へ転記してください。**2車単と2車複、通常印と妙味印は別物**です。過去の集計値が分からない欄は **0のまま**にし、推測値を入れないでください。
""")
    st.warning("重要：下の『全21組』と『記号別比較』は同じレースを別の切り口で示す**別々の集計表**です。それぞれの過去集計がある場合だけ転記します。両方へ入力しても各表の中で二重加算はしません。『無印合計』は1Rにつき通常2点（7車立て）、個別の『無印1』『無印2』は各1点です。")
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
        st.markdown("### 2車複｜全組み合わせ（過去分引継ぎ）")
        st.caption("列は左から【組み合わせ｜対象R｜的中数｜払戻合計（円）】。通常と妙味を別々に入力。7車立ての各組は1R1点なので購入点数＝対象Rです。例：◎－▲なら 44｜7｜1920。")
        for cg in GROUP_MARKS:
            with st.expander(f"{cg}評価・2車複21組の引継ぎ"):
                for ca, cb in combinations(list(GROUP_MARKS[cg]) + ["無印1", "無印2"], 2):
                    cc = st.columns([2, 1, 1, 1])
                    cc[0].markdown(f"{ca}－{cb}")
                    ck = f"carry_qall_{'n' if cg == '通常' else 'v'}_{ca}_{cb}"
                    cn = cc[1].number_input("対象R", min_value=0, key=ck+"_n", label_visibility="collapsed")
                    ch = cc[2].number_input("的中数", min_value=0, key=ck+"_h", label_visibility="collapsed")
                    cs = cc[3].number_input("払戻合計", min_value=0, step=10, key=ck+"_sum", label_visibility="collapsed")
                    carry_quinella_all[cg][(ca, cb)] = {"N":int(cn), "H":int(ch), "SUM":int(cs), "KSUM":int(cn)}
        st.markdown("### 2車複｜記号別比較（過去分引継ぎ）")
        st.caption("列は【買い目｜対象R｜購入点数｜的中数｜払戻合計（円）】。◎－無印合計は無印1・2を両方買うため、7車44Rなら対象R44・購入点数88。◎－▲は44・44・7・1920。上の全21組の数字をこちらへ**自動転記はしません**。元データがある行だけ入力してください。")
        for label in daily_quinella_labels:
            cc = st.columns([2, 1, 1, 1, 1])
            cc[0].markdown(label)
            ck = f"carry_qnamed_{label}"
            cn = cc[1].number_input("対象R", min_value=0, key=ck+"_n", label_visibility="collapsed")
            cp = cc[2].number_input("購入点数", min_value=0, key=ck+"_points", label_visibility="collapsed")
            ch = cc[3].number_input("的中数", min_value=0, key=ck+"_h", label_visibility="collapsed")
            cs = cc[4].number_input("払戻合計", min_value=0, step=10, key=ck+"_sum", label_visibility="collapsed")
            carry_quinella_named[label] = {"N":int(cn), "H":int(ch), "SUM":int(cs), "KSUM":int(cp)}
        st.form_submit_button("前日までの集計を反映")
    st.download_button(
        "日次＋引継ぎをまとめてバックアップ（JSON）",
        data=json.dumps(export_complete_backup(), ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="velovi_complete_backup.json", mime="application/json",
        key="velovi_complete_backup_download",
    )
    st.caption("バックアップには日次100Rと印着内率、2車単、2車複の引継ぎ入力値を含みます。引継ぎ値の変更後は再度ダウンロードしてください。")


# ============================================================
# C. 日次集計（除外・部分入力・払い戻しチェック）
# ============================================================
daily_mark_records = {g: blank_group_marks(g) for g in GROUP_MARKS}
daily_bet_records = {g: blank_group_bets(g) for g in GROUP_MARKS}
daily_unmarked = {name: blank_unmarked() for name in ("◎→×", "◎→無印1", "◎→無印2")}
daily_quinella = {name: blank_bet() for name in ('◎－○', '◎－▲', '◎－△', '◎－×', '◎－無印合計', '◎－β', '◎－ε')}
quinella_missing_payouts = 0
# 全2車複：通常／妙味それぞれの5印＋残り無印を全組み合わせで検証。
# 集計は日次入力のみ。引継ぎの集計値から未記録の組み合わせは復元できない。
quinella_all_records = {g: {} for g in GROUP_MARKS}
quinella_all_races = {g: 0 for g in GROUP_MARKS}
quinella_all_missing = {g: 0 for g in GROUP_MARKS}
quinella_all_order = {g: list(GROUP_MARKS[g]) + ["無印1", "無印2"] for g in GROUP_MARKS}
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
    quinella_pay = int(entry.get("quinella_pay", 0))
    field_size = int(entry["field_size"])
    exclude = bool(entry["exclude"])

    if not any([raw_normal, raw_alpha, raw_finish, payout > 0, quinella_pay > 0, exclude]):
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
    # 2車複・全通り：各評価の5印＋無印1・2で全21通り（6車なら15通り）。
    # 無印1・2は、その評価で印のない車番を小さい順に割り当てる。
    # 同一レースで各評価は別集計。的中は1組のみで、払戻は2車複入力を使う。
    for q_group, q_raw in (("通常", raw_normal), ("妙味", raw_alpha)):
        q_all_marks = parse_markline(q_raw, q_group) if q_raw else {}
        if len(q_all_marks) != 5 or not all(1 <= int(v) <= field_size for v in q_all_marks.values()):
            continue
        if not all(1 <= int(v) <= field_size for v in finish[:2]):
            continue
        q_remaining = sorted(set(str(v) for v in range(1, field_size + 1)) - set(q_all_marks.values()), key=int)
        if len(q_remaining) != field_size - 5:
            continue
        q_labeled = dict(q_all_marks)
        q_labeled.update({f"無印{i}": car for i, car in enumerate(q_remaining, 1)})
        q_order = [label for label in quinella_all_order[q_group] if label in q_labeled]
        quinella_all_races[q_group] += 1
        for left, right in combinations(q_order, 2):
            key = (left, right)
            rec = quinella_all_records[q_group].setdefault(key, blank_bet())
            rec["N"] += 1
            rec["KSUM"] += 1
            if {q_labeled[left], q_labeled[right]} == set(finish[:2]):
                rec["H"] += 1
                if quinella_pay > 0:
                    rec["SUM"] += quinella_pay
                else:
                    quinella_all_missing[q_group] += 1
                    warnings.append(f"R{rid}: {q_group}2車複 {left}－{right} 的中ですが払戻未入力です。")

    # 2車複：通常印4～5車、妙味印4～5車。車番が重なる買い目も分類ごとに独立検証。
    q_marks = parse_markline(raw_normal, "通常") if raw_normal else {}
    q_value_marks = parse_markline(raw_alpha, "妙味") if raw_alpha else {}
    q_valid = (len(q_marks) in (4, 5) and "◎" in q_marks
               and all(1 <= int(v) <= field_size for v in q_marks.values()))
    if q_valid:
        q_axis = q_marks["◎"]
        q_unmarked = sorted(set(str(v) for v in range(1, field_size + 1)) - set(q_marks.values()), key=int)
        q_pairs = [(f"◎－{mark}", q_marks[mark]) for mark in ("○", "▲", "△", "×") if mark in q_marks]
        q_pairs += [("◎－無印合計", car) for car in q_unmarked]
        if len(q_value_marks) in (4, 5):
            q_pairs += [(f"◎－{mark}", q_value_marks[mark]) for mark in ("β", "ε") if mark in q_value_marks]
        q_results = {name: False for name in daily_quinella}
        for q_label, q_other in q_pairs:
            if q_axis == q_other or not 1 <= int(q_other) <= field_size:
                continue
            q_rec = daily_quinella[q_label]
            q_rec["N"] += 1
            q_rec["KSUM"] += 1
            if {q_axis, q_other} == set(finish[:2]):
                q_rec["H"] += 1
                q_results[q_label] = True
                if quinella_pay > 0:
                    q_rec["SUM"] += quinella_pay
                else:
                    quinella_missing_payouts += 1
                    warnings.append(f"R{rid}: 2車複{q_label}が的中していますが、2車複払戻が未入力です。")
        for q_label in daily_quinella:
            detail[f"2車複 {q_label}"] = "的中" if q_results[q_label] else "外れ・対象外"
    else:
        for q_label in daily_quinella:
            detail[f"2車複 {q_label}"] = "印不足・対象外"
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
# 累積：既存の日次集計に過去引継ぎを加算（入力済みの過去分を二重に入れないこと）。
quinella_all_total = {g:{} for g in GROUP_MARKS}
for g in GROUP_MARKS:
    for pair in set(quinella_all_records[g]) | set(carry_quinella_all[g]):
        quinella_all_total[g][pair] = add_records(quinella_all_records[g].get(pair, blank_bet()), carry_quinella_all[g].get(pair, blank_bet()), ("N","H","SUM","KSUM"))
# 「全21組」と「記号別比較」のどちらに前日分を入力しても◎軸累積へ反映。
# 同一買い目の二重加算を防止するため、記号別比較が入力済みなら優先する。
def sum_bets(records):
    """同じ軸からの異なる買い目を各100円ずつ購入した合算。"""
    selected = list(records)
    if not selected:
        return blank_bet()
    return {"N": max(int(r["N"]) for r in selected),
            "KSUM": sum(int(r["KSUM"]) for r in selected),
            "H": sum(int(r["H"]) for r in selected),
            "SUM": sum(int(r["SUM"]) for r in selected)}


def past_named_quinella(label):
    named = carry_quinella_named.get(label, blank_bet())
    if any(int(named.get(field, 0)) for field in ("N", "H", "SUM", "KSUM")):
        return named
    if label == "◎－無印合計":
        pieces = [carry_quinella_all["通常"].get(("◎", m), blank_bet()) for m in ("無印1", "無印2")]
        return sum_bets(pieces)
    if label in ("◎－○", "◎－▲", "◎－△", "◎－×"):
        return carry_quinella_all["通常"].get(("◎", label.split("－", 1)[1]), blank_bet())
    # 妙味印と通常◎との重なりは過去の各レース情報なしには再構成できない。
    return named

quinella_named_total = {
    name: add_records(daily_quinella[name], past_named_quinella(name), ("N", "H", "SUM", "KSUM"))
    for name in daily_quinella
}
def compact_result(name, rec):
    """結果一覧に必要な項目だけを表示。的中率は対象R基準。"""
    r = bet_row(name, rec)
    return {"買い方": name, "対象R": r["対象R"], "購入点数": r["購入点数"],
            "的中R": r["的中数"], "的中率%": r["的中率%"],
            "投資額": r["投資額"], "払戻合計": r["払戻合計"],
            "収支": r["払戻合計"] - r["投資額"], "回収率%": r["回収率%"]}




with tab_result:
    st.subheader("累積成績｜◎軸の結果")
    st.caption(f"本日有効：通常{valid_races['通常']}R／妙味{valid_races['妙味']}R・除外{excluded_races}R。過去引継ぎと本日入力を合算。1点100円換算。")

    # 2車単は通常◎の1着固定、2車複は通常◎を含む組み合わせだけ。
    exacta_diamond = sum_bets(
        total_bet_records["通常"][("◎", m)] for m in GROUP_MARKS["通常"][1:]
    )
    # 2車複の過去引継ぎは「記号別比較」側にも存在する。
    # 全21組の引継ぎが未入力でも、◎軸の記号別引継ぎから累積を表示する。
    # 引継ぎは記号別入力優先、未入力時だけ21組を参照し二重加算を防ぐ。
    quinella_diamond = sum_bets(
        quinella_named_total[label] for label in
        ("◎－○", "◎－▲", "◎－△", "◎－×", "◎－無印合計")
    )
    # 妙味評価はα軸の買い目別記録を使用。2車複は21組の引継ぎと日次入力を合算。
    exacta_alpha = sum_bets(
        total_bet_records["妙味"][("α", m)] for m in GROUP_MARKS["妙味"][1:]
    )
    quinella_alpha = sum_bets(
        quinella_all_total["妙味"][("α", m)] for m in GROUP_MARKS["妙味"][1:]
    )
    primary = pd.DataFrame([
        compact_result("2車単 ◎→全", exacta_diamond),
        compact_result("2車単 α→全", exacta_alpha),
        compact_result("2車複 ◎－全", quinella_diamond),
        compact_result("2車複 α－全", quinella_alpha),
    ])
    show_full_table(style_roi(primary))
    st.caption("通常◎軸と妙味α軸を別々に集計。2車単は各4点、2車複のα軸は印相手4点。過去分は対応する引継ぎ欄を反映します。")

    st.subheader("2車単｜◎軸・買い目別【累積】")
    # ◎以外の軸→全は作らず、個別買い目は常時一覧表示。
    exacta_rows = [compact_result(f"◎→{m}", total_bet_records["通常"][("◎", m)])
                   for m in GROUP_MARKS["通常"][1:]]
    exacta_rows += [compact_result(name, total_unmarked[name])
                    for name in ("◎→無印1", "◎→無印2")]
    show_full_table(style_roi(pd.DataFrame(exacta_rows)))

    st.subheader("2車複｜◎軸・買い目別【累積】")
    q_df = pd.DataFrame([compact_result(name, quinella_named_total[name])
                         for name in daily_quinella_labels])
    show_full_table(style_roi(q_df))
    if quinella_missing_payouts:
        st.warning(f"2車複：的中{quinella_missing_payouts}件で払戻未入力。回収率は暫定値です。")

    st.subheader("2車単｜妙味評価 α軸・買い目別【累積】")
    value_exacta_rows = [compact_result(f"α→{m}", total_bet_records["妙味"][("α", m)])
                          for m in GROUP_MARKS["妙味"][1:]]
    show_full_table(style_roi(pd.DataFrame(value_exacta_rows)))

    st.subheader("2車複｜妙味評価 α軸・買い目別【累積】")
    value_quinella_rows = [compact_result(f"α－{m}", quinella_all_total["妙味"][("α", m)])
                            for m in GROUP_MARKS["妙味"][1:]]
    show_full_table(style_roi(pd.DataFrame(value_quinella_rows)))
    st.caption("妙味2車複は『全組み合わせ（過去分引継ぎ）』の妙味評価欄を使用します。未入力の過去分は0として扱います。")

    st.subheader("印着内率【累積】")
    for group in GROUP_MARKS:
        st.markdown(f"**{group}評価**")
        show_full_table(mark_frame(group, total_mark_records).style.format({
            "1着率%": "{:.1f}", "連対率%": "{:.1f}", "印着内率%": "{:.1f}"
        }, na_rep="—"))

    quinella_all_exports = {}
    with st.expander("2車複｜全組み合わせの詳細（◎軸以外も含む）", expanded=False):
        st.caption("こちらは21組の個別検証です。上の◎軸累積表とは引継ぎ入力欄が別です。")
        for q_group in GROUP_MARKS:
            q_rows = []
            for left, right in combinations(quinella_all_order[q_group], 2):
                rec = quinella_all_total[q_group].get((left, right))
                if rec and rec["N"]:
                    q_rows.append(compact_result(f"{left}－{right}", rec))
            q_individual_df = pd.DataFrame(q_rows, columns=list(compact_result("", blank_bet()).keys()))
            quinella_all_exports[q_group] = q_individual_df
            st.markdown(f"**{q_group}評価**")
            show_full_table(style_roi(q_individual_df))

    summary_df = pd.DataFrame([set_summary(g, total_bet_records) for g in GROUP_MARKS])
    total_unmarked["◎→×"] = dict(total_bet_records["通常"][("◎", "×")])
    summary_df = pd.concat([summary_df, pd.DataFrame([unmarked_summary(total_unmarked)])], ignore_index=True)

    with st.expander("本日分だけの成績", expanded=False):
        today_df = pd.DataFrame([set_summary(group, daily_bet_records) for group in GROUP_MARKS])
        show_full_table(style_roi(today_df))
        show_full_table(style_roi(unmarked_frame(daily_unmarked)))
        for group in GROUP_MARKS:
            st.markdown(f"**{group}評価｜本日の印着内率**")
            show_full_table(mark_frame(group, daily_mark_records))

    if warnings:
        st.warning("\n".join(warnings[:25]) + ("\n…" if len(warnings) > 25 else ""))
    if race_details:
        with st.expander("本日のレース別判定を確認"):
            show_full_table(pd.DataFrame(race_details).fillna(""))

    st.divider()
    st.download_button("◎・α軸｜2車単・2車複 集計CSV", data=primary.to_csv(index=False).encode("utf-8-sig"), file_name="velovi_diamond_axis.csv", mime="text/csv")

    st.subheader("個別CSV（必要な場合のみ）")
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
    st.download_button("2車複 記号別比較 CSV", data=pd.DataFrame([bet_row(name, quinella_named_total[name]) for name in daily_quinella]).to_csv(index=False).encode("utf-8-sig"), file_name="velovi_quinella_daily.csv", mime="text/csv")
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

    for q_group, q_export in quinella_all_exports.items():
        st.download_button(f"{q_group}・2車複 個別CSV", data=q_export.to_csv(index=False).encode("utf-8-sig"), file_name=f"velovi_quinella_{'normal' if q_group == '通常' else 'value'}.csv", mime="text/csv")
