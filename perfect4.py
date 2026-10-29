# -*- coding: utf-8 -*-
"""惑星理論・独立検証集計 v2

ヴェロビ予想本体には一切依存しない Streamlit 集計アプリ。
- 太陽 / 惑星 / 衛星(複数) / 彗星(複数・任意) と 通常評価 ◎○▲△× を入力
- レース単位で2車複・3連複の的中率、実点数に応じた回収率を算出
- 衛星は優劣を付けず、惑星－衛星など一括フォーメーションとして判定
- 彗星は既存方式には含めず、新規の太陽系／◎▲固定3連複でのみ3車目候補に含める
- 通常評価の印1着、連対、3着内率および◎－▲の2車複を別枠集計
- 日次100R (50件ページ)、前日引継ぎ、完全JSONバックアップ、CSV出力
- 100円均等購入の仮想検証。実購入とは区別する。
"""
from __future__ import annotations
from collections import Counter
from itertools import combinations
import json
import re
from typing import Any
import pandas as pd
import streamlit as st

st.set_page_config(page_title="惑星理論｜独立検証集計", layout="wide")
st.title("惑星理論｜独立検証集計")
st.caption("予想本体とは独立。既存の惑星固定3連複は彗星を除外。追加の太陽系3連複・◎▲固定3連複のみ彗星を3車目候補に含めます。すべて1点100円の仮想平買い。")

MARKS = ("◎", "○", "▲", "△", "×")
BET_NAMES = ("2車複 太陽－惑星", "2車複 太陽－衛星", "2車複 惑星－衛星", "2車複 ◎－▲（別枠）", "3連複 惑星－（太陽・衛星）－（太陽・衛星）", "3連複 太陽－惑星－（衛星・彗星）", "3連複 ◎－▲－（太陽・惑星・衛星・彗星）")
SESSIONS = ("モーニング", "デイ", "ナイター", "ミッドナイト")
SCOPES = ("男子・通常開催", "男子・ミッドナイト", "ガールズ・通常開催", "ガールズ・ミッドナイト")


def initial_row(i: int) -> dict:
    return {"race": str(i), "session": "デイ", "girls": False,
            "sun": "", "planet": "", "satellites": "", "comets": "", "normal": "", "finish": "",
            "quinella_pay": 0, "trio_pay": 0, "exclude": False}


def initial_summary() -> dict:
    return {"bets": {key: {"n": 0, "h": 0, "points": 0, "paid": 0, "missing": 0} for key in BET_NAMES},
            "marks": {m: {"n": 0, "c1": 0, "c2": 0, "c3": 0} for m in MARKS},
            "race_count": 0}


def clean_cars(raw: Any) -> str:
    return "".join(c for c in str(raw or "") if c in "123456789")


def parse_cars(raw: Any, *, max_count: int, exact: int | None = None) -> list[str]:
    vals = list(clean_cars(raw))
    if len(vals) > max_count or len(vals) != len(set(vals)) or (exact is not None and len(vals) != exact):
        raise ValueError("車番が重複しているか、桁数が不正です")
    return vals


def ordered_marks(raw: Any) -> dict[str, str]:
    chars = parse_cars(raw, max_count=5)
    if len(chars) not in (0, 4, 5):
        raise ValueError("通常評価は空欄、または◎○▲△×順の4〜5車番で入力してください")
    return dict(zip(MARKS, chars))


def scope_for(row: dict) -> str:
    return ("ガールズ" if row.get("girls") else "男子") + "・" + ("ミッドナイト" if row.get("session") == "ミッドナイト" else "通常開催")


def pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def trip(a: str, b: str, c: str) -> tuple[str, str, str]:
    return tuple(sorted((a, b, c)))


def build_bets(sun: str, planet: str, satellites: list[str], comets: list[str], marks: dict[str, str]) -> dict[str, set[tuple]]:
    sat = set(satellites)
    pool = sorted({sun, *sat})
    bets = {
        BET_NAMES[0]: {pair(sun, planet)},
        BET_NAMES[1]: {pair(sun, s) for s in sat},
        BET_NAMES[2]: {pair(planet, s) for s in sat},
        BET_NAMES[3]: set(),
        BET_NAMES[4]: {trip(planet, a, b) for a, b in combinations(pool, 2)},
        BET_NAMES[5]: {trip(sun, planet, car) for car in set(satellites + comets)},
        BET_NAMES[6]: set(),
    }
    if "◎" in marks and "▲" in marks and marks["◎"] != marks["▲"]:
        bets[BET_NAMES[3]] = {pair(marks["◎"], marks["▲"])}
        bets[BET_NAMES[6]] = {trip(marks["◎"], marks["▲"], car) for car in {sun, planet, *satellites, *comets}}
    # 予想本体とは無関係。誤入力などの重複車番を含む組合せは除去。
    return {k: {v for v in group if len(set(v)) == len(v)} for k, group in bets.items()}


def process(row: dict) -> tuple[dict | None, list[str]]:
    warnings: list[str] = []
    fields = ("sun", "planet", "satellites", "comets", "normal", "finish", "quinella_pay", "trio_pay")
    if row.get("exclude"):
        return None, warnings
    if not any(str(row.get(x, "")).strip() not in ("", "0") for x in fields):
        return None, warnings
    rid = str(row.get("race", "")).strip()
    try:
        finish = parse_cars(row.get("finish", ""), max_count=3, exact=3)
        sun = parse_cars(row.get("sun", ""), max_count=1, exact=1)[0]
        planet = parse_cars(row.get("planet", ""), max_count=1, exact=1)[0]
        sat = parse_cars(row.get("satellites", ""), max_count=7)
        comets = parse_cars(row.get("comets", ""), max_count=7)
        marks = ordered_marks(row.get("normal", ""))
        if sun == planet or any(s in (sun, planet) for s in sat):
            raise ValueError("太陽・惑星・衛星の車番に重複があります")
        if any(c in {sun, planet, *sat} for c in comets):
            raise ValueError("彗星の車番が太陽・惑星・衛星と重複しています")
        universe = {sun, planet, *sat, *comets, *finish, *marks.values()}
        if any(v not in "1234567" for v in universe):
            raise ValueError("車番は1〜7の範囲で入力してください")
        if not sat:
            raise ValueError("衛星を1車以上入力してください")
        qpay = int(row.get("quinella_pay") or 0)
        tpay = int(row.get("trio_pay") or 0)
        if qpay < 0 or tpay < 0:
            raise ValueError("払戻額は0以上で入力してください")
    except (ValueError, TypeError, IndexError) as e:
        return None, [f"{rid}：{e}"]

    qresult = pair(finish[0], finish[1])
    tresult = tuple(sorted(finish))
    bets = build_bets(sun, planet, sat, comets, marks)
    detail = {"R": row.get("race", ""), "開催": row.get("session", "デイ"), "区分": scope_for(row),
              "太陽": sun, "惑星": planet, "衛星": "".join(sat), "彗星": "".join(comets), "通常評価": row.get("normal", ""),
              "着順": "-".join(finish), "2車複配当": qpay, "3連複配当": tpay,
              "bets": {}, "marks": marks}
    for key, candidates in bets.items():
        triple = key.startswith("3連複")
        won = (tresult if triple else qresult) in candidates if candidates else False
        paid = tpay if triple else qpay
        if won and paid <= 0:
            warnings.append(f"{rid}：{key}が的中しましたが払戻額が0です。回収率は未確定扱いにします")
        detail["bets"][key] = {"n": int(bool(candidates)), "h": int(won), "points": len(candidates),
                                "paid": paid if won else 0, "missing": int(won and paid <= 0),
                                "formation": " / ".join("-".join(x) for x in sorted(candidates))}
    return detail, warnings


def add_summary(target: dict, source: dict) -> None:
    for bet in BET_NAMES:
        for k in ("n", "h", "points", "paid", "missing"):
            target["bets"][bet][k] += int(source.get("bets", {}).get(bet, {}).get(k, 0))
    for mark in MARKS:
        for k in ("n", "c1", "c2", "c3"):
            target["marks"][mark][k] += int(source.get("marks", {}).get(mark, {}).get(k, 0))
    target["race_count"] += int(source.get("race_count", 0))


def from_details(details: list[dict]) -> dict:
    result = initial_summary()
    for d in details:
        result["race_count"] += 1
        for bet, rec in d["bets"].items():
            for field in ("n", "h", "points", "paid", "missing"):
                result["bets"][bet][field] += rec[field]
        for mark, car in d["marks"].items():
            result["marks"][mark]["n"] += 1
            f = d["着順"].split("-")
            if car in f:
                result["marks"][mark][f"c{f.index(car)+1}"] += 1
    return result


def percent(a: int, b: int) -> float | None:
    return round(a * 100 / b, 2) if b else None


def bet_table(s: dict) -> pd.DataFrame:
    rows = []
    for name, r in s["bets"].items():
        investment = r["points"] * 100
        rows.append({"方式": name, "対象R": r["n"], "的中R": r["h"],
                     "的中率%": percent(r["h"], r["n"]), "購入点数": r["points"],
                     "投資額": investment, "払戻額": r["paid"],
                     "収支": r["paid"] - investment if not r["missing"] else None,
                     "回収率%": percent(r["paid"], investment) if not r["missing"] else None,
                     "配当未入力R": r["missing"]})
    return pd.DataFrame(rows)


def mark_table(s: dict) -> pd.DataFrame:
    rows=[]
    for mark, r in s["marks"].items():
        n=r["n"]
        rows.append({"印": mark, "対象R": n, "1着": r["c1"], "2着": r["c2"], "3着": r["c3"],
                     "1着率%": percent(r["c1"], n), "連対率%": percent(r["c1"]+r["c2"], n),
                     "3着内率%": percent(r["c1"]+r["c2"]+r["c3"], n)})
    return pd.DataFrame(rows)


if "planet_daily_rows_v1" not in st.session_state:
    st.session_state["planet_daily_rows_v1"] = [initial_row(i) for i in range(1,101)]
if "planet_carry_v1" not in st.session_state:
    st.session_state["planet_carry_v1"] = {s: initial_summary() for s in SCOPES}


def clear_widget_cache():
    for key in list(st.session_state):
        if key.startswith("pv1_row_"):
            del st.session_state[key]


def make_backup() -> bytes:
    return json.dumps({"format": "planet_theory_aggregate_v1", "daily_rows": st.session_state["planet_daily_rows_v1"],
                       "carry": st.session_state["planet_carry_v1"]}, ensure_ascii=False, indent=2).encode("utf-8")


def restore_backup(blob: bytes):
    payload = json.loads(blob.decode("utf-8"))
    if payload.get("format") != "planet_theory_aggregate_v1":
        raise ValueError("惑星理論集計v1のバックアップではありません。元の集計コードのJSONと混同しないでください")
    rows = payload.get("daily_rows")
    carry = payload.get("carry")
    if not isinstance(rows, list) or len(rows) != 100 or not isinstance(carry, dict):
        raise ValueError("日次100Rまたは引継ぎデータが不正です")
    new_rows=[]
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"{i}件目の入力が不正です")
        new_rows.append({**initial_row(i), **row})
    new_carry = {scope: initial_summary() for scope in SCOPES}
    for scope, s in carry.items():
        if scope not in new_carry or not isinstance(s, dict):
            raise ValueError("引継ぎ区分が不正です")
        for bet in BET_NAMES:
            data = s.get("bets", {}).get(bet, {})
            for k in ("n", "h", "points", "paid", "missing"):
                v = data.get(k, 0)
                if not isinstance(v, int) or v < 0:
                    raise ValueError("引継ぎ数値が不正です")
                new_carry[scope]["bets"][bet][k] = v
        for mark in MARKS:
            for k in ("n", "c1", "c2", "c3"):
                v = s.get("marks", {}).get(mark, {}).get(k, 0)
                if not isinstance(v, int) or v < 0:
                    raise ValueError("引継ぎ印数値が不正です")
                new_carry[scope]["marks"][mark][k] = v
        new_carry[scope]["race_count"] = int(s.get("race_count", 0))
    st.session_state["planet_daily_rows_v1"] = new_rows
    st.session_state["planet_carry_v1"] = new_carry
    clear_widget_cache()


tab_daily, tab_carry, tab_results = st.tabs(["日次入力", "引継ぎ・バックアップ", "集計結果"])
with tab_daily:
    st.info("50件ずつ入力し、必ず『この50件を反映』を押してください。日次バックアップには反映済みデータだけが入ります。")
    page = st.radio("入力範囲", (0,1), format_func=lambda i: "1〜50件" if i == 0 else "51〜100件", horizontal=True)
    start=page*50
    incoming=[]
    with st.form(f"pv1_form_{page}"):
        for idx in range(start, start+50):
            r=st.session_state["planet_daily_rows_v1"][idx]
            st.markdown(f"**入力枠 {idx+1}**")
            c=st.columns([.75, 1.5, .85, .9])
            race=c[0].text_input("R",value=str(r.get("race", "")),key=f"pv1_row_{idx}_race")
            session=c[1].selectbox("時間帯",SESSIONS,index=SESSIONS.index(r.get("session","デイ")) if r.get("session") in SESSIONS else 1,key=f"pv1_row_{idx}_session")
            girls=c[2].checkbox("ガールズ",value=bool(r.get("girls",False)),key=f"pv1_row_{idx}_girls")
            exclude=c[3].checkbox("集計除外",value=bool(r.get("exclude",False)),key=f"pv1_row_{idx}_exclude")
            c=st.columns([.7,.7,1.1,1.1,1.4,1.0])
            sun=c[0].text_input("太陽",value=str(r.get("sun","")),key=f"pv1_row_{idx}_sun")
            planet=c[1].text_input("惑星",value=str(r.get("planet","")),key=f"pv1_row_{idx}_planet")
            satellites=c[2].text_input("衛星（複数可）",value=str(r.get("satellites","")),key=f"pv1_row_{idx}_satellites")
            comets=c[3].text_input("彗星（任意・複数可）",value=str(r.get("comets","")),key=f"pv1_row_{idx}_comets")
            normal=c[4].text_input("通常印 ◎○▲△×",value=str(r.get("normal","")),key=f"pv1_row_{idx}_normal")
            finish=c[5].text_input("着順1〜3着",value=str(r.get("finish","")),key=f"pv1_row_{idx}_finish")
            c=st.columns(2)
            qpay=c[0].number_input("2車複払戻（100円につき）",value=max(0,int(r.get("quinella_pay") or 0)),step=10,min_value=0,key=f"pv1_row_{idx}_qpay")
            tpay=c[1].number_input("3連複払戻（100円につき）",value=max(0,int(r.get("trio_pay") or 0)),step=10,min_value=0,key=f"pv1_row_{idx}_tpay")
            incoming.append({"race":race,"session":session,"girls":girls,"exclude":exclude,
                             "sun":sun,"planet":planet,"satellites":satellites,"comets":comets,"normal":normal,
                             "finish":finish,"quinella_pay":int(qpay),"trio_pay":int(tpay)})
            st.divider()
        submitted=st.form_submit_button("この50件を反映",type="primary")
    if submitted:
        st.session_state["planet_daily_rows_v1"][start:start+50]=incoming
        st.success("50件を反映しました。バックアップの保存もお忘れなく。")

with tab_carry:
    st.warning("Streamlitのセッション情報は永続保存ではありません。完全バックアップJSONを保存して次回復元してください。旧集計コードのバックアップ形式とは別です。")
    st.download_button("日次＋引継ぎを完全バックアップ（JSON）",make_backup(),file_name="planet_aggregate_complete_v1.json",mime="application/json")
    uploaded=st.file_uploader("惑星理論集計v1バックアップを復元",type=["json"])
    if st.button("完全バックアップを復元",disabled=uploaded is None):
        try:
            restore_backup(uploaded.getvalue())
            st.success("復元しました")
            st.rerun()
        except (ValueError,TypeError,KeyError,UnicodeError) as e:
            st.error(str(e))
    st.subheader("日次データを引継ぎに確定")
    st.caption("日次100件の有効レースを区分別の累積に加え、日次を空欄にします。バックアップしてから実施してください。同じ日次データを二重確定しない設計です。")
    confirm=st.checkbox("日次を引継ぎへ移し、日次欄を消去することを確認しました",key="pv1_confirm_roll")
    if st.button("日次を引継ぎに確定してクリア",disabled=not confirm):
        details=[];errs=[]
        for row in st.session_state["planet_daily_rows_v1"]:
            d,ws=process(row)
            errs.extend(ws)
            if d: details.append(d)
        if errs:
            st.error("不正入力・配当未入力があります。引継ぎを中止しました。集計結果の警告を確認してください。")
        elif not details:
            st.info("確定するレースがありません")
        else:
            for scope in SCOPES:
                summary=from_details([d for d in details if d["区分"]==scope])
                add_summary(st.session_state["planet_carry_v1"][scope],summary)
            st.session_state["planet_daily_rows_v1"]=[initial_row(i) for i in range(1,101)]
            clear_widget_cache()
            st.success(f"{len(details)}Rを引継ぎました。新しい完全バックアップを保存してください。")
            st.rerun()
    st.subheader("引継ぎ累積の確認")
    for scope in SCOPES:
        with st.expander(scope):
            s=st.session_state["planet_carry_v1"][scope]
            st.caption(f"引継ぎ対象レース：{s['race_count']}R")
            st.dataframe(bet_table(s),hide_index=True,use_container_width=True)
            st.dataframe(mark_table(s),hide_index=True,use_container_width=True)

with tab_results:
    division=st.radio("種別",("全レース","男子","ガールズ"),horizontal=True)
    session_sel=st.radio("開催区分",("全開催","通常開催","ミッドナイト"),horizontal=True)
    def matched(scope: str) -> bool:
        return ((division=="全レース" or scope.startswith(division)) and
                (session_sel=="全開催" or scope.endswith(session_sel)))
    details=[];warnings=[]
    for row in st.session_state["planet_daily_rows_v1"]:
        d,ws=process(row)
        warnings.extend(ws)
        if d:details.append(d)
    chosen=[d for d in details if matched(d["区分"])]
    total=from_details(chosen)
    for scope in SCOPES:
        if matched(scope):add_summary(total,st.session_state["planet_carry_v1"][scope])
    st.metric("累積対象レース",total["race_count"])
    st.subheader("惑星理論｜買い目別（複数衛星は一括集計）")
    st.caption("各方式で1Rに複数点あっても、当たれば的中Rは1。投資は全成立点数×100円。従来方式は変更せず、新3連複2方式を独立追加。◎－▲軸方式は通常評価を用いる別枠検証です。")
    bets_frame=bet_table(total)
    st.dataframe(bets_frame,hide_index=True,use_container_width=True)
    st.download_button("買い目別集計CSV",bets_frame.to_csv(index=False).encode("utf-8-sig"),file_name="planet_bet_summary.csv",mime="text/csv")
    st.subheader("通常評価｜印別着内率（惑星理論の車券判定には不使用）")
    marks_frame=mark_table(total)
    st.dataframe(marks_frame,hide_index=True,use_container_width=True)
    st.download_button("印着内率CSV",marks_frame.to_csv(index=False).encode("utf-8-sig"),file_name="planet_mark_summary.csv",mime="text/csv")
    if warnings:
        st.warning("\n".join(warnings[:30])+("\n…" if len(warnings)>30 else ""))
    if chosen:
        st.subheader("日次レース別検証明細")
        rows=[]
        for d in chosen:
            entry={k:v for k,v in d.items() if k not in ("bets","marks")}
            for bet,rec in d["bets"].items():
                entry[bet+" 買い目"]=rec["formation"]
                entry[bet+" 点数"]=rec["points"]
                entry[bet+" 的中"]="○" if rec["h"] else "×"
            rows.append(entry)
        frame=pd.DataFrame(rows)
        st.dataframe(frame,hide_index=True,use_container_width=True)
        st.download_button("レース別検証CSV",frame.to_csv(index=False).encode("utf-8-sig"),file_name="planet_daily_details.csv",mime="text/csv")
    st.caption("旧ヴェロビ集計アプリの履歴や引継ぎ数字を自動移行していません。異なる方式のデータを混ぜないためです。")
