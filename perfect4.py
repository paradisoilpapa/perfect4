# -*- coding: utf-8 -*-

from collections import defaultdict
from typing import List, Dict, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ヴェロビ復習（全体累積）", layout="wide")
st.title("ヴェロビ 復習（全体累積）｜2車複ゾーン追加・フルコード版")

# =========================
# 基本設定（7車ベース）
# =========================
FIELD_SIZE = 7
WINNER_RANKS = tuple(range(1, 8))
PATTERN_AXES = (1,)
AXIS1_TARGETS = (2, 3)
INDIVIDUAL_AXIS1_TARGETS = (2, 3)
AXIS2_TARGETS = ()
AXIS3_TARGETS = ()

# 2車複：個別引継ぎ用ペア。
# 既存の1軸・2軸に加えて、評価3軸・評価4軸の下位絡みを検証するため、
# 3-4/5/6/7 と 4-5/6/7 も累積対象に入れます。
NISHAFUKU_PAIRS = [
    # 軸1に必要なペア
    (1, 2), (1, 3), (1, 4),
    (1, 5), (1, 6), (1, 7),

    # 軸2に必要なペア
    (2, 3), (2, 4),
    (2, 5), (2, 6), (2, 7),

    # 評価3軸・4軸の追加検証ペア
    (3, 4), (3, 5), (3, 6), (3, 7),
    (4, 5), (4, 6), (4, 7),
]
NISHAFUKU_EXTRA_PAIRS = []

# 小倉ミッドナイトA級7車・直近2年ベースのペア別平均配当（100円あたり）。
# 必要に応じて画面上で上書きできます。
PAIR_BASE_AVG_PAY_DEFAULTS = {
    "1-2": 271,
    "1-3": 436,
    "1-4": 654,
    "1-5": 1059,
    "1-6": 1754,
    "1-7": 1519,
    "2-3": 881,
    "2-4": 1333,
    "2-5": 1869,
    "2-6": 1657,
    "2-7": 4092,
}

# 小倉ミッドナイトA級7車・直近2年ベースの固定想定的中率（%）。
# 母数738R：1-2=167回、1-3=105回、1-4=78回、1-5=38回、1-6=26回、1-7=35回、
# 2-3=46回、2-4=42回、2-5=27回、2-6=15回、2-7=22回。
# 現在入力中の的中率とは独立した「想定ペア的%」として使用します。
PAIR_BASE_HIT_RATE_DEFAULTS = {
    "1-2": 22.6,
    "1-3": 14.2,
    "1-4": 10.6,
    "1-5": 5.1,
    "1-6": 3.5,
    "1-7": 4.7,
    "2-3": 6.2,
    "2-4": 5.7,
    "2-5": 3.7,
    "2-6": 2.0,
    "2-7": 3.0,
}

# 3連複 1-2-全の固定想定値。
# 小倉ミッドナイトA級7車・直近2年の3連複全集計より、
# 1-2-3=101回/平均378円、1-2-4=88回/537円、
# 1-2-5=57回/1053円、1-2-6=44回/1136円、1-2-7=30回/1545円。
TRIO_12_ALL_BASE_COUNTS = {
    "1-2-3": 101,
    "1-2-4": 88,
    "1-2-5": 57,
    "1-2-6": 44,
    "1-2-7": 30,
}
TRIO_12_ALL_BASE_AVG_PAYS = {
    "1-2-3": 378,
    "1-2-4": 537,
    "1-2-5": 1053,
    "1-2-6": 1136,
    "1-2-7": 1545,
}

# 小倉ミッドナイトA級7車・直近2年の3連複全集計。
# 候補（評価3～7）の基準複勝率を作るために使用します。
# 3-5-7は表に出ていないため0回として扱います。
TRIO_FULL_BASE_COUNTS = {
    "1-2-3": 101,
    "1-2-4": 88,
    "1-2-5": 57,
    "1-3-5": 48,
    "1-2-6": 44,
    "1-3-4": 43,
    "1-2-7": 30,
    "1-4-5": 29,
    "1-3-6": 24,
    "2-4-5": 23,
    "2-3-4": 21,
    "2-3-5": 20,
    "1-4-7": 19,
    "1-5-6": 19,
    "1-4-6": 19,
    "3-4-5": 16,
    "2-3-6": 13,
    "2-4-6": 13,
    "1-6-7": 11,
    "2-5-6": 11,
    "1-3-7": 11,
    "2-3-7": 10,
    "3-4-7": 9,
    "3-4-6": 9,
    "4-5-7": 8,
    "2-4-7": 8,
    "1-5-7": 7,
    "2-5-7": 7,
    "2-6-7": 6,
    "3-5-6": 5,
    "3-5-7": 0,
    "4-6-7": 2,
    "3-6-7": 2,
    "4-5-6": 2,
    "5-6-7": 1,
}
# 小倉ミッドナイトA級7車・直近2年の3連複平均配当（100円あたり）。
TRIO_FULL_BASE_AVG_PAYS = {
    "1-2-3": 378,
    "1-2-4": 537,
    "1-2-5": 1053,
    "1-3-5": 985,
    "1-2-6": 1136,
    "1-3-4": 619,
    "1-2-7": 1545,
    "1-4-5": 2019,
    "1-3-6": 2749,
    "2-4-5": 2441,
    "2-3-4": 2258,
    "2-3-5": 1824,
    "1-4-7": 3296,
    "1-5-6": 3177,
    "1-4-6": 1519,
    "3-4-5": 2789,
    "2-3-6": 4772,
    "2-4-6": 2102,
    "1-6-7": 6155,
    "2-5-6": 4138,
    "1-3-7": 2146,
    "2-3-7": 5106,
    "3-4-7": 5373,
    "3-4-6": 2188,
    "4-5-7": 6251,
    "2-4-7": 3241,
    "1-5-7": 3550,
    "2-5-7": 3524,
    "2-6-7": 5575,
    "3-5-6": 1102,
    "3-5-7": 0,
    "4-6-7": 19765,
    "3-6-7": 7830,
    "4-5-6": 3250,
    "5-6-7": 14080,
}

# 小倉2年分の3連複集計母数。
# 2車複基準と揃えるため738Rを基準にします。
TRIO_BASE_TOTAL_RACES = 738

TRIO_BASE_PLACE_COUNTS = {r: 0 for r in range(1, FIELD_SIZE + 1)}
for _trio_key, _cnt in TRIO_FULL_BASE_COUNTS.items():
    for _r in [int(x) for x in _trio_key.split("-")]:
        TRIO_BASE_PLACE_COUNTS[_r] += int(_cnt)

# 小倉2年分3連複全集計から逆算した評価別基準複勝率。
# 3連複1-2個別表では、1・2は軸として固定済みなので、評価3～7だけ補正に使います。
TRIO_BASE_PLACE_RATES = {
    r: round(100.0 * cnt / TRIO_BASE_TOTAL_RACES, 1)
    for r, cnt in TRIO_BASE_PLACE_COUNTS.items()
}


def place_state(diff) -> str:
    """評価別3着内率の基準差を状態表示する。"""
    if diff is None:
        return ""
    try:
        d = float(diff)
    except Exception:
        return ""
    if d >= 5.0:
        return "来すぎ"
    if d <= -5.0:
        return "基準未満"
    return "中庸"

TRIO_12_ALL_EXPECTED_AVG_PAY = round(
    sum(TRIO_12_ALL_BASE_COUNTS[k] * TRIO_12_ALL_BASE_AVG_PAYS[k] for k in TRIO_12_ALL_BASE_COUNTS)
    / max(1, sum(TRIO_12_ALL_BASE_COUNTS.values())),
    1,
)

# 3連複は実データの回数から想定率を置く。
# 以前の「2車複1-2×3」は理論近似だが、実測の3連複基準では高く出すぎるため使わない。
TRIO_12_INDIVIDUAL_EXPECTED_HIT_RATES = {
    k: round(100.0 * v / TRIO_BASE_TOTAL_RACES, 1)
    for k, v in TRIO_12_ALL_BASE_COUNTS.items()
}
TRIO_12_ALL_EXPECTED_HIT_RATE = round(
    100.0 * sum(TRIO_12_ALL_BASE_COUNTS.values()) / TRIO_BASE_TOTAL_RACES,
    1,
)
TRIO_12_ALL_EXPECTED_ROI = round((TRIO_12_ALL_EXPECTED_HIT_RATE / 100.0) * TRIO_12_ALL_EXPECTED_AVG_PAY / 500.0 * 100.0, 1)
TRIO_12_INDIVIDUAL_EXPECTED_ROIS = {
    k: round(TRIO_12_INDIVIDUAL_EXPECTED_HIT_RATES[k] * TRIO_12_ALL_BASE_AVG_PAYS[k] / 100.0, 1)
    for k in TRIO_12_ALL_BASE_COUNTS
}

TRIO_FULL_EXPECTED_HIT_RATES = {
    k: round(100.0 * v / TRIO_BASE_TOTAL_RACES, 1)
    for k, v in TRIO_FULL_BASE_COUNTS.items()
}
TRIO_FULL_EXPECTED_ROIS = {
    k: round(TRIO_FULL_EXPECTED_HIT_RATES[k] * TRIO_FULL_BASE_AVG_PAYS.get(k, 0) / 100.0, 1)
    for k in TRIO_FULL_BASE_COUNTS
}


# 実運用で3連複の軸候補にする2車複ペア。
# 現実的に使うのは、想定ペア的中率が高く、軸として成立しやすい5候補まで。
# これ以外の2車複本線が出ても、3連複軸には使わない。
TRIO_AXIS_ALLOWED_KEYS = ["1-2", "1-3", "1-4", "2-3", "2-4"]


def _trio_key_from_parts(a: int, b: int, c: int) -> str:
    return "-".join(str(x) for x in sorted([int(a), int(b), int(c)]))


def _build_trio_used_keys(axis_keys):
    keys = []
    seen = set()
    for axis_key in axis_keys:
        try:
            a, b = [int(x) for x in axis_key.split("-")]
        except Exception:
            continue
        for target in range(1, FIELD_SIZE + 1):
            if target in (a, b):
                continue
            key = _trio_key_from_parts(a, b, target)
            if key in TRIO_FULL_BASE_COUNTS and key not in seen:
                keys.append(key)
                seen.add(key)
    return keys


# 実運用で累積転記する3連複キー。
# 小倉基準計算には全35通りを使うが、手入力・引継ぎは上記5軸から派生する目だけに絞る。
TRIO_USED_KEYS = _build_trio_used_keys(TRIO_AXIS_ALLOWED_KEYS)



RANK_SYMBOLS = {
    1: "評価１",
    2: "評価２",
    3: "評価３",
    4: "評価４",
    5: "評価５",
    6: "評価６",
    7: "評価７",
}


def rank_symbol(r: int) -> str:
    return RANK_SYMBOLS.get(r, f"評価{r}")


PairKey = Tuple[int, int]  # (winner_eval, second_eval)


def parse_rankline(s: str, expected_len: int) -> List[str]:
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    if not s.isdigit() or len(s) != expected_len:
        return []
    if any(ch not in "1234567" for ch in s):
        return []
    if len(set(s)) != len(s):
        return []
    return list(s)


def parse_finish(s: str) -> List[str]:
    if not s:
        return []
    s = s.replace("-", "").replace(" ", "").replace("/", "").replace(",", "")
    s = "".join(ch for ch in s if ch in "1234567")
    out: List[str] = []
    for ch in s:
        if ch not in out:
            out.append(ch)
        if len(out) == 3:
            break
    return out


def build_conditional_tables(pair_counts: Dict[PairKey, int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = list(range(1, FIELD_SIZE + 1))
    count_rows = []
    pct_rows = []

    for wr in WINNER_RANKS:
        total = 0
        for rr in cols:
            if rr == wr:
                continue
            total += int(pair_counts.get((wr, rr), 0))

        row_c = {"1着の評価": wr, "N": total}
        for rr in cols:
            row_c[str(rr)] = None if rr == wr else int(pair_counts.get((wr, rr), 0))
        count_rows.append(row_c)

        row_p = {"1着の評価": wr, "N": total}
        for rr in cols:
            if rr == wr:
                row_p[str(rr)] = None
            else:
                v = int(pair_counts.get((wr, rr), 0))
                row_p[str(rr)] = round(100.0 * v / total, 1) if total > 0 else 0.0
        pct_rows.append(row_p)

    return pd.DataFrame(count_rows), pd.DataFrame(pct_rows)


def rate(x: int, n: int):
    return round(100.0 * x / n, 1) if n > 0 else None


def payout_zone_key(pay: int) -> str | None:
    """2車複払戻（100円あたり）を的中ゾーンへ分類する。"""
    try:
        pay = int(pay)
    except Exception:
        return None
    if pay <= 0:
        return None
    odds = pay / 100.0
    if odds <= 3.0:
        return "Z3"
    if odds <= 6.0:
        return "Z6"
    if odds <= 10.0:
        return "Z10"
    if odds <= 20.0:
        return "Z20"
    return "Z20P"


def zone_text(count: int, total_h: int) -> str:
    count = int(count or 0)
    total_h = int(total_h or 0)
    if total_h <= 0:
        return "0/0%"
    return f"{count}/{round(100.0 * count / total_h, 1)}%"


def zone_row(pair: str, rec: Dict[str, int]) -> Dict:
    H = int(rec.get("H", 0))
    z3 = int(rec.get("Z3", 0))
    z6 = int(rec.get("Z6", 0))
    z10 = int(rec.get("Z10", 0))
    z20 = int(rec.get("Z20", 0))
    z20p = int(rec.get("Z20P", 0))
    zsum = z3 + z6 + z10 + z20 + z20p
    return {
        "ペア": pair,
        "的中H": H,
        "〜3倍": zone_text(z3, H),
        "3.1〜6倍": zone_text(z6, H),
        "6.1〜10倍": zone_text(z10, H),
        "10.1〜20倍": zone_text(z20, H),
        "20.1倍〜": zone_text(z20p, H),
        "ゾーン確認": "OK" if (H == 0 or zsum == H) else f"不一致({zsum}/{H})",
    }


def zone_total_row(recs: List[Dict[str, int]]) -> Dict:
    """個別2車複 的中ゾーン分布の総合行。全ペアの的中Hを合算して比率を出す。"""
    total = new_payout_rec()
    for rec in recs:
        for k in ("H", "Z3", "Z6", "Z10", "Z20", "Z20P"):
            total[k] = int(total.get(k, 0)) + int(rec.get(k, 0))
    H = int(total.get("H", 0))
    z3 = int(total.get("Z3", 0))
    z6 = int(total.get("Z6", 0))
    z10 = int(total.get("Z10", 0))
    z20 = int(total.get("Z20", 0))
    z20p = int(total.get("Z20P", 0))
    zsum = z3 + z6 + z10 + z20 + z20p
    return {
        "ペア": "総合",
        "的中H": H,
        "〜3倍": zone_text(z3, H),
        "3.1〜6倍": zone_text(z6, H),
        "6.1〜10倍": zone_text(z10, H),
        "10.1〜20倍": zone_text(z20, H),
        "20.1倍〜": zone_text(z20p, H),
        "ゾーン確認": "OK" if (H == 0 or zsum == H) else f"不一致({zsum}/{H})",
    }


def build_conditional_tables_13(pair_counts: Dict[PairKey, int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = list(range(1, FIELD_SIZE + 1))
    count_rows = []
    pct_rows = []

    for wr in WINNER_RANKS:
        total = 0
        for rr in cols:
            if rr == wr:
                continue
            total += int(pair_counts.get((wr, rr), 0))

        row_c = {"1着の評価": wr, "N": total}
        row_p = {"1着の評価": wr, "N": total}
        for rr in cols:
            col = f"3着={rr}"
            if rr == wr:
                row_c[col] = None
                row_p[col] = None
            else:
                v = int(pair_counts.get((wr, rr), 0))
                row_c[col] = v
                row_p[col] = round(100.0 * v / total, 1) if total > 0 else 0.0
        count_rows.append(row_c)
        pct_rows.append(row_p)

    return pd.DataFrame(count_rows), pd.DataFrame(pct_rows)


def new_payout_rec() -> Dict[str, int]:
    # Z3   : 的中払戻 〜3.0倍（〜300円）
    # Z6   : 的中払戻 3.1〜6.0倍（310〜600円）
    # Z10  : 的中払戻 6.1〜10.0倍（610〜1000円）
    # Z20  : 的中払戻 10.1〜20.0倍（1010〜2000円）
    # Z20P : 的中払戻 20.1倍〜（2010円〜）
    return {
        "N": 0, "KSUM": 0, "H": 0, "SUM": 0,
        "Z3": 0, "Z6": 0, "Z10": 0, "Z20": 0, "Z20P": 0,
    }


def add_rec(dst: Dict[str, int], src: Dict[str, int]):
    for k in ("N", "KSUM", "H", "SUM", "Z3", "Z6", "Z10", "Z20", "Z20P"):
        dst[k] += int(src.get(k, 0))


def combine_recs(recs: List[Dict[str, int]]) -> Dict[str, int]:
    """
    同じレース群に対する複数買い目の合算。
    Nは足さず、最大Nを使う。
    KSUM/H/SUMは合算する。
    """
    out = new_payout_rec()
    out["N"] = max((int(r.get("N", 0)) for r in recs), default=0)
    for rec in recs:
        out["KSUM"] += int(rec.get("KSUM", 0))
        out["H"] += int(rec.get("H", 0))
        out["SUM"] += int(rec.get("SUM", 0))
    return out


def ksum_sanrenpuku_12_all(field_n: int) -> int:
    """3連複：評価1-評価2-全。7車なら5点、6車なら4点、5車なら3点。"""
    try:
        return max(0, int(field_n) - 2)
    except Exception:
        return 0


def hit_sanrenpuku_12_all(vorder: List[str], finish: List[str], field_n: int) -> bool:
    """3連複 1-2-全：評価1と評価2がともに3着内なら的中。"""
    if ksum_sanrenpuku_12_all(field_n) <= 0:
        return False
    if not vorder or len(finish) < 3:
        return False
    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}
    finish_ranks = {car_to_rank.get(car) for car in finish[:3]}
    return 1 in finish_ranks and 2 in finish_ranks




def sanrenpuku12_key(a: int, b: int, c: int) -> str:
    vals = sorted([int(a), int(b), int(c)])
    return f"{vals[0]}-{vals[1]}-{vals[2]}"


def ksum_sanrenpuku_12_individual(target: int, field_n: int) -> int:
    """3連複：評価1-評価2-target の1点。"""
    try:
        target = int(target)
        field_n = int(field_n)
    except Exception:
        return 0
    if field_n < 3:
        return 0
    if target in (1, 2):
        return 0
    if target > field_n:
        return 0
    return 1


def hit_sanrenpuku_12_individual(target: int, vorder: List[str], finish: List[str], field_n: int) -> bool:
    """3連複：評価1・評価2・target が3着内にそろえば的中。"""
    if ksum_sanrenpuku_12_individual(target, field_n) <= 0:
        return False
    if not vorder or len(finish) < 3:
        return False
    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}
    finish_ranks = {car_to_rank.get(car) for car in finish[:3]}
    return {1, 2, int(target)}.issubset(finish_ranks)


def ksum_sanrenpuku_key(key: str, field_n: int) -> int:
    """3連複：評価キー（例 2-4-7）の1点。欠車時は存在する評価だけ有効。"""
    try:
        vals = [int(x) for x in str(key).split("-")]
        field_n = int(field_n)
    except Exception:
        return 0
    if len(vals) != 3 or len(set(vals)) != 3:
        return 0
    if field_n < 3:
        return 0
    if any(v < 1 or v > field_n for v in vals):
        return 0
    return 1


def hit_sanrenpuku_key(key: str, vorder: List[str], finish: List[str], field_n: int) -> bool:
    """3連複：指定評価3つが3着内にそろえば的中。"""
    if ksum_sanrenpuku_key(key, field_n) <= 0:
        return False
    if not vorder or len(finish) < 3:
        return False
    try:
        vals = {int(x) for x in str(key).split("-")}
    except Exception:
        return False
    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}
    finish_ranks = {car_to_rank.get(car) for car in finish[:3]}
    return vals.issubset(finish_ranks)


def sanrenpuku_individual_row(label: str, rec: Dict[str, int], key: str) -> Dict:
    """任意3連複個別用の表示行。小倉基準で想定差・回収差を見る。"""
    row = payout_row(label, rec)
    exp_rate = TRIO_FULL_EXPECTED_HIT_RATES.get(key)
    exp_avg_pay = TRIO_FULL_BASE_AVG_PAYS.get(key)
    exp_roi = TRIO_FULL_EXPECTED_ROIS.get(key)

    row["目"] = key
    row["想定的中率%"] = exp_rate
    row["基準平均配当"] = exp_avg_pay
    row["想定回収率%"] = exp_roi

    hit_rate = row.get("的中率%")
    avg_pay = row.get("平均配当")
    roi = row.get("回収率%")

    if hit_rate is not None and pd.notna(hit_rate) and exp_rate is not None:
        row["想定差"] = round(float(hit_rate) - float(exp_rate), 1)
    else:
        row["想定差"] = None
    row["状態"] = diff_status(row.get("想定差"), exp_rate)

    if avg_pay is not None and pd.notna(avg_pay) and exp_avg_pay:
        row["配当係数"] = round(float(avg_pay) / float(exp_avg_pay), 2)
        row["平均配当差"] = round(float(avg_pay) - float(exp_avg_pay), 1)
        if row["配当係数"] < 0.80:
            row["配当位置"] = "安すぎ"
            row["配当戻り余地"] = "あり"
        elif row["配当係数"] <= 1.30:
            row["配当位置"] = "基準付近"
            row["配当戻り余地"] = "中庸"
        else:
            row["配当位置"] = "高すぎ"
            row["配当戻り余地"] = "上振れ警戒"
    else:
        row["配当係数"] = None
        row["平均配当差"] = None
        row["配当位置"] = "未回収"
        row["配当戻り余地"] = ""

    if roi is not None and pd.notna(roi) and exp_roi is not None:
        row["回収差"] = round(float(roi) - float(exp_roi), 1)
    else:
        row["回収差"] = None

    reasons = []
    if row.get("的中H", 0) == 0:
        reasons.append("未回収除外")
    if row.get("状態") == "当たりすぎ":
        reasons.append("的中率過熱除外")
    if row.get("配当位置") == "高すぎ":
        reasons.append("配当上振れ警戒")
    if row.get("回収差") is not None and row.get("回収差") > 20:
        reasons.append("後追い除外")
    if not reasons:
        if row.get("配当位置") == "安すぎ":
            reasons.append("歪み枠")
        elif row.get("状態") == "中庸":
            reasons.append("中庸枠")
        else:
            reasons.append("候補")
    row["総合候補理由"] = "／".join(reasons)
    return row


def sanrenpuku12_individual_row(label: str, rec: Dict[str, int], key: str) -> Dict:
    """3連複1-2個別用の表示行。2車複表と同じように想定差・回収差を見る。"""
    row = payout_row(label, rec)
    exp_rate = TRIO_12_INDIVIDUAL_EXPECTED_HIT_RATES.get(key)
    exp_avg_pay = TRIO_12_ALL_BASE_AVG_PAYS.get(key)
    exp_roi = TRIO_12_INDIVIDUAL_EXPECTED_ROIS.get(key)

    row["目"] = key
    row["想定的中率%"] = exp_rate
    row["基準平均配当"] = exp_avg_pay
    row["想定回収率%"] = exp_roi

    hit_rate = row.get("的中率%")
    avg_pay = row.get("平均配当")
    roi = row.get("回収率%")

    if hit_rate is not None and pd.notna(hit_rate) and exp_rate is not None:
        row["想定差"] = round(float(hit_rate) - float(exp_rate), 1)
    else:
        row["想定差"] = None
    row["状態"] = diff_status(row.get("想定差"), exp_rate)

    if avg_pay is not None and pd.notna(avg_pay) and exp_avg_pay:
        row["配当係数"] = round(float(avg_pay) / float(exp_avg_pay), 2)
        row["平均配当差"] = round(float(avg_pay) - float(exp_avg_pay), 1)
        if row["配当係数"] < 0.80:
            row["配当位置"] = "安すぎ"
            row["配当戻り余地"] = "あり"
        elif row["配当係数"] <= 1.30:
            row["配当位置"] = "基準付近"
            row["配当戻り余地"] = "中庸"
        else:
            row["配当位置"] = "高すぎ"
            row["配当戻り余地"] = "上振れ警戒"
    else:
        row["配当係数"] = None
        row["平均配当差"] = None
        row["配当位置"] = "未回収"
        row["配当戻り余地"] = ""

    if roi is not None and pd.notna(roi) and exp_roi is not None:
        row["回収差"] = round(float(roi) - float(exp_roi), 1)
    else:
        row["回収差"] = None

    # 2車複と同じ考え方で、後追い・過熱・未回収を避ける。
    h = float(row.get("的中H") or 0)
    diff = row.get("想定差")
    coef = row.get("配当係数")
    roi_diff = row.get("回収差")
    if h <= 0:
        reason = "未回収除外"
    elif diff is not None and diff >= 5.0:
        reason = "的中率過熱除外"
    elif roi_diff is not None and roi_diff >= 25.0:
        reason = "後追い除外"
    elif coef is not None and coef > 1.30:
        reason = "配当上振れ警戒"
    elif coef is not None and coef < 0.80:
        reason = "歪み枠"
    elif diff is not None and abs(float(diff)) <= 3.0:
        reason = "中庸枠"
    else:
        reason = "監視"
    row["総合候補理由"] = reason
    row["判定"] = ""
    return row

def sanrenpuku12_expected_rate(pair12_rate: float | None = None) -> float | None:
    """2車複1-2想定率×3で、1-2両方3着内率を概算。上限は100%。"""
    try:
        if pair12_rate is None:
            return float(TRIO_12_ALL_EXPECTED_HIT_RATE)
        return round(min(100.0, float(pair12_rate) * 3.0), 1)
    except Exception:
        return None


def sanrenpuku12_row(label: str, rec: Dict[str, int]) -> Dict:
    """3連複1-2-全用の表示行。小倉2年分3連複集計を固定想定として併記。"""
    row = payout_row(label, rec)
    exp_rate = sanrenpuku12_expected_rate()
    exp_avg_pay = float(TRIO_12_ALL_EXPECTED_AVG_PAY)
    exp_roi = float(TRIO_12_ALL_EXPECTED_ROI)

    row["想定1-2両方3着内率%"] = exp_rate
    row["想定平均配当"] = exp_avg_pay
    row["ゾーン想定回収率%"] = exp_roi

    if exp_rate and exp_rate > 0:
        row["7車5点_損益分岐平均配当"] = round((5.0 * 100.0) / (exp_rate / 100.0), 1)
    else:
        row["7車5点_損益分岐平均配当"] = None

    avg_pay = row.get("平均配当")
    roi = row.get("回収率%")
    hit_rate = row.get("的中率%")

    if avg_pay is not None and pd.notna(avg_pay):
        row["平均配当差"] = round(float(avg_pay) - exp_avg_pay, 1)
    else:
        row["平均配当差"] = None

    if roi is not None and pd.notna(roi):
        row["ゾーン回収差"] = round(float(roi) - exp_roi, 1)
    else:
        row["ゾーン回収差"] = None

    if hit_rate is not None and pd.notna(hit_rate) and exp_rate is not None:
        row["的中率差"] = round(float(hit_rate) - float(exp_rate), 1)
    else:
        row["的中率差"] = None

    return row


def nishafuku12_base_row(label: str, rec: Dict[str, int]) -> Dict:
    """2車複1-2そのものの基礎集計。1-2ゾーンの土台確認用。"""
    row = payout_row(label, rec)

    exp_rate = float(PAIR_BASE_HIT_RATE_DEFAULTS.get("1-2", 0.0))
    exp_avg_pay = float(PAIR_BASE_AVG_PAY_DEFAULTS.get("1-2", 0.0))
    exp_roi = round(exp_rate * exp_avg_pay / 100.0, 1) if exp_avg_pay > 0 else None

    row["想定的中率%"] = round(exp_rate, 1)
    row["基準平均配当"] = round(exp_avg_pay, 1)
    row["想定回収率%"] = exp_roi

    hit_rate = row.get("的中率%")
    avg_pay = row.get("平均配当")
    roi = row.get("回収率%")

    if hit_rate is not None and pd.notna(hit_rate):
        row["的中率差"] = round(float(hit_rate) - exp_rate, 1)
    else:
        row["的中率差"] = None

    if avg_pay is not None and pd.notna(avg_pay):
        row["平均配当差"] = round(float(avg_pay) - exp_avg_pay, 1)
    else:
        row["平均配当差"] = None

    if roi is not None and pd.notna(roi) and exp_roi is not None:
        row["回収差"] = round(float(roi) - float(exp_roi), 1)
    else:
        row["回収差"] = None

    return row


def targets_for_pattern(axis: int, field_n: int) -> List[int]:
    """
    2車単固定型の相手評価。
    評価1→23
    評価2→13
    欠車対応：存在する評価だけ返す。
    """
    if axis == 1:
        base = AXIS1_TARGETS
    elif axis == 2:
        base = AXIS2_TARGETS
    else:
        base = ()

    return [r for r in base if r <= field_n]


def ksum_2t_pattern(axis: int, field_n: int) -> int:
    """2車単固定型の点数。"""
    if axis > field_n:
        return 0
    return len(targets_for_pattern(axis, field_n))


def hit_2t_pattern(axis: int, win_rank: int, sec_rank: int, field_n: int) -> bool:
    """2車単固定型の的中判定。"""
    if axis > field_n:
        return False
    return win_rank == axis and sec_rank in targets_for_pattern(axis, field_n)


def pattern_label(axis: int) -> str:
    if axis == 1:
        return "2車単 1→23"
    if axis == 2:
        return "2車単 2→13"
    return f"2車単 評価{axis}"


def pair_target_label(axis: int, target: int) -> str:
    return f"2車単 {axis}→{target}"


def ksum_axis_to_target(axis: int, target: int, field_n: int) -> int:
    """2車単：axis→target の点数。存在する評価だけ1点として扱う。"""
    if field_n < 2:
        return 0
    if axis > field_n or target > field_n:
        return 0
    if axis == target:
        return 0
    return 1


def hit_axis_to_target(axis: int, target: int, win_rank: int, sec_rank: int, field_n: int) -> bool:
    """2車単：axis→target の的中判定。"""
    if ksum_axis_to_target(axis, target, field_n) <= 0:
        return False
    return win_rank == axis and sec_rank == target


def nishafuku_label(a: int, b: int) -> str:
    return f"2車複 {a}-{b}"


NISHAFUKU_SET_DEFS = {
    # 標準棚：軸1・2のみ
    "標準 1-234": [nishafuku_label(1, 2), nishafuku_label(1, 3), nishafuku_label(1, 4)],
    "標準 2-134": [nishafuku_label(1, 2), nishafuku_label(2, 3), nishafuku_label(2, 4)],

    # 穴棚：軸1・2のみ
    "穴 1-567": [nishafuku_label(1, 5), nishafuku_label(1, 6), nishafuku_label(1, 7)],
    "穴 2-567": [nishafuku_label(2, 5), nishafuku_label(2, 6), nishafuku_label(2, 7)],
}

agg_payout_nishafuku_set_manual: Dict[str, Dict[str, int]] = {
    set_label: new_payout_rec() for set_label in NISHAFUKU_SET_DEFS
}

# 34-12 2車複フォメ専用集計。
# 推奨流れ（V評価入力順）の「3番手・4番手」×「1番手・2番手」を2車複4点で買う形。
# 例：推奨流れ 3→5→7→1→2→4→6
#     2車複 7=3 / 7=5 / 1=3 / 1=5
NISHAFUKU_3412_LABEL = "34-12 2車複フォメ"
NISHAFUKU_3412_RANK_PAIRS = [(3, 1), (3, 2), (4, 1), (4, 2)]
# 引継ぎ分は、既存の「個別2車複 引継ぎ入力（累積）」から自動合算する。
# 34-12 = 推奨流れの3・4番手 × 1・2番手 = 1-3 / 2-3 / 1-4 / 2-4
NISHAFUKU_3412_SOURCE_LABELS = [
    nishafuku_label(1, 3),
    nishafuku_label(2, 3),
    nishafuku_label(1, 4),
    nishafuku_label(2, 4),
]


def ksum_nishafuku_3412(field_n: int) -> int:
    """34-12 2車複フォメの点数。推奨流れの1～4番手が存在する時だけ4点。"""
    try:
        field_n = int(field_n)
    except Exception:
        return 0
    if field_n < 4:
        return 0
    return len(NISHAFUKU_3412_RANK_PAIRS)


def hit_nishafuku_3412(win_rank: int, sec_rank: int, field_n: int) -> bool:
    """34-12 2車複フォメの的中判定。1→2着評価順位が3/4番手×1/2番手なら的中。"""
    if ksum_nishafuku_3412(field_n) <= 0:
        return False
    actual = {int(win_rank), int(sec_rank)}
    for a, b in NISHAFUKU_3412_RANK_PAIRS:
        if actual == {a, b}:
            return True
    return False


def nishafuku_3412_bets_from_order(vorder: List[str]) -> List[str]:
    """入力された推奨流れ順から、34-12の実車番買い目を表示用に作る。"""
    if not vorder or len(vorder) < 4:
        return []
    rank_to_car = {i + 1: str(car) for i, car in enumerate(vorder)}
    bets = []
    for a, b in NISHAFUKU_3412_RANK_PAIRS:
        ca = rank_to_car.get(a)
        cb = rank_to_car.get(b)
        if ca is None or cb is None:
            continue
        bets.append(f"{ca}={cb}")
    return bets


# 123-123-4 三連複3点の推定集計。
# 実三連複配当は入力していないため、N/H/的中率だけを出す。金額・回収率は出さない。
# 1→2着評価分布と評価別3着回数から、3着を条件付き按分して推定する。
TRIO_1231234_LABEL = "123-123-4 三連複3点"
TRIO_1231234_KEYS = ["1-2-4", "1-3-4", "2-3-4"]
TRIO_1231234_TOP_SET = {1, 2, 3}
TRIO_1231234_TARGET = 4

TRIO_1241243_LABEL = "124-124-3 三連複3点"
TRIO_1241243_KEYS = ["1-2-3", "1-3-4", "2-3-4"]
TRIO_1241243_TOP_SET = {1, 2, 4}
TRIO_1241243_TARGET = 3


def _trio_1231234_is_hit_ranks(ranks) -> bool:
    """評価順位3つが 1-2-4 / 1-3-4 / 2-3-4 のどれかなら的中。"""
    try:
        s = {int(x) for x in ranks}
    except Exception:
        return False
    return TRIO_1231234_TARGET in s and len(s & TRIO_1231234_TOP_SET) >= 2


def hit_trio_1231234(vorder: List[str], finish: List[str], field_n: int) -> bool:
    """日次入力から、123-123-4三連複3点の実的中だけ判定する。"""
    try:
        field_n = int(field_n)
    except Exception:
        return False
    if field_n < 4 or not vorder or len(finish) < 3:
        return False
    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}
    finish_ranks = [car_to_rank.get(car) for car in finish[:3]]
    if any(x is None for x in finish_ranks):
        return False
    return _trio_1231234_is_hit_ranks(finish_ranks)


def estimate_trio_1231234_from_pair12_and_rank(pair12_counts: Dict[PairKey, int], rank_counts: Dict[int, Dict[str, int]]) -> Dict:
    """
    123-123-4三連複3点を、既存の2車複ブロックと評価別3着回数から推定する。

    実3連複配当がないため、払戻SUMは出さない。
    推定方法：
      1着→2着の各評価ペアごとに、残り評価の3着回数比で3着評価を按分。
      その3着評価を加えた3つの評価が 1-2-4 / 1-3-4 / 2-3-4 なら推定Hに加算。
    """
    total_n = sum(int(v) for v in pair12_counts.values())
    ksum = int(total_n) * len(TRIO_1231234_KEYS)

    c3_by_rank = {r: int(rank_counts.get(r, {}).get("C3", 0)) for r in range(1, FIELD_SIZE + 1)}
    est_h = 0.0
    detail_rows = []

    for (wr, sr), cnt in sorted(pair12_counts.items()):
        cnt = int(cnt)
        if cnt <= 0 or wr == sr:
            continue

        remaining = [r for r in range(1, FIELD_SIZE + 1) if r not in (int(wr), int(sr))]
        denom = sum(c3_by_rank.get(r, 0) for r in remaining)
        if denom <= 0:
            continue

        pair_est_h = 0.0
        hit_third_parts = []
        for tr in remaining:
            if not _trio_1231234_is_hit_ranks([wr, sr, tr]):
                continue
            add = cnt * (c3_by_rank.get(tr, 0) / denom)
            pair_est_h += add
            hit_third_parts.append(f"{tr}:{add:.1f}")

        if pair_est_h > 0:
            est_h += pair_est_h
            detail_rows.append({
                "1着評価": int(wr),
                "2着評価": int(sr),
                "回数": cnt,
                "推定的中H": round(pair_est_h, 1),
                "的中3着按分": " / ".join(hit_third_parts),
            })

    hit_rate = round(100.0 * est_h / total_n, 1) if total_n > 0 else None
    return {
        "型": TRIO_1231234_LABEL,
        "対象N": int(total_n),
        "総点数KSUM": int(ksum),
        "推定H": round(est_h, 1),
        "推定的中率%": hit_rate,
        "構成": " / ".join(TRIO_1231234_KEYS),
        "detail_rows": detail_rows,
    }


def trio_1231234_daily_row(rec: Dict[str, int]) -> Dict:
    """日次入力だけは実着順から的中Hを出す。配当入力なしなのでSUM/回収率は出さない。"""
    N = int(rec.get("N", 0))
    KSUM = int(rec.get("KSUM", 0))
    H = int(rec.get("H", 0))
    hit_rate = round(100.0 * H / N, 1) if N > 0 else None
    return {
        "型": "123-123-4｜今日入力・実着順",
        "対象N": N,
        "総点数KSUM": KSUM,
        "的中H": H,
        "的中率%": hit_rate,
        "構成": " / ".join(TRIO_1231234_KEYS),
    }




def _trio_1241243_is_hit_ranks(ranks) -> bool:
    """評価順位3つが 1-2-3 / 1-3-4 / 2-3-4 のどれかなら的中。"""
    try:
        s = {int(x) for x in ranks}
    except Exception:
        return False
    return TRIO_1241243_TARGET in s and len(s & TRIO_1241243_TOP_SET) >= 2


def hit_trio_1241243(vorder: List[str], finish: List[str], field_n: int) -> bool:
    """日次入力から、124-124-3三連複3点の実的中だけ判定する。"""
    try:
        field_n = int(field_n)
    except Exception:
        return False
    if field_n < 4 or not vorder or len(finish) < 3:
        return False
    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}
    finish_ranks = [car_to_rank.get(car) for car in finish[:3]]
    if any(x is None for x in finish_ranks):
        return False
    return _trio_1241243_is_hit_ranks(finish_ranks)


def estimate_trio_1241243_from_pair12_and_rank(pair12_counts: Dict[PairKey, int], rank_counts: Dict[int, Dict[str, int]]) -> Dict:
    """
    124-124-3三連複3点を、既存の2車複ブロックと評価別3着回数から推定する。
    実3連複配当がないため、払戻SUMは出さない。
    """
    total_n = sum(int(v) for v in pair12_counts.values())
    ksum = int(total_n) * len(TRIO_1241243_KEYS)

    c3_by_rank = {r: int(rank_counts.get(r, {}).get("C3", 0)) for r in range(1, FIELD_SIZE + 1)}
    est_h = 0.0
    detail_rows = []

    for (wr, sr), cnt in sorted(pair12_counts.items()):
        cnt = int(cnt)
        if cnt <= 0 or wr == sr:
            continue

        remaining = [r for r in range(1, FIELD_SIZE + 1) if r not in (int(wr), int(sr))]
        denom = sum(c3_by_rank.get(r, 0) for r in remaining)
        if denom <= 0:
            continue

        pair_est_h = 0.0
        hit_third_parts = []
        for tr in remaining:
            if not _trio_1241243_is_hit_ranks([wr, sr, tr]):
                continue
            add = cnt * (c3_by_rank.get(tr, 0) / denom)
            pair_est_h += add
            hit_third_parts.append(f"{tr}:{add:.1f}")

        if pair_est_h > 0:
            est_h += pair_est_h
            detail_rows.append({
                "1着評価": int(wr),
                "2着評価": int(sr),
                "回数": cnt,
                "推定的中H": round(pair_est_h, 1),
                "的中3着按分": " / ".join(hit_third_parts),
            })

    hit_rate = round(100.0 * est_h / total_n, 1) if total_n > 0 else None
    return {
        "型": TRIO_1241243_LABEL,
        "対象N": int(total_n),
        "総点数KSUM": int(ksum),
        "推定H": round(est_h, 1),
        "推定的中率%": hit_rate,
        "構成": " / ".join(TRIO_1241243_KEYS),
        "detail_rows": detail_rows,
    }


def trio_1241243_daily_row(rec: Dict[str, int]) -> Dict:
    """日次入力だけは実着順から的中Hを出す。配当入力なしなのでSUM/回収率は出さない。"""
    N = int(rec.get("N", 0))
    KSUM = int(rec.get("KSUM", 0))
    H = int(rec.get("H", 0))
    hit_rate = round(100.0 * H / N, 1) if N > 0 else None
    return {
        "型": "124-124-3｜今日入力・実着順",
        "対象N": N,
        "総点数KSUM": KSUM,
        "的中H": H,
        "的中率%": hit_rate,
        "構成": " / ".join(TRIO_1241243_KEYS),
    }


def ksum_nishafuku_pair(a: int, b: int, field_n: int) -> int:
    """2車複：評価a-b の点数。存在する評価だけ1点として扱う。"""
    if field_n < 2:
        return 0
    if a > field_n or b > field_n:
        return 0
    if a == b:
        return 0
    return 1


def hit_nishafuku_pair(a: int, b: int, win_rank: int, sec_rank: int, field_n: int) -> bool:
    """2車複：実際の1着・2着評価順位がa-bなら的中。順不同。"""
    if ksum_nishafuku_pair(a, b, field_n) <= 0:
        return False
    return {win_rank, sec_rank} == {a, b}



def payout_row(label: str, rec: Dict[str, int]) -> Dict:
    N = int(rec["N"])
    KSUM = int(rec["KSUM"])
    H = int(rec["H"])
    SUM = int(rec["SUM"])

    invest = KSUM * 100
    roi = round(100.0 * SUM / invest, 1) if invest > 0 else None
    avg_pay = round(SUM / H, 1) if H > 0 else None
    hit_rate = round(100.0 * H / N, 1) if N > 0 else None

    return {
        "型": label,
        "対象N": N,
        "総点数KSUM": KSUM,
        "投資額換算": invest,
        "払戻合計SUM": SUM,
        "的中H": H,
        "的中率%": hit_rate,
        "平均配当": avg_pay,
        "回収率%": roi,
        "判定": "",
    }


def rec_for_labels(source: Dict[str, Dict[str, int]], labels: List[str]) -> Dict[str, int]:
    """指定ラベル群の合算レコード。Nは最大N、KSUM/H/SUMは合算。"""
    return combine_recs([source[label] for label in labels if label in source])


def expected_set_hit_rate_from_pair12(labels: List[str], pair12_counts: Dict[PairKey, int]) -> float | None:
    """
    1→2着評価分布から、2車複セットの想定的中率を出す。
    2車複なので順不同で集計する。

    例：
      1-234 = 1-2 / 1-3 / 1-4
      → (1,2)+(2,1)+(1,3)+(3,1)+(1,4)+(4,1)
    """
    total = sum(int(v) for v in pair12_counts.values())
    if total <= 0:
        return None

    hit = 0
    for label in labels:
        # label例: "2車複 1-4"
        try:
            pair_part = label.replace("2車複", "").strip()
            a_str, b_str = pair_part.split("-")
            a, b = int(a_str), int(b_str)
        except Exception:
            continue

        hit += int(pair12_counts.get((a, b), 0))
        hit += int(pair12_counts.get((b, a), 0))

    return round(100.0 * hit / total, 1)


def payout_row_with_expected_set_hit(label: str, rec: Dict[str, int], labels: List[str], pair12_counts: Dict[PairKey, int]) -> Dict:
    """想定セット的中率と、実的中率との差を併記した行。"""
    row = payout_row(label, rec)

    expected_hit = expected_set_hit_rate_from_pair12(labels, pair12_counts)
    row["想定セット的中率%"] = expected_hit

    if row["的中率%"] is not None and expected_hit is not None:
        row["想定差"] = round(row["的中率%"] - expected_hit, 1)
    else:
        row["想定差"] = None

    return row


def expected_pair_hit_rate_from_pair12(a: int, b: int, pair12_counts: Dict[PairKey, int]) -> float | None:
    """1→2着評価分布から、評価a-bの2車複想定的中率を出す。順不同。"""
    total = sum(int(v) for v in pair12_counts.values())
    if total <= 0:
        return None
    hit = int(pair12_counts.get((a, b), 0)) + int(pair12_counts.get((b, a), 0))
    return round(100.0 * hit / total, 1)


def nishafuku_individual_row(label: str, rec: Dict[str, int], pair12_counts: Dict[PairKey, int]) -> Dict:
    """個別2車複の累積表示行。3軸・4軸追加ペアも同じ形式で見る。"""
    row = payout_row(label, rec)
    pair_part = label.replace("2車複", "").strip()
    row["ペアキー"] = pair_part

    try:
        a, b = [int(x) for x in pair_part.split("-")]
    except Exception:
        a = b = None

    # 1-2〜2-7は小倉固定基準、追加した3-4以降は1→2着分布からの累積想定率を使う。
    exp_rate = PAIR_BASE_HIT_RATE_DEFAULTS.get(pair_part)
    if exp_rate is None and a is not None and b is not None:
        exp_rate = expected_pair_hit_rate_from_pair12(a, b, pair12_counts)

    exp_avg_pay = PAIR_BASE_AVG_PAY_DEFAULTS.get(pair_part)
    exp_roi = round(float(exp_rate) * float(exp_avg_pay) / 100.0, 1) if exp_rate is not None and exp_avg_pay else None

    row["想定ペア的%"] = exp_rate
    row["ペア基準配当"] = exp_avg_pay
    row["想定回収率%"] = exp_roi

    hit_rate = row.get("的中率%")
    avg_pay = row.get("平均配当")
    roi = row.get("回収率%")

    if hit_rate is not None and pd.notna(hit_rate) and exp_rate is not None:
        row["想定差"] = round(float(hit_rate) - float(exp_rate), 1)
    else:
        row["想定差"] = None

    if avg_pay is not None and pd.notna(avg_pay) and exp_avg_pay:
        row["配当係数"] = round(float(avg_pay) / float(exp_avg_pay), 2)
        row["平均配当差"] = round(float(avg_pay) - float(exp_avg_pay), 1)
    else:
        row["配当係数"] = None
        row["平均配当差"] = None

    if roi is not None and pd.notna(roi) and exp_roi is not None:
        row["回収差"] = round(float(roi) - float(exp_roi), 1)
    else:
        row["回収差"] = None

    return row


def diff_status(diff, expected=None) -> str:
    """想定差の状態をざっくり表示。想定0%は候補対象外。"""
    if expected is not None and expected == 0:
        return "対象外"
    if diff is None:
        return ""
    if diff >= 10:
        return "当たりすぎ"
    if diff <= -10:
        return "当たらなすぎ"
    return "中庸"


def _clean_num_list(values):
    out = []
    for v in values:
        try:
            if pd.notna(v):
                out.append(float(v))
        except Exception:
            pass
    return out


def _median(values):
    vals = sorted(_clean_num_list(values))
    n = len(vals)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def _deviation_stats(value, values):
    """平均差・中央値差・偏差値・基準位置を返す。少数候補でも落ちない軽量版。"""
    try:
        if value is None or pd.isna(value):
            return {"平均差": None, "中央値差": None, "偏差値": None, "基準位置": ""}
        x = float(value)
    except Exception:
        return {"平均差": None, "中央値差": None, "偏差値": None, "基準位置": ""}

    vals = _clean_num_list(values)
    if not vals:
        return {"平均差": None, "中央値差": None, "偏差値": None, "基準位置": ""}

    mean = sum(vals) / len(vals)
    med = _median(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals) if len(vals) > 0 else 0.0
    sd = var ** 0.5

    mean_diff = round(x - mean, 1)
    med_diff = round(x - med, 1) if med is not None else None
    if sd > 0:
        dev = round(50.0 + 10.0 * (x - mean) / sd, 1)
    else:
        dev = 50.0

    if dev >= 60:
        pos = "高すぎ"
    elif dev >= 55:
        pos = "やや高い"
    elif dev <= 40:
        pos = "低すぎ"
    elif dev <= 45:
        pos = "やや低い"
    else:
        pos = "中庸"

    return {
        "平均差": mean_diff,
        "中央値差": med_diff,
        "偏差値": dev,
        "基準位置": pos,
    }



def drop_blank_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """表示用：全行が空欄/None/NaNの列だけ削除する。判定列も全空なら削る。"""
    if df is None or df.empty:
        return df
    out = df.copy()
    drop_cols = []
    for col in out.columns:
        s = out[col]
        # None/NaN または 空文字だけなら空列扱い
        is_blank = s.apply(lambda v: pd.isna(v) or str(v).strip() == "")
        if bool(is_blank.all()):
            drop_cols.append(col)
    if drop_cols:
        out = out.drop(columns=drop_cols)
    return out

def table_auto_height(df: pd.DataFrame, row_px: int = 35, header_px: int = 38, pad_px: int = 8, min_px: int = 90) -> int:
    """行数に合わせて表の高さを自動調整。余白と縦スクロールを減らす。"""
    if df is None:
        return min_px
    try:
        n = len(df)
    except Exception:
        n = 0
    return max(min_px, header_px + row_px * max(n, 1) + pad_px)


def render_sortable_table(df: pd.DataFrame, height: int | None = None):
    """Streamlit標準のソート可能表。高さ未指定なら行数に合わせて自動調整。"""
    if df is None or df.empty:
        st.info("表示するデータがありません。")
        return

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=height if height is not None else table_auto_height(df),
    )



# =========================
# 投資EV診断（既存推奨買い目を変えずに診断だけ行う）
# =========================
EV_K_MAP = {
    "2車複": 75,
    "3連複": 125,
}
EV_N0_MAP = {
    "2車複": 50,
    "3連複": 40,
}
EV_H0_MAP = {
    "2車複": 5,
    "3連複": 3,
}


def _safe_float(v, default=None):
    try:
        if v is None or pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def _pct_to_prob(v):
    x = _safe_float(v, None)
    if x is None:
        return None
    # 既存表は%表記なので、1.0を超える値は%として扱う。
    return x / 100.0 if x > 1.0 else x


def _odds_from_pay(v):
    """100円あたり払戻金を倍率に変換。例：315円→3.15倍。"""
    x = _safe_float(v, None)
    if x is None or x <= 0:
        return None
    return x / 100.0


def _heat_penalty_from_ratio(odds_ratio):
    r = _safe_float(odds_ratio, None)
    if r is None:
        return 1.0
    if r >= 0.90:
        return 1.00
    if r >= 0.75:
        return 0.85
    if r >= 0.60:
        return 0.65
    return 0.00


def _single_ev_label(ev, confidence, odds_ratio, is_anchor=False):
    ev = _safe_float(ev, 0.0)
    conf = _safe_float(confidence, 0.0)
    ratio = _safe_float(odds_ratio, 1.0)

    if is_anchor:
        if ev >= 1.00 and ratio >= 0.85:
            return "保険採用"
        if ev >= 0.90:
            return "低比重保険"
        return "保険除外"

    if ev >= 1.20 and conf >= 0.70 and ratio >= 0.90:
        return "強推奨"
    if ev >= 1.10 and conf >= 0.60 and ratio >= 0.85:
        return "推奨"
    if ev >= 1.00:
        return "監視"
    return "除外"


def calculate_ev_metrics(df: pd.DataFrame, bet_type: str, condition_margin: float = 0.90, duplicate_penalty: float = 1.0) -> pd.DataFrame:
    """
    既存の集計表に投資診断列を追加する。

    重要：この段階では該当レースの現在オッズを入力していないため、
    EVは確定させない。
    代わりに、p_safeから必要オッズを逆算して表示する。

    EV = p_safe × current_odds
    よって、必要odds = 目標EV / p_safe
    """
    if df is None or df.empty:
        return df

    out = df.copy()
    K = float(EV_K_MAP.get(bet_type, 100))
    N0 = float(EV_N0_MAP.get(bet_type, 50))
    H0 = float(EV_H0_MAP.get(bet_type, 3))

    p_adj_list = []
    p_safe_list = []
    ref_odds_list = []
    base_odds_list = []
    odds_ratio_list = []
    ref_ev_list = []
    req100_list = []
    req105_list = []
    req110_list = []
    req120_list = []
    req_pay110_list = []
    conf_list = []
    heat_list = []
    score_list = []
    label_list = []
    anchor_list = []

    for _, row in out.iterrows():
        N = _safe_float(row.get("対象N"), 0.0) or 0.0
        hits = _safe_float(row.get("的中H"), 0.0) or 0.0

        p_current = _pct_to_prob(row.get("的中率%"))
        if p_current is None:
            p_current = 0.0

        if bet_type == "2車複":
            p_base = _pct_to_prob(row.get("想定ペア的%"))
            base_pay = row.get("ペア基準配当")
        else:
            p_base = _pct_to_prob(row.get("想定的中率%"))
            base_pay = row.get("基準平均配当")

        if p_base is None:
            p_base = p_current

        w = N / (N + K) if (N + K) > 0 else 0.0
        p_adj = w * p_current + (1.0 - w) * p_base
        p_safe = p_adj * float(condition_margin)

        # 該当レースの現在オッズは未入力なので、これは参考値。
        # 「平均配当が今も出るなら」という参考EVに留める。
        ref_odds = _odds_from_pay(row.get("平均配当"))
        if ref_odds is None:
            ref_odds = _odds_from_pay(base_pay)

        base_odds = _odds_from_pay(base_pay)
        odds_ratio = (ref_odds / base_odds) if (ref_odds is not None and base_odds is not None and base_odds > 0) else None
        heat_penalty = _heat_penalty_from_ratio(odds_ratio)

        ref_ev = (p_safe * ref_odds) if ref_odds is not None else None
        confidence = min(1.0, N / N0) * min(1.0, hits / H0) if N0 > 0 and H0 > 0 else 0.0

        # 現在オッズ未入力なので、Scoreは参考EVベースの参考スコア。
        score = (ref_ev * heat_penalty * float(duplicate_penalty)) if ref_ev is not None else None

        if p_safe and p_safe > 0:
            req100 = 1.00 / p_safe
            req105 = 1.05 / p_safe
            req110 = 1.10 / p_safe
            req120 = 1.20 / p_safe
        else:
            req100 = req105 = req110 = req120 = None

        key = str(row.get("ペアキー") or row.get("目") or "").strip()
        is_anchor = (bet_type == "2車複" and key == "1-2")

        # 現在オッズ未入力のため、買い/ケンの確定判定はしない。
        # 1-2だけは必要オッズ確認の保険枠として表示する。
        ev_label = "必要オッズ確認"
        if is_anchor:
            ev_label = "保険必要オッズ確認"

        p_adj_list.append(round(p_adj * 100.0, 2))
        p_safe_list.append(round(p_safe * 100.0, 2))
        ref_odds_list.append(round(ref_odds, 2) if ref_odds is not None else None)
        base_odds_list.append(round(base_odds, 2) if base_odds is not None else None)
        odds_ratio_list.append(round(odds_ratio, 2) if odds_ratio is not None else None)
        ref_ev_list.append(round(ref_ev, 3) if ref_ev is not None else None)
        req100_list.append(round(req100, 2) if req100 is not None else None)
        req105_list.append(round(req105, 2) if req105 is not None else None)
        req110_list.append(round(req110, 2) if req110 is not None else None)
        req120_list.append(round(req120, 2) if req120 is not None else None)
        req_pay110_list.append(round(req110 * 100.0, 0) if req110 is not None else None)
        conf_list.append(round(confidence, 3))
        heat_list.append(round(heat_penalty, 2))
        score_list.append(round(score, 3) if score is not None else None)
        label_list.append(ev_label)
        anchor_list.append(bool(is_anchor))

    out["p_adj%"] = p_adj_list
    out["p_safe%"] = p_safe_list
    out["参考odds"] = ref_odds_list
    out["基準odds"] = base_odds_list
    out["odds_ratio"] = odds_ratio_list
    out["参考EV"] = ref_ev_list
    # 画面上で使う買い基準はEV1.10に一本化する。
    # EV1.00/1.05は損益分岐・弱確認ラインであり、購入判断には使わないため非表示。
    out["最低必要オッズ"] = req110_list
    out["最低必要払戻"] = req_pay110_list
    out["Confidence"] = conf_list
    out["heat_penalty"] = heat_list
    out["Score"] = score_list
    out["EV判定"] = label_list
    out["is_anchor"] = anchor_list
    out["券種"] = bet_type
    return out



def _pair_key_norm(a: int, b: int) -> str:
    """2車複表示用に評価番号を昇順キーへ整える。"""
    a, b = int(a), int(b)
    if a == b:
        return ""
    x, y = sorted((a, b))
    return f"{x}-{y}"


def _pair_hit_rate_from_pair12_total(pair_key: str, pair12_counts: Dict[PairKey, int]) -> float | None:
    """1→2着評価分布から、任意2車複キーの現在的中率%を出す。"""
    try:
        a, b = [int(x) for x in str(pair_key).split("-")]
    except Exception:
        return None
    total = sum(int(v) for v in pair12_counts.values())
    if total <= 0 or a == b:
        return None
    hit = int(pair12_counts.get((a, b), 0)) + int(pair12_counts.get((b, a), 0))
    return round(100.0 * hit / total, 1)


def _rank_pair_candidate_row(row: pd.Series) -> float:
    """クロスフォーメーション用のヒモ候補を軽く順位化する。小さいほど優先。"""
    score = 100.0
    judge = str(row.get("判定", ""))
    asset = str(row.get("資産枠", ""))
    reason = str(row.get("総合候補理由", ""))
    if judge == "注":
        score -= 40.0
    elif judge == "本線":
        score -= 20.0
    if asset == "歪み" or "歪み" in reason:
        score -= 18.0
    elif asset == "中庸" or "中庸" in reason:
        score -= 14.0
    elif asset == "安定" or "安定" in reason:
        score -= 8.0
    try:
        # 配当が戻りやすいものを少し優先。ただし係数が極端なものは既存ロジック側で弾く前提。
        coef = float(row.get("配当係数"))
        if pd.notna(coef):
            score += abs(coef - 0.85) * 6.0
    except Exception:
        pass
    try:
        exp = float(row.get("想定ペア的%"))
        if pd.notna(exp):
            score -= exp / 10.0
    except Exception:
        pass
    try:
        opp = int(row.get("相手"))
        score += opp * 0.05
    except Exception:
        pass
    return float(score)




def build_cross_formation_summary(df_pairs: pd.DataFrame, pair12_counts: Dict[PairKey, int]) -> dict | None:
    """
    クロスフォーメーション A◯-B△ を1つだけ作る。

    v11.7方針：
    - クロスフォーメーションの基準は、既存の2車複「本線・注」ロジックに準じる。
    - 中心ペアは本線を優先。なければ注。
    - 注ペアが中心と別に存在する場合は、まず「中心ペア」と「注ペア」を両方内包する4点フォーメーションだけを優先比較する。
      例：本線1-5、注2-3なら、12-35 または 13-25 のように、1-5と2-3を両方含む型を比較する。
    - もし中心＋注を両方含める型が作れない場合だけ、中心ペアを含む全候補から選ぶ。
    - 現在的中率最大ではなく、本線・注・資産枠・配当位置・除外理由など既存推奨基準に沿ったスコアで選ぶ。
    - 通常表示は型だけ。内部4点は detail へ格納する。
    """
    if df_pairs is None or df_pairs.empty:
        return None
    work = df_pairs.copy()
    if "ペアキー" not in work.columns:
        return None

    # 既存の本線・注をそのまま中心情報として使う。
    cand_df = work[work.get("判定", "").astype(str).isin(["本線", "注"])].copy()
    if cand_df.empty:
        return None
    cand_df["_center_rank"] = cand_df["判定"].astype(str).map({"本線": 0, "注": 1}).fillna(9)
    sort_cols = ["_center_rank"]
    if "_枠内順位" in cand_df.columns:
        sort_cols.append("_枠内順位")
    sort_cols.append("ペアキー")
    cand_df = cand_df.sort_values(sort_cols)

    center_key = str(cand_df.iloc[0].get("ペアキー", "")).strip()
    try:
        center_a, center_b = [int(x) for x in center_key.split("-")]
    except Exception:
        return None
    if center_a == center_b:
        return None

    # 中心とは別の最上位「注」を拾う。中心が注の場合は、次点注を探す。
    note_key = None
    note_df = work[(work.get("判定", "").astype(str) == "注")].copy()
    if not note_df.empty:
        if "_枠内順位" in note_df.columns:
            note_df = note_df.sort_values(["_枠内順位", "ペアキー"])
        else:
            note_df = note_df.sort_values(["ペアキー"])
        for _, nr in note_df.iterrows():
            pk = str(nr.get("ペアキー", "")).strip()
            if pk and pk != center_key:
                note_key = pk
                break

    ranks = [1, 2, 3, 4, 5, 6, 7]

    row_map = {}
    for _, r in work.iterrows():
        pk = str(r.get("ペアキー", "")).strip()
        if pk:
            row_map[pk] = r

    def current_rate(pk: str) -> float:
        hr = _pair_hit_rate_from_pair12_total(pk, pair12_counts)
        return float(hr) if hr is not None else 0.0

    def _str(row: pd.Series | None, col: str) -> str:
        if row is None:
            return ""
        try:
            v = row.get(col, "")
        except Exception:
            return ""
        if pd.isna(v):
            return ""
        return str(v)

    def _num(row: pd.Series | None, col: str, default=None):
        if row is None:
            return default
        try:
            v = row.get(col, default)
            if pd.isna(v):
                return default
            return float(v)
        except Exception:
            return default

    def pair_display_rate(pk: str) -> float:
        """表示用の想定的中率。既存EV診断のp_safe%があればそれを使う。"""
        row = row_map.get(pk)
        if row is not None:
            v = _num(row, "p_safe%", None)
            if v is not None:
                return round(v, 2)
            v = _num(row, "想定ペア的%", None)
            if v is not None:
                return round(v, 2)
            v = _num(row, "的中率%", None)
            if v is not None:
                return round(v, 2)
        # 既存表にないペアは現在分布だけ。過信しないよう表示用も割引。
        return round(current_rate(pk) * 0.65, 2)

    def pair_rec_score(pk: str, role: str = "side") -> tuple[float, dict]:
        """既存の推奨買い目判定に準じたペア評価。"""
        row = row_map.get(pk)
        cur = current_rate(pk)
        p_disp = pair_display_rate(pk)
        info = {
            "買い目": pk,
            "表示想定的中率%": p_disp,
            "現在的中率%": round(cur, 1),
            "判定": "",
            "資産枠": "",
            "総合候補理由": "",
            "配当位置": "",
            "配当戻り余地": "",
            "ペア評価点": None,
            "評価メモ": "",
        }

        if row is None:
            # 3-4等、既存2車複表にない橋渡しペア。現在分布だけなので控えめ。
            score = 8.0 + min(cur, 8.0) * 1.2
            if role not in ("bridge", "note"):
                score -= 18.0
            info["ペア評価点"] = round(score, 3)
            info["評価メモ"] = "既存2車複表なし・現在分布を割引"
            return score, info

        judge = _str(row, "判定")
        asset = _str(row, "資産枠")
        reason = _str(row, "総合候補理由")
        pay_pos = _str(row, "配当位置")
        pay_room = _str(row, "配当戻り余地")
        ev_label = _str(row, "EV判定")
        rank_score = _num(row, "_枠内順位", None)
        p_safe = _num(row, "p_safe%", None)
        expected = _num(row, "想定ペア的%", None)
        coef = _num(row, "配当係数", None)
        deviation = _num(row, "偏差値", None)

        score = 50.0
        memo = []

        if judge == "本線":
            score += 45.0; memo.append("本線")
        elif judge == "注":
            score += 36.0; memo.append("注")

        if asset == "安定":
            score += 18.0; memo.append("安定")
        elif asset == "中庸":
            score += 22.0; memo.append("中庸")
        elif asset == "歪み":
            score += 14.0; memo.append("歪み")

        if "安定枠" in reason:
            score += 16.0
        if "中庸枠" in reason:
            score += 18.0
        if "歪み枠" in reason:
            score += 10.0

        # 除外理由は減点。本線・注を内包するため、完全排除にはしない。
        if "未回収除外" in reason:
            score -= 22.0; memo.append("未回収減点")
        if "回収率過熱除外" in reason:
            score -= 26.0; memo.append("回収過熱減点")
        if "的中率過熱除外" in reason:
            score -= 22.0; memo.append("的中過熱減点")
        if "配当過熱除外" in reason:
            score -= 18.0; memo.append("配当過熱減点")
        if "後追い除外" in reason:
            score -= 12.0; memo.append("後追い減点")

        if "基準付近" in pay_pos:
            score += 14.0; memo.append("基準付近")
        elif "中庸" in pay_pos:
            score += 10.0
        elif "安すぎ" in pay_pos or "低すぎ" in pay_pos:
            score -= 4.0
        elif "高すぎ" in pay_pos:
            score -= 18.0; memo.append("高すぎ減点")

        if "中庸" in pay_room:
            score += 8.0
        elif "あり" in pay_room:
            score += 3.0
        elif "上振れ警戒" in pay_room:
            score -= 16.0; memo.append("上振れ警戒")

        if rank_score is not None:
            score -= min(max(rank_score, 0.0), 80.0) * 0.45

        if p_safe is not None:
            score += min(p_safe, 12.0) * 1.4
        elif expected is not None:
            score += min(expected, 12.0) * 1.0
        else:
            score += min(cur, 8.0) * 0.6

        if coef is not None:
            if 0.80 <= coef <= 1.30:
                score += 7.0
            elif coef > 1.30:
                score -= min((coef - 1.30) * 12.0, 18.0)
            elif coef < 0.50:
                score -= 6.0

        if deviation is not None:
            score -= abs(deviation - 52.0) * 0.10

        if role == "center":
            score += 30.0
        elif role == "note":
            score += 24.0
        elif role == "bridge":
            score *= 0.62

        info.update({
            "判定": judge,
            "資産枠": asset,
            "総合候補理由": reason,
            "配当位置": pay_pos,
            "配当戻り余地": pay_room,
            "EV判定": ev_label,
            "ペア評価点": round(score, 3),
            "評価メモ": "・".join(memo),
        })
        return score, info

    def edges_from_partition(left: tuple[int, int], right: tuple[int, int]) -> list[str]:
        """2×2のクロスフォーメーションから内部4点を作る。"""
        return [
            _pair_key_norm(left[0], right[0]),
            _pair_key_norm(left[0], right[1]),
            _pair_key_norm(left[1], right[0]),
            _pair_key_norm(left[1], right[1]),
        ]

    def formation_type(left: tuple[int, int], right: tuple[int, int]) -> str:
        """表示型。各側は昇順、左右はそのまま。"""
        l = "".join(str(x) for x in sorted(left))
        r = "".join(str(x) for x in sorted(right))
        return f"{l}-{r}"

    # 全2×2分割を作る。ただし重複表示を避けるため、最小値を左側に固定する。
    partitions = []
    for a in ranks:
        for b in ranks:
            if b <= a:
                continue
            left = tuple(sorted((a, b)))
            remaining = [x for x in ranks if x not in left]
            for c in remaining:
                for d in remaining:
                    if d <= c:
                        continue
                    right = tuple(sorted((c, d)))
                    # left/rightの入れ替え重複を避ける。
                    if min(left) > min(right):
                        continue
                    if set(left) & set(right):
                        continue
                    partitions.append((left, right))

    def build_candidate(left: tuple[int, int], right: tuple[int, int]) -> dict | None:
        pair_keys = edges_from_partition(left, right)
        if len(set(pair_keys)) != 4:
            return None
        if center_key not in pair_keys:
            return None

        has_note = bool(note_key and note_key in pair_keys)
        details = []
        scores = []
        for pk in pair_keys:
            if pk == center_key:
                role = "center"
            elif note_key and pk == note_key:
                role = "note"
            else:
                # 既存表にないペアは橋渡し、あるものはside。
                role = "bridge" if pk not in row_map else "side"
            s, d = pair_rec_score(pk, role=role)
            scores.append(s)
            details.append(d)

        disp_rates = [float(d.get("表示想定的中率%") or 0.0) for d in details]
        current_rates = [float(d.get("現在的中率%") or 0.0) for d in details]
        formation_hit = round(sum(disp_rates), 1)
        current_total = round(sum(current_rates), 1)
        non_center_rates = [r for pk, r in zip(pair_keys, disp_rates) if pk != center_key]
        min_non_center = min(non_center_rates) if non_center_rates else 0.0

        # 低すぎる枝が多いとテンポ補助にならない。
        low_pen = sum(1 for x in non_center_rates if x < 2.0) * 8.0
        if non_center_rates and min_non_center < 1.0:
            low_pen += 10.0

        # 6・7の過剰採用を減点。ただし本線・注内包の方を優先するため控えめ。
        used = set(left) | set(right)
        outer_pen = 0.0
        for r in used:
            if r == 5:
                outer_pen += 0.8
            elif r == 6:
                outer_pen += 2.5
            elif r == 7:
                outer_pen += 5.0
        if len([r for r in used if r >= 6]) >= 2:
            outer_pen += 6.0

        # 本線＋注を内包する型を強く優先。中心だけの型は後段のフォールバック。
        include_bonus = 80.0 if has_note else 0.0

        # 中心・注はすでに強く評価。その他2点は「枝」として評価。
        selection_score = sum(scores) + formation_hit * 0.80 + include_bonus - low_pen - outer_pen

        # 12-35 と 13-25 のように本線＋注を両方含む型では、合計的中率と非中心最低を重視。
        sort_score = (
            1 if has_note else 0,
            round(selection_score, 3),
            formation_hit,
            min_non_center,
            -sum(used) * 0.001,
        )

        return {
            "方式": "クロスフォーメーション",
            "型": formation_type(left, right),
            "中心": center_key,
            "注内包": has_note,
            "注": note_key or "",
            "左": "".join(str(x) for x in sorted(left)),
            "右": "".join(str(x) for x in sorted(right)),
            "買い目": pair_keys,
            "想定的中率%": formation_hit,
            "現在的中率合計%": current_total,
            "非中心最低的中率%": round(min_non_center, 1),
            "選択スコア": round(selection_score, 3),
            "detail": details,
            "_sort_score": sort_score,
        }

    candidates = []
    for left, right in partitions:
        c = build_candidate(left, right)
        if c is not None:
            candidates.append(c)

    if not candidates:
        return None

    # 注がある場合、中心＋注を両方内包する型を優先比較する。
    if note_key:
        preferred = [c for c in candidates if c.get("注内包")]
        if preferred:
            candidates_for_select = preferred
        else:
            candidates_for_select = candidates
    else:
        candidates_for_select = candidates

    candidates_for_select = sorted(candidates_for_select, key=lambda x: x["_sort_score"], reverse=True)
    best = candidates_for_select[0]

    # 根拠表示には、選択対象の上位と、全体上位を混ぜて確認できるようにする。
    all_ranked = sorted(candidates, key=lambda x: x["_sort_score"], reverse=True)

    total_hit = best.get("想定的中率%")
    if total_hit is None:
        state = ""
    elif total_hit >= 50.0:
        state = "テンポ良好"
    elif total_hit >= 45.0:
        state = "採用候補"
    elif total_hit >= 40.0:
        state = "監視"
    else:
        state = "低め"

    if total_hit and total_hit > 0:
        need_avg_pay_ev110 = round(400.0 * 1.10 / (float(total_hit) / 100.0), 0)
        need_avg_odds_ev110 = round(need_avg_pay_ev110 / 100.0, 2)
    else:
        need_avg_pay_ev110 = None
        need_avg_odds_ev110 = None

    def _candidate_row(c: dict, selected_pool: str) -> dict:
        hit = c.get("想定的中率%")
        if hit and hit > 0:
            need_pay = round(400.0 * 1.10 / (float(hit) / 100.0), 0)
        else:
            need_pay = None
        return {
            "型": c.get("型"),
            "中心": c.get("中心"),
            "注": c.get("注"),
            "注内包": c.get("注内包"),
            "表示想定的中率%": c.get("想定的中率%"),
            "現在的中率合計%": c.get("現在的中率合計%"),
            "非中心最低的中率%": c.get("非中心最低的中率%"),
            "選択スコア": c.get("選択スコア"),
            "EV1.10必要平均払戻": need_pay,
            "比較枠": selected_pool,
        }

    top_rows = []
    for c in candidates_for_select[:10]:
        top_rows.append(_candidate_row(c, "中心＋注内包優先" if note_key and any(x.get("注内包") for x in candidates_for_select) else "中心優先"))
    # 全体上位も参考として少し残す。ただし重複型は避ける。
    seen = {r["型"] for r in top_rows}
    for c in all_ranked[:10]:
        if c.get("型") in seen:
            continue
        top_rows.append(_candidate_row(c, "全体参考"))
        seen.add(c.get("型"))
        if len(top_rows) >= 12:
            break

    best.update({
        "EV1.10必要平均払戻": need_avg_pay_ev110,
        "EV1.10必要平均オッズ": need_avg_odds_ev110,
        "状態": state,
        "candidate_rows": top_rows,
    })
    best.pop("_sort_score", None)
    return best

def race_ev_summary(df: pd.DataFrame, stake_col: str = "stake") -> dict:
    """選ばれた買い目群のRaceEV/RaceConfidenceを計算する。"""
    if df is None or df.empty:
        return {"RaceEV": None, "RaceConfidence": None, "総点数": 0, "投資額": 0, "race_label": "ケン"}

    work = df.copy()
    if stake_col not in work.columns:
        work[stake_col] = 100.0

    total_stake = 0.0
    ev_weighted = 0.0
    conf_weighted = 0.0
    count = 0

    for _, r in work.iterrows():
        stake = _safe_float(r.get(stake_col), 0.0) or 0.0
        ev = _safe_float(r.get("EV"), None)
        conf = _safe_float(r.get("Confidence"), 0.0) or 0.0
        if stake <= 0 or ev is None:
            continue
        total_stake += stake
        ev_weighted += stake * ev
        conf_weighted += stake * conf
        count += 1

    if total_stake <= 0:
        return {"RaceEV": None, "RaceConfidence": None, "総点数": 0, "投資額": 0, "race_label": "ケン"}

    race_ev = ev_weighted / total_stake
    race_conf = conf_weighted / total_stake

    if race_ev >= 1.10 and race_conf >= 0.70:
        label = "買い"
    elif race_ev >= 1.05 and race_conf >= 0.60:
        label = "小口買い"
    else:
        label = "ケン"

    return {
        "RaceEV": round(race_ev, 3),
        "RaceConfidence": round(race_conf, 3),
        "総点数": count,
        "投資額": int(total_stake),
        "race_label": label,
    }


def build_sanrenpuku_4point_candidate_summary(df_pairs: pd.DataFrame) -> dict | None:
    """
    三連複4点候補を作る。

    v11.8c方針：
    - 評価1・2・3は固定する。
    - 第4枠Xは 1-4 / 1-5 / 1-6 / 1-7 だけを見る。
    - 回収差がプラスの候補は「＋につき除外」とする。
    - 回収差が0以下の候補だけで、安定差 = abs(想定差) + abs(回収差) を比較する。
    - 安定差が一番小さいXを選び、123XBOXを表示する。
    - 根拠表示は第4枠選定に必要な列だけに絞る。
    - 投資系の列（資産枠・配当位置・EV判定など）はこの表に混ぜない。
    """
    if df_pairs is None or df_pairs.empty:
        return None
    if "ペアキー" not in df_pairs.columns:
        return None

    work = df_pairs.copy()
    row_map = {}
    for _, row in work.iterrows():
        key = str(row.get("ペアキー", "")).strip()
        if key:
            row_map[key] = row

    def _str(row: pd.Series | None, col: str) -> str:
        if row is None:
            return ""
        try:
            v = row.get(col, "")
        except Exception:
            return ""
        if pd.isna(v):
            return ""
        return str(v)

    def _num(row: pd.Series | None, col: str, default=None):
        if row is None:
            return default
        try:
            v = row.get(col, default)
            if pd.isna(v):
                return default
            return float(v)
        except Exception:
            return default

    def classify_one(x: int) -> dict:
        key = f"1-{int(x)}"
        row = row_map.get(key)

        hit_diff = _num(row, "想定差", None)
        roi_diff = _num(row, "回収差", None)
        hit_abs = abs(float(hit_diff)) if hit_diff is not None else None
        roi_abs = abs(float(roi_diff)) if roi_diff is not None else None

        if hit_abs is not None and roi_abs is not None:
            stability_gap = round(hit_abs + roi_abs, 3)
            # 第4枠は「足りない側」を拾う設計にする。
            # 回収差がプラスの候補は、安定差が小さくても後追い扱いで除外する。
            if roi_diff is not None and float(roi_diff) > 0:
                selectable = False
                select_reason = "＋につき除外"
            else:
                selectable = True
                select_reason = "安定差計算可"
        else:
            stability_gap = None
            selectable = False
            select_reason = "差分不足"

        # 表示は「元データ→最終判定値」の順にする。
        # abs内訳は安定差の計算確認用であり、採用判定の独立条件にはしない。
        return {
            "第4枠": int(x),
            "1軸相手": key,
            "想定差": hit_diff,
            "回収差": roi_diff,
            "安定差": stability_gap,
            "判定": "",
            "選択可否": "可" if selectable else "不可",
            "選択理由": select_reason,
            "安定差内訳": (
                f"abs({hit_diff}) + abs({roi_diff}) = {round(hit_abs, 3)} + {round(roi_abs, 3)} = {stability_gap}"
                if hit_abs is not None and roi_abs is not None else "差分不足"
            ),
        }

    candidates_all = [classify_one(x) for x in (4, 5, 6, 7)]
    selectable = [c for c in candidates_all if c.get("選択可否") == "可"]

    if selectable:
        selectable = sorted(
            selectable,
            key=lambda r: (
                float(r.get("安定差", 999999.0)),
                int(r.get("第4枠", 9)),
            ),
        )
        best = selectable[0]
    else:
        # 通常は「回収差0以下」が候補になる。
        # ただし全候補がプラス、または差分不足の場合でも画面が空にならないように例外処理する。
        calc_candidates = [c for c in candidates_all if c.get("安定差") is not None]
        if calc_candidates:
            best = sorted(
                calc_candidates,
                key=lambda r: (
                    float(r.get("安定差", 999999.0)),
                    int(r.get("第4枠", 9)),
                ),
            )[0]
            best["選択理由"] = "全候補＋または対象外のため例外採用"
        else:
            fallback = next((c for c in candidates_all if int(c.get("第4枠", 0)) == 4), None)
            if fallback is None:
                return None
            best = fallback
            best["選択理由"] = "差分不足のため既定4枠"

    # 採用行・除外行を候補表上で明示する。
    best_x = int(best["第4枠"])
    for c in candidates_all:
        if int(c.get("第4枠", 0)) == best_x:
            c["判定"] = "◎採用"
            if c.get("選択可否") == "可":
                c["選択理由"] = "回収差0以下の中で安定差最小"
            else:
                c["選択理由"] = c.get("選択理由") or "例外採用"
        elif c.get("選択理由") == "＋につき除外":
            c["判定"] = "＋につき除外"
            c["選択理由"] = "回収差プラス"
        elif c.get("選択可否") == "可":
            c["判定"] = ""
            c["選択理由"] = "比較候補"
        else:
            c["判定"] = ""
            c["選択理由"] = "差分不足"

    def _candidate_sort_key(r):
        judge = str(r.get("判定", ""))
        if judge == "◎採用":
            rank = 0
        elif judge == "":
            rank = 1
        elif judge == "＋につき除外":
            rank = 2
        else:
            rank = 3
        return (
            rank,
            float(r.get("安定差") if r.get("安定差") is not None else 999999.0),
            int(r.get("第4枠", 9)),
        )

    candidates_all = sorted(candidates_all, key=_candidate_sort_key)

    x = best_x
    trio_keys = [
        _trio_key_from_parts(1, 2, 3),
        _trio_key_from_parts(1, 2, x),
        _trio_key_from_parts(1, 3, x),
        _trio_key_from_parts(2, 3, x),
    ]
    trio_keys = list(dict.fromkeys(trio_keys))

    hit_diff_best = best.get("想定差")
    roi_diff_best = best.get("回収差")
    stability_detail = best.get("安定差内訳", "差分不足")

    return {
        "型": f"123{x}BOX",
        "第4枠": x,
        "1軸相手": best.get("1軸相手"),
        "想定差": hit_diff_best,
        "回収差": roi_diff_best,
        "安定差": best.get("安定差"),
        "安定差内訳": stability_detail,
        "判定": "◎採用",
        "選択理由": "回収差0以下の中で安定差最小（回収差プラスは除外）",
        "買い目": trio_keys,
        "candidate_rows": candidates_all,
    }



def build_axis1_stability_hybrid_formation_summary(
    df_pairs: pd.DataFrame,
    rank_total_map: Dict[int, Dict[str, int]] | None = None,
    pair12_counts: Dict[PairKey, int] | None = None,
) -> dict | None:
    """
    三連複フォーメーションを作る。

    方針：
    - 役割番号でフォーメーションを作る。
      1 = 軸（評価1）
      2 = 安定差1位
      3 = 1・2を除いた評価上位
      4 = 安定差2位
      5 = 1・2・3・4を除いた次の評価上位
    - 三連複は 12-123-12345（重複除外で7点）。
    - 3連単オッズゾーンは 12→123→12345（重複除外で12点）。
    - 2車単は 12→123（重複除外で4点）。
    - 安定差は abs(想定差) + abs(回収差)。
    - ここでは回収差プラス除外は使わない。

    重要：
    - オッズ帯に使う想定的中率は、当日だけの3連複実績では出さない。
    - 小倉基準も使わない。
    - 日々引き継いでいる「評価別3着内率」と「1→2着評価分布」を使って、
      累積評価ベースの三連複想定的中率を作る。
    """
    if df_pairs is None or df_pairs.empty:
        return None
    if "ペアキー" not in df_pairs.columns:
        return None

    work = df_pairs.copy()
    row_map = {}
    for _, row in work.iterrows():
        key = str(row.get("ペアキー", "")).strip()
        if key:
            row_map[key] = row

    def _num(row: pd.Series | None, col: str, default=None):
        if row is None:
            return default
        try:
            v = row.get(col, default)
            if pd.isna(v):
                return default
            return float(v)
        except Exception:
            return default

    candidates = []
    for x in range(2, FIELD_SIZE + 1):
        key = f"1-{int(x)}"
        row = row_map.get(key)
        hit_diff = _num(row, "想定差", None)
        roi_diff = _num(row, "回収差", None)
        if hit_diff is not None and roi_diff is not None:
            stability = round(abs(float(hit_diff)) + abs(float(roi_diff)), 3)
        else:
            stability = None
        candidates.append({
            "相手": int(x),
            "1軸相手": key,
            "想定差": hit_diff,
            "回収差": roi_diff,
            "安定差": stability,
            "判定": "",
            "選択理由": "差分不足" if stability is None else "比較候補",
        })

    valid = [c for c in candidates if c.get("安定差") is not None]
    if len(valid) < 2:
        return None

    valid_sorted = sorted(
        valid,
        key=lambda r: (
            float(r.get("安定差", 999999.0)),
            int(r.get("相手", 9)),
        ),
    )

    # =====================================================
    # 役割番号の決定
    # 1 = 軸（評価1）
    # 2 = 安定差1位
    # 3 = 1・2を除いた評価上位
    # 4 = 安定差2位
    # 5 = 1・2・3・4を除いた次の評価上位
    # =====================================================
    axis = 1
    role2 = int(valid_sorted[0]["相手"])

    role3 = None
    for r in range(2, FIELD_SIZE + 1):
        if r not in (axis, role2):
            role3 = int(r)
            break

    role4 = None
    for c in valid_sorted[1:]:
        cand = int(c["相手"])
        if cand not in (axis, role2, role3):
            role4 = cand
            break
    if role4 is None and len(valid_sorted) >= 2:
        role4 = int(valid_sorted[1]["相手"])

    role5 = None
    for r in range(2, FIELD_SIZE + 1):
        if r not in (axis, role2, role3, role4):
            role5 = int(r)
            break

    roles = [x for x in [axis, role2, role3, role4, role5] if x is not None]
    if len(roles) < 5:
        return None

    first_mates = [axis, role2]
    second_mates = [axis, role2, role3]
    third_mates = [axis, role2, role3, role4, role5]

    # 三連複：12-123-12345。重複除外・同一組み合わせ重複除外。
    trio_keys = []
    seen = set()
    for a in first_mates:
        for b in second_mates:
            for c in third_mates:
                vals = [int(a), int(b), int(c)]
                if len(set(vals)) != 3:
                    continue
                key = _trio_key_from_parts(vals[0], vals[1], vals[2])
                if key not in seen:
                    trio_keys.append(key)
                    seen.add(key)

    if not trio_keys:
        return None

    first_code = "".join(str(x) for x in first_mates)
    second_code = "".join(str(x) for x in second_mates)
    third_code = "".join(str(x) for x in third_mates)
    form_type = f"{first_code}-{second_code}-{third_code}"

    role_label_map = {
        role2: "②安定差1位",
        role3: "③評価上位",
        role4: "④安定差2位",
        role5: "⑤評価上位追加",
    }

    for c in candidates:
        x = int(c.get("相手", 0))
        if x in role_label_map:
            c["判定"] = role_label_map[x]
            if x == role2:
                c["選択理由"] = "安定差1位"
            elif x == role3:
                c["選択理由"] = "1・2を除いた評価上位"
            elif x == role4:
                c["選択理由"] = "安定差2位"
            elif x == role5:
                c["選択理由"] = "1・2・3・4を除いた次の評価上位"
        elif c.get("安定差") is not None:
            c["判定"] = ""
            c["選択理由"] = "比較候補"
        else:
            c["判定"] = ""
            c["選択理由"] = "差分不足"

    def _cand_sort_key(r):
        judge = str(r.get("判定", ""))
        if judge.startswith("②"):
            rank = 0
        elif judge.startswith("③"):
            rank = 1
        elif judge.startswith("④"):
            rank = 2
        elif judge.startswith("⑤"):
            rank = 3
        else:
            rank = 4
        return (
            rank,
            float(r.get("安定差") if r.get("安定差") is not None else 999999.0),
            int(r.get("相手", 9)),
        )

    candidate_rows = sorted(candidates, key=_cand_sort_key)

    # =====================================================
    # 累積評価ベースで三連複フォメの想定的中率を作る
    # =====================================================
    rank_total_map = rank_total_map or {}
    pair12_counts = pair12_counts or {}

    def _rank_place_rate(r: int):
        rec = rank_total_map.get(int(r), {})
        try:
            n = int(rec.get("N", 0) or 0)
            c1 = int(rec.get("C1", 0) or 0)
            c2 = int(rec.get("C2", 0) or 0)
            c3 = int(rec.get("C3", 0) or 0)
        except Exception:
            return None
        if n <= 0:
            return None
        return 100.0 * (c1 + c2 + c3) / n

    def _pair12_rate(a: int, b: int):
        try:
            a = int(a); b = int(b)
        except Exception:
            return None
        total = sum(int(v) for v in pair12_counts.values())
        if total <= 0 or a == b:
            return None
        hit = int(pair12_counts.get((a, b), 0)) + int(pair12_counts.get((b, a), 0))
        return 100.0 * hit / total

    axis_place = _rank_place_rate(1)

    # =====================================================
    # 三連複 12-123-12345 の累積評価ベース想定
    # 評価別3着内率の積で、全3車組の中のフォメカバー率を推定する。
    # =====================================================
    all_ranks = [r for r in range(1, FIELD_SIZE + 1)]
    place_weights = {r: (_rank_place_rate(r) or 0.0) for r in all_ranks}
    valid_trio_sets = set()
    for key in trio_keys:
        vals = tuple(sorted(int(x) for x in str(key).split("-")))
        if len(vals) == 3:
            valid_trio_sets.add(vals)

    denom = 0.0
    numer = 0.0
    for i, a in enumerate(all_ranks):
        for j in range(i + 1, len(all_ranks)):
            b = all_ranks[j]
            for k in range(j + 1, len(all_ranks)):
                c = all_ranks[k]
                w = float(place_weights.get(a, 0.0)) * float(place_weights.get(b, 0.0)) * float(place_weights.get(c, 0.0))
                denom += w
                if tuple(sorted((a, b, c))) in valid_trio_sets:
                    numer += w

    place_cover_rate = (100.0 * numer / denom) if denom > 0 else None

    # 1→2着評価分布側でも、フォメを構成する3車のうち2車が上位2着に入る頻度を見る。
    valid_edges = set()
    for key in trio_keys:
        vals = [int(x) for x in str(key).split("-")]
        for i, a in enumerate(vals):
            for b in vals[i + 1:]:
                valid_edges.add(tuple(sorted((int(a), int(b)))))

    pair_total = sum(int(v) for v in pair12_counts.values())
    pair_hit = 0
    if pair_total > 0:
        for a, b in valid_edges:
            pair_hit += int(pair12_counts.get((a, b), 0)) + int(pair12_counts.get((b, a), 0))
        pair_cover_rate = 100.0 * pair_hit / pair_total
    else:
        pair_cover_rate = None

    # 三連複の想定的中率は、3着内カバーを主、1→2着分布を弱補助にする。
    # pair_coverは「2車が上位2着に入る頻度」なので、そのままだと高く出る。
    if place_cover_rate is not None and pair_cover_rate is not None:
        cover_rate = 0.85 * place_cover_rate + 0.15 * pair_cover_rate
        cumulative_hit_rate = round(max(0.0, min(100.0, cover_rate)), 1)
    elif place_cover_rate is not None:
        cover_rate = place_cover_rate
        cumulative_hit_rate = round(max(0.0, min(100.0, cover_rate)), 1)
    else:
        cover_rate = None
        cumulative_hit_rate = None

    points = len(trio_keys)
    invest_per_race = points * 100

    if cumulative_hit_rate is not None and cumulative_hit_rate > 0:
        breakeven_avg_pay = round(invest_per_race / (cumulative_hit_rate / 100.0), 1)
    else:
        breakeven_avg_pay = None

    basis_n_values = []
    for r in range(1, FIELD_SIZE + 1):
        try:
            n = int(rank_total_map.get(r, {}).get("N", 0) or 0)
            if n > 0:
                basis_n_values.append(n)
        except Exception:
            pass
    basis_n = max(basis_n_values) if basis_n_values else 0

    estimate_rows = []
    for key in trio_keys:
        vals = [int(x) for x in str(key).split("-")]
        rates = [_rank_place_rate(v) for v in vals]
        estimate_rows.append({
            "買い目": key,
            "評価1_3着内率%": round(_rank_place_rate(1), 1) if _rank_place_rate(1) is not None else None,
            "構成評価3着内率%": " / ".join("—" if r is None else f"{r:.1f}" for r in rates),
            "補助2車複率%": round(sum((_pair12_rate(a, b) or 0.0) for i, a in enumerate(vals) for b in vals[i + 1:]), 1),
        })

    return {
        "型": form_type,
        "評価1軸": 1,
        "1列目": first_code,
        "2列目": second_code,
        "3列目": third_code,
        "役割1_軸": axis,
        "役割2_安定差1位": role2,
        "役割3_評価上位": role3,
        "役割4_安定差2位": role4,
        "役割5_評価上位追加": role5,
        "安定差上位2車": [role2, role4],
        "評価上位追加2車": [role3, role5],
        "買い目": trio_keys,
        "点数": points,

        # 累積評価ベース。購入判断・オッズ帯はこちらを使う。
        "累積対象N": basis_n,
        "評価1_3着内率%": round(axis_place, 1) if axis_place is not None else None,
        "相手3着内カバー率%": round(place_cover_rate, 1) if place_cover_rate is not None else None,
        "2車複カバー率%": round(pair_cover_rate, 1) if pair_cover_rate is not None else None,
        "合成カバー率%": round(cover_rate, 1) if cover_rate is not None else None,
        "累積評価ベース想定的中率%": cumulative_hit_rate,
        "100%必要平均払戻": breakeven_avg_pay,
        "累積評価ベース買い目別": estimate_rows,

        # 既存表示との互換用。中身は小倉基準でも本日実績でもなく、累積評価ベース。
        "想定的中率%": cumulative_hit_rate,
        "基準平均配当": None,
        "想定回収率%": None,

        "選択理由": "役割番号：1=軸、2=安定差1位、3=1・2を除いた評価上位、4=安定差2位、5=次の評価上位。三連複は12-123-12345。オッズ帯は累積評価別3着内率と1→2着評価分布から算出。",
        "candidate_rows": candidate_rows,
    }


# =========================
# Tabs
# =========================
tabs = st.tabs(["日次手入力（最大100R）", "前日までの集計（累積）", "分析結果"])

# 日次の入力行
byrace_rows: List[Dict] = []

# 前日まで：評価別（1～7）
agg_rank_manual: Dict[int, Dict[str, int]] = defaultdict(
    lambda: {"N": 0, "C1": 0, "C2": 0, "C3": 0}
)

# 前日まで：1→2（評価）
pair12_manual: Dict[PairKey, int] = defaultdict(int)

# 前日まで：1→3（評価）
pair13_manual: Dict[PairKey, int] = defaultdict(int)

# 前日まで：新回収率
# 2車単：1→23
agg_payout_2t_pattern_manual: Dict[int, Dict[str, int]] = {
    axis: new_payout_rec() for axis in PATTERN_AXES
}

# 前日まで：個別回収（任意入力）
# 1→2 / 1→3
agg_payout_axis_target_manual: Dict[Tuple[int, int], Dict[str, int]] = {
    (1, target): new_payout_rec() for target in INDIVIDUAL_AXIS1_TARGETS
}

# 前日まで：個別2車複（1・2軸＋3・4軸追加検証）
agg_payout_nishafuku_manual: Dict[str, Dict[str, int]] = {
    nishafuku_label(a, b): new_payout_rec() for a, b in NISHAFUKU_PAIRS
}
for a, b in NISHAFUKU_EXTRA_PAIRS:
    agg_payout_nishafuku_manual[nishafuku_label(a, b)] = new_payout_rec()

# 前日まで：34-12 2車複フォメ専用集計
# ここは手入力しない。個別2車複の累積（1-3/2-3/1-4/2-4）から自動合算する。
agg_payout_nishafuku_3412_manual: Dict[str, Dict[str, int]] = {
    NISHAFUKU_3412_LABEL: new_payout_rec(),
}

# 前日まで：3連複 1-2-全（仮想全体）
agg_payout_sanrenpuku12_all_manual: Dict[str, Dict[str, int]] = {
    "仮想全体": new_payout_rec(),
}

# 前日まで：3連複 1-2 個別（1-2-3～1-2-7）
agg_payout_sanrenpuku12_individual_manual: Dict[str, Dict[str, Dict[str, int]]] = {
    "仮想全体": {k: new_payout_rec() for k in TRIO_USED_KEYS},
}



# =========================
# A. 日次手入力（欠車対応）
# =========================
with tabs[0]:
    st.subheader("日次手入力（7車ベース・欠車対応・最大100R）")
    st.caption(
        "入力中の白化を抑えるため、フォーム送信式です。"
        "V評価は頭数ぶんの桁数で入力（例：7車=1432567 / 6車=143256）。"
        "着順は～3桁。2車複配当のみ入力します。"
        "三連複は実配当入力を使わず、評価別3着内率×カバー率から必要平均払戻を算出します。"
    )

    with st.form("daily_input_form"):
        cols_hdr = st.columns([0.7, 0.8, 2.8, 1.0, 1.0])
        cols_hdr[0].markdown("**R**")
        cols_hdr[1].markdown("**頭数**")
        cols_hdr[2].markdown("**V評価（頭数ぶんの桁数）**")
        cols_hdr[3].markdown("**着順(～3桁)**")
        cols_hdr[4].markdown("**2車複**")

        daily_inputs = []

        for i in range(1, 101):
            c1, c2, c3, c4, c5 = st.columns([0.7, 0.8, 2.8, 1.0, 1.0])

            rid = c1.text_input("", key=f"rid_{i}", value=str(i))
            field_n = c2.selectbox("", options=[7, 6, 5], index=0, key=f"field_n_{i}")
            vline = c3.text_input("", key=f"vline_{i}", value="")
            fin = c4.text_input("", key=f"fin_{i}", value="")
            pay_2f = c5.number_input("", key=f"pay2f_{i}", min_value=0, value=0, step=10)
            pay_3f = 0
            pay_2t = 0

            daily_inputs.append(
                {
                    "rid": rid,
                    "field_n": field_n,
                    "vline": vline,
                    "fin": fin,
                    "pay_2t": pay_2t,
                    "pay_2f": pay_2f,
                    "pay_3f": pay_3f,
                }
            )

        st.form_submit_button("日次入力を反映")

    for item in daily_inputs:
        rid = item["rid"]
        field_n = int(item["field_n"])
        vline = item["vline"]
        fin = item["fin"]
        pay_2t = int(item["pay_2t"])
        pay_2f = int(item["pay_2f"])
        pay_3f = int(item.get("pay_3f", 0))
        vorder = parse_rankline(vline, field_n)
        finish = parse_finish(fin)

        any_input = any([vline.strip(), fin.strip(), pay_2f > 0])
        if any_input:
            if not vorder:
                st.warning(f"R{rid}: 頭数{field_n}なので、V評価は{field_n}桁で入力してください。")
                continue

            vset = set(vorder)
            invalid_finish = [x for x in finish if x not in vset]
            if invalid_finish:
                st.warning(
                    f"R{rid}: 着順 {''.join(invalid_finish)} がV評価（出走車）に含まれていません。"
                    " 欠車/入力ミスの可能性があります。"
                )

            byrace_rows.append(
                {
                    "race": rid,
                    "field_n": field_n,
                    "vorder": vorder,
                    "finish": finish,
                    "pay_2t": pay_2t,
                    "pay_2f": pay_2f,
                    "pay_3f": pay_3f,
                }
            )


# =========================
# B. 前日までの集計（累積）
# =========================
with tabs[1]:
    st.markdown('<a id="prev-aggregate"></a>', unsafe_allow_html=True)
    st.subheader("前日までの集計（累積・全体）")
    st.caption("入力中の白化を抑えるため、フォーム送信式です。入力後に下のボタンを押してください。")

    with st.form("prev_aggregate_form"):
        cols_12 = list(range(1, FIELD_SIZE + 1))

        st.markdown("## 1→2 着評価分布（累積・回数）")
        st.caption("1着が評価1〜7のとき、2着の評価の回数を入力。")

        h = st.columns([1.8] + [1] * len(cols_12))
        h[0].markdown("**条件：1着の評価**")
        for j, rr in enumerate(cols_12, start=1):
            h[j].markdown(f"**2着={rr}**")

        pair_inputs = []
        for wr in WINNER_RANKS:
            row_cols = st.columns([1.8] + [1] * len(cols_12))
            row_cols[0].write(f"評価{wr}が1着")
            for j, rr in enumerate(cols_12, start=1):
                if rr == wr:
                    row_cols[j].write("")
                    continue
                v = row_cols[j].number_input(
                    "",
                    key=f"pair12_prev_wr{wr}_rr{rr}",
                    min_value=0,
                    value=0,
                )
                pair_inputs.append((wr, rr, int(v)))

        st.divider()

        st.markdown("## 1→3 着評価分布（累積・回数）")
        st.caption("1着が評価1〜7のとき、3着の評価の回数を入力。")

        h13 = st.columns([1.8] + [1] * len(cols_12))
        h13[0].markdown("**条件：1着の評価**")
        for j, rr in enumerate(cols_12, start=1):
            h13[j].markdown(f"**3着={rr}**")

        pair13_inputs = []
        for wr in WINNER_RANKS:
            row_cols = st.columns([1.8] + [1] * len(cols_12))
            row_cols[0].write(f"評価{wr}が1着")
            for j, rr in enumerate(cols_12, start=1):
                if rr == wr:
                    row_cols[j].write("")
                    continue
                v = row_cols[j].number_input(
                    "",
                    key=f"pair13_prev_wr{wr}_rr{rr}",
                    min_value=0,
                    value=0,
                )
                pair13_inputs.append((wr, rr, int(v)))

        st.divider()

        st.markdown("## 評価別 入賞回数（累積）")
        st.caption("評価1～7まで入力。Nは各評価が存在したレース数。")

        hdr = st.columns([1.8, 1, 1, 1.8])
        hdr[0].markdown("**評価**")
        hdr[1].markdown("**出走数N**")
        hdr[2].markdown("**1着回数**")
        hdr[3].markdown("**2着回数 / 3着回数**")

        rank_inputs = []
        for r in range(1, 8):
            c0, c1, c2, c3 = st.columns([1.8, 1, 1, 1.8])
            c0.write(rank_symbol(r))
            N = c1.number_input("", key=f"aggN_{r}", min_value=0, value=0)
            C1 = c2.number_input("", key=f"aggC1_{r}", min_value=0, value=0)
            c3_cols = c3.columns(2)
            C2 = c3_cols[0].number_input("", key=f"aggC2_{r}", min_value=0, value=0)
            C3 = c3_cols[1].number_input("", key=f"aggC3_{r}", min_value=0, value=0)
            rank_inputs.append((r, int(N), int(C1), int(C2), int(C3)))

        st.divider()

        st.divider()

        st.markdown("## 個別2車複 引継ぎ入力（累積）")
        st.caption(
            "対象N・払戻合計SUM・的中Hを入力。KSUMは対象Nと同じ1点扱いで自動計算します。"
            "今回から3-4/3-5/3-6/3-7、4-5/4-6/4-7も追加しています。"
        )
        hdr_nf = st.columns([1.4, 1, 1.4, 1])
        hdr_nf[0].markdown("**型**")
        hdr_nf[1].markdown("**対象N**")
        hdr_nf[2].markdown("**払戻合計SUM**")
        hdr_nf[3].markdown("**的中H**")

        nishafuku_pair_inputs = []
        for a, b in NISHAFUKU_PAIRS:
            label = nishafuku_label(a, b)
            key_base = f"nishafuku_prev_{a}_{b}"
            c0, c1, c2, c3 = st.columns([1.4, 1, 1.4, 1])
            c0.write(label)
            N = c1.number_input("", key=f"{key_base}_N", min_value=0, value=0)
            SUM = c2.number_input("", key=f"{key_base}_SUM", min_value=0, value=0, step=10)
            H = c3.number_input("", key=f"{key_base}_H", min_value=0, value=0)
            nishafuku_pair_inputs.append((label, int(N), int(SUM), int(H)))

        st.markdown("## 個別2車複 的中ゾーン入力（累積）")
        st.caption("的中した2車複の払戻倍率帯だけを入力。10倍以下を 〜3 / 3.1〜6 / 6.1〜10 に分けます。")
        hdr_z = st.columns([1.4, 0.8, 0.8, 0.9, 1.0, 1.0])
        hdr_z[0].markdown("**型**")
        hdr_z[1].markdown("**〜3倍**")
        hdr_z[2].markdown("**3.1〜6倍**")
        hdr_z[3].markdown("**6.1〜10倍**")
        hdr_z[4].markdown("**10.1〜20倍**")
        hdr_z[5].markdown("**20.1倍〜**")

        nishafuku_zone_inputs = []
        for a, b in NISHAFUKU_PAIRS:
            label = nishafuku_label(a, b)
            key_base = f"nishafuku_zone_prev_{a}_{b}"
            c0, c1, c2, c3, c4, c5 = st.columns([1.4, 0.8, 0.8, 0.9, 1.0, 1.0])
            c0.write(label)
            Z3 = c1.number_input("", key=f"{key_base}_Z3", min_value=0, value=0)
            Z6 = c2.number_input("", key=f"{key_base}_Z6", min_value=0, value=0)
            Z10 = c3.number_input("", key=f"{key_base}_Z10", min_value=0, value=0)
            Z20 = c4.number_input("", key=f"{key_base}_Z20", min_value=0, value=0)
            Z20P = c5.number_input("", key=f"{key_base}_Z20P", min_value=0, value=0)
            nishafuku_zone_inputs.append((label, int(Z3), int(Z6), int(Z10), int(Z20), int(Z20P)))

        # 既存処理との互換用に空リストだけ残します。
        payout_inputs = []
        sanrenpuku12_inputs = []
        sanrenpuku12_individual_inputs = []
        nishafuku_set_inputs = []

        st.form_submit_button("前日までの集計を反映")

    for wr, rr, v in pair_inputs:
        if v:
            pair12_manual[(wr, rr)] += int(v)

    for wr, rr, v in pair13_inputs:
        if v:
            pair13_manual[(wr, rr)] += int(v)

    for r, N, C1, C2, C3 in rank_inputs:
        if any([N, C1, C2, C3]):
            rec = agg_rank_manual[r]
            rec["N"] += int(N)
            rec["C1"] += int(C1)
            rec["C2"] += int(C2)
            rec["C3"] += int(C3)

    for axis, N, KSUM, SUM, H in payout_inputs:
        if any([N, KSUM, SUM, H]):
            rec = agg_payout_2t_pattern_manual[axis]
            rec["N"] += int(N)
            rec["KSUM"] += int(KSUM)
            rec["SUM"] += int(SUM)
            rec["H"] += int(H)

    for label, N, SUM, H in nishafuku_pair_inputs:
        if any([N, SUM, H]) and label in agg_payout_nishafuku_manual:
            rec = agg_payout_nishafuku_manual[label]
            rec["N"] += int(N)
            rec["KSUM"] += int(N)
            rec["SUM"] += int(SUM)
            rec["H"] += int(H)

    for label, Z3, Z6, Z10, Z20, Z20P in nishafuku_zone_inputs:
        if any([Z3, Z6, Z10, Z20, Z20P]) and label in agg_payout_nishafuku_manual:
            rec = agg_payout_nishafuku_manual[label]
            rec["Z3"] += int(Z3)
            rec["Z6"] += int(Z6)
            rec["Z10"] += int(Z10)
            rec["Z20"] += int(Z20)
            rec["Z20P"] += int(Z20P)

    # 34-12前日まで分は専用入力を持たせず、既存の個別2車複引継ぎから自動合算する。
    # Nは4点の最大N、KSUM/SUM/Hは4点合計。
    agg_payout_nishafuku_3412_manual[NISHAFUKU_3412_LABEL] = rec_for_labels(
        agg_payout_nishafuku_manual,
        NISHAFUKU_3412_SOURCE_LABELS,
    )

    for label, N, SUM, H in sanrenpuku12_inputs:
        if any([N, SUM, H]) and label in agg_payout_sanrenpuku12_all_manual:
            rec = agg_payout_sanrenpuku12_all_manual[label]
            rec["N"] += int(N)
            rec["KSUM"] += int(N) * 5
            rec["SUM"] += int(SUM)
            rec["H"] += int(H)

    for label, key, N, SUM, H in sanrenpuku12_individual_inputs:
        if any([N, SUM, H]) and label in agg_payout_sanrenpuku12_individual_manual and key in agg_payout_sanrenpuku12_individual_manual[label]:
            rec = agg_payout_sanrenpuku12_individual_manual[label][key]
            rec["N"] += int(N)
            rec["KSUM"] += int(N)
            rec["SUM"] += int(SUM)
            rec["H"] += int(H)

    for set_label, N, KSUM, SUM, H in nishafuku_set_inputs:
        if any([N, KSUM, SUM, H]):
            rec = agg_payout_nishafuku_set_manual[set_label]
            rec["N"] += int(N)
            rec["KSUM"] += int(KSUM)
            rec["SUM"] += int(SUM)
            rec["H"] += int(H)


# =========================
# 集計：日次 + 前日まで累積
# =========================
rank_daily: Dict[int, Dict[str, int]] = {
    r: {"N": 0, "C1": 0, "C2": 0, "C3": 0} for r in range(1, 8)
}

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    if not vorder:
        continue

    car_by_rank = {i + 1: vorder[i] for i in range(len(vorder))}

    for r in range(1, len(vorder) + 1):
        rank_daily[r]["N"] += 1
        car = car_by_rank.get(r)
        if car is None:
            continue

        if len(finish) >= 1 and finish[0] == car:
            rank_daily[r]["C1"] += 1
        if len(finish) >= 2 and finish[1] == car:
            rank_daily[r]["C2"] += 1
        if len(finish) >= 3 and finish[2] == car:
            rank_daily[r]["C3"] += 1

rank_total: Dict[int, Dict[str, int]] = {
    r: {"N": 0, "C1": 0, "C2": 0, "C3": 0} for r in range(1, 8)
}

for r in range(1, 8):
    for k in ("N", "C1", "C2", "C3"):
        rank_total[r][k] += rank_daily[r][k]

for r, rec in agg_rank_manual.items():
    if r in rank_total:
        rank_total[r]["N"] += rec["N"]
        rank_total[r]["C1"] += rec["C1"]
        rank_total[r]["C2"] += rec["C2"]
        rank_total[r]["C3"] += rec["C3"]

pair12_daily: Dict[PairKey, int] = defaultdict(int)
pair13_daily: Dict[PairKey, int] = defaultdict(int)

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    if len(finish) < 2 or not vorder:
        continue

    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}
    win_rank = car_to_rank.get(finish[0])
    sec_rank = car_to_rank.get(finish[1])

    if win_rank is None or sec_rank is None:
        continue

    pair12_daily[(int(win_rank), int(sec_rank))] += 1

    if len(finish) >= 3:
        third_rank = car_to_rank.get(finish[2])
        if third_rank is not None:
            pair13_daily[(int(win_rank), int(third_rank))] += 1

pair12_total: Dict[PairKey, int] = defaultdict(int)
for k, v in pair12_daily.items():
    pair12_total[k] += int(v)
for k, v in pair12_manual.items():
    pair12_total[k] += int(v)

pair13_total: Dict[PairKey, int] = defaultdict(int)
for k, v in pair13_daily.items():
    pair13_total[k] += int(v)
for k, v in pair13_manual.items():
    pair13_total[k] += int(v)

# --- 新回収率（日次） ---
# 2車単：1→23
payout_2t_pattern_daily: Dict[int, Dict[str, int]] = {
    axis: new_payout_rec() for axis in PATTERN_AXES
}

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    field_n = int(row.get("field_n", len(vorder) or 0))

    if not vorder or field_n <= 0 or len(finish) < 2:
        continue

    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}

    win_rank = car_to_rank.get(finish[0])
    sec_rank = car_to_rank.get(finish[1])

    if win_rank is None or sec_rank is None:
        continue

    win_rank = int(win_rank)
    sec_rank = int(sec_rank)
    pay_2t = int(row.get("pay_2t", 0))

    for axis in PATTERN_AXES:
        ksum = ksum_2t_pattern(axis, field_n)
        if ksum <= 0:
            continue

        rec = payout_2t_pattern_daily[axis]
        rec["N"] += 1
        rec["KSUM"] += ksum

        if hit_2t_pattern(axis, win_rank, sec_rank, field_n):
            if pay_2t > 0:
                rec["H"] += 1
                rec["SUM"] += pay_2t

# --- 個別（日次） ---
# 2車単：1→2 / 1→3
INDIVIDUAL_PAIRS = [(1, target) for target in INDIVIDUAL_AXIS1_TARGETS]
payout_axis_target_daily: Dict[Tuple[int, int], Dict[str, int]] = {
    pair: new_payout_rec() for pair in INDIVIDUAL_PAIRS
}

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    field_n = int(row.get("field_n", len(vorder) or 0))

    if not vorder or field_n <= 0 or len(finish) < 2:
        continue

    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}

    win_rank = car_to_rank.get(finish[0])
    sec_rank = car_to_rank.get(finish[1])

    if win_rank is None or sec_rank is None:
        continue

    win_rank = int(win_rank)
    sec_rank = int(sec_rank)
    pay_2t = int(row.get("pay_2t", 0))

    for axis, target in INDIVIDUAL_PAIRS:
        ksum = ksum_axis_to_target(axis, target, field_n)
        if ksum <= 0:
            continue

        rec = payout_axis_target_daily[(axis, target)]
        rec["N"] += 1
        rec["KSUM"] += ksum

        if hit_axis_to_target(axis, target, win_rank, sec_rank, field_n):
            if pay_2t > 0:
                rec["H"] += 1
                rec["SUM"] += pay_2t


# --- 2車複シミュレーション（日次） ---
payout_nishafuku_daily: Dict[str, Dict[str, int]] = {
    nishafuku_label(a, b): new_payout_rec() for a, b in NISHAFUKU_PAIRS
}
for a, b in NISHAFUKU_EXTRA_PAIRS:
    payout_nishafuku_daily[nishafuku_label(a, b)] = new_payout_rec()

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    field_n = int(row.get("field_n", len(vorder) or 0))

    if not vorder or field_n <= 0 or len(finish) < 2:
        continue

    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}

    win_rank = car_to_rank.get(finish[0])
    sec_rank = car_to_rank.get(finish[1])

    if win_rank is None or sec_rank is None:
        continue

    win_rank = int(win_rank)
    sec_rank = int(sec_rank)
    pay_2f = int(row.get("pay_2f", 0))


    for a, b in NISHAFUKU_PAIRS:
        label = nishafuku_label(a, b)
        ksum = ksum_nishafuku_pair(a, b, field_n)
        if ksum <= 0:
            continue

        rec = payout_nishafuku_daily[label]
        rec["N"] += 1
        rec["KSUM"] += ksum

        if hit_nishafuku_pair(a, b, win_rank, sec_rank, field_n):
            if pay_2f > 0:
                rec["H"] += 1
                rec["SUM"] += pay_2f
                zkey = payout_zone_key(pay_2f)
                if zkey:
                    rec[zkey] += 1


    for a, b in NISHAFUKU_EXTRA_PAIRS:
        label = nishafuku_label(a, b)
        ksum = ksum_nishafuku_pair(a, b, field_n)
        if ksum <= 0:
            continue

        rec = payout_nishafuku_daily[label]
        rec["N"] += 1
        rec["KSUM"] += ksum

        if hit_nishafuku_pair(a, b, win_rank, sec_rank, field_n):
            if pay_2f > 0:
                rec["H"] += 1
                rec["SUM"] += pay_2f
                zkey = payout_zone_key(pay_2f)
                if zkey:
                    rec[zkey] += 1





# --- 34-12 2車複フォメ（日次） ---
payout_nishafuku_3412_daily: Dict[str, Dict[str, int]] = {
    NISHAFUKU_3412_LABEL: new_payout_rec(),
}

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    field_n = int(row.get("field_n", len(vorder) or 0))

    if not vorder or field_n <= 0 or len(finish) < 2:
        continue

    car_to_rank = {car: i + 1 for i, car in enumerate(vorder)}
    win_rank = car_to_rank.get(finish[0])
    sec_rank = car_to_rank.get(finish[1])

    if win_rank is None or sec_rank is None:
        continue

    ksum = ksum_nishafuku_3412(field_n)
    if ksum <= 0:
        continue

    rec = payout_nishafuku_3412_daily[NISHAFUKU_3412_LABEL]
    rec["N"] += 1
    rec["KSUM"] += ksum

    if hit_nishafuku_3412(int(win_rank), int(sec_rank), field_n):
        pay_2f = int(row.get("pay_2f", 0))
        if pay_2f > 0:
            rec["H"] += 1
            rec["SUM"] += pay_2f
            zkey = payout_zone_key(pay_2f)
            if zkey:
                rec[zkey] += 1


# --- 123-123-4 / 124-124-3 三連複3点（日次・配当なし） ---
payout_trio_1231234_daily: Dict[str, Dict[str, int]] = {
    TRIO_1231234_LABEL: new_payout_rec(),
}
payout_trio_1241243_daily: Dict[str, Dict[str, int]] = {
    TRIO_1241243_LABEL: new_payout_rec(),
}

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    field_n = int(row.get("field_n", len(vorder) or 0))

    if not vorder or field_n <= 0 or len(finish) < 3:
        continue

    if field_n < 4:
        continue

    rec = payout_trio_1231234_daily[TRIO_1231234_LABEL]
    rec["N"] += 1
    rec["KSUM"] += len(TRIO_1231234_KEYS)
    if hit_trio_1231234(vorder, finish, field_n):
        rec["H"] += 1

    rec = payout_trio_1241243_daily[TRIO_1241243_LABEL]
    rec["N"] += 1
    rec["KSUM"] += len(TRIO_1241243_KEYS)
    if hit_trio_1241243(vorder, finish, field_n):
        rec["H"] += 1


# --- 3連複 1-2-全（日次） ---
payout_sanrenpuku12_all_daily: Dict[str, Dict[str, int]] = {
    "仮想全体": new_payout_rec(),
}
payout_sanrenpuku12_individual_daily: Dict[str, Dict[str, Dict[str, int]]] = {
    "仮想全体": {k: new_payout_rec() for k in TRIO_USED_KEYS},
}

for row in byrace_rows:
    vorder = row.get("vorder", [])
    finish = row.get("finish", [])
    field_n = int(row.get("field_n", len(vorder) or 0))

    if not vorder or field_n <= 0 or len(finish) < 3:
        continue

    ksum = ksum_sanrenpuku_12_all(field_n)
    if ksum <= 0:
        continue

    # 三連複の実配当入力は廃止。的中Hだけ参考集計し、SUMは使わない。
    pay_3f = 0
    is_hit = hit_sanrenpuku_12_all(vorder, finish, field_n)

    rec_all = payout_sanrenpuku12_all_daily["仮想全体"]
    rec_all["N"] += 1
    rec_all["KSUM"] += ksum
    if is_hit:
        rec_all["H"] += 1

    # 個別3連複。実運用対象の1・2絡みだけを、存在する評価ごとに毎回1点仮想購入。
    for key in TRIO_USED_KEYS:
        one_ksum = ksum_sanrenpuku_key(key, field_n)
        if one_ksum <= 0:
            continue
        one_hit = hit_sanrenpuku_key(key, vorder, finish, field_n)

        rec_ind_all = payout_sanrenpuku12_individual_daily["仮想全体"][key]
        rec_ind_all["N"] += 1
        rec_ind_all["KSUM"] += one_ksum
        if one_hit:
            rec_ind_all["H"] += 1


payout_2t_pattern_total: Dict[int, Dict[str, int]] = {
    axis: new_payout_rec() for axis in PATTERN_AXES
}

for axis in PATTERN_AXES:
    add_rec(payout_2t_pattern_total[axis], payout_2t_pattern_daily[axis])
    add_rec(payout_2t_pattern_total[axis], agg_payout_2t_pattern_manual[axis])


payout_axis_target_total: Dict[Tuple[int, int], Dict[str, int]] = {
    pair: new_payout_rec() for pair in INDIVIDUAL_PAIRS
}

for pair in INDIVIDUAL_PAIRS:
    add_rec(payout_axis_target_total[pair], payout_axis_target_daily[pair])
    add_rec(payout_axis_target_total[pair], agg_payout_axis_target_manual[pair])

payout_nishafuku_total: Dict[str, Dict[str, int]] = {
    nishafuku_label(a, b): new_payout_rec() for a, b in NISHAFUKU_PAIRS
}
for a, b in NISHAFUKU_EXTRA_PAIRS:
    payout_nishafuku_total[nishafuku_label(a, b)] = new_payout_rec()

for label in payout_nishafuku_total.keys():
    add_rec(payout_nishafuku_total[label], payout_nishafuku_daily[label])
    add_rec(payout_nishafuku_total[label], agg_payout_nishafuku_manual[label])


payout_nishafuku_3412_total: Dict[str, Dict[str, int]] = {
    NISHAFUKU_3412_LABEL: new_payout_rec(),
}
for label in payout_nishafuku_3412_total.keys():
    add_rec(payout_nishafuku_3412_total[label], payout_nishafuku_3412_daily[label])
    add_rec(payout_nishafuku_3412_total[label], agg_payout_nishafuku_3412_manual[label])


payout_sanrenpuku12_all_total: Dict[str, Dict[str, int]] = {
    "仮想全体": new_payout_rec(),
}
for label in payout_sanrenpuku12_all_total.keys():
    add_rec(payout_sanrenpuku12_all_total[label], payout_sanrenpuku12_all_daily[label])
    add_rec(payout_sanrenpuku12_all_total[label], agg_payout_sanrenpuku12_all_manual[label])

payout_sanrenpuku12_individual_total: Dict[str, Dict[str, Dict[str, int]]] = {
    "仮想全体": {k: new_payout_rec() for k in TRIO_USED_KEYS},
}
for label in payout_sanrenpuku12_individual_total.keys():
    for key in TRIO_USED_KEYS:
        add_rec(payout_sanrenpuku12_individual_total[label][key], payout_sanrenpuku12_individual_daily[label][key])
        add_rec(payout_sanrenpuku12_individual_total[label][key], agg_payout_sanrenpuku12_individual_manual[label][key])


# =========================
# 出力：分析結果
# =========================
with tabs[2]:
    st.markdown('<a id="analysis-result"></a>', unsafe_allow_html=True)
    st.subheader("1→2 着評価分布（全体累積）｜1着が評価1〜7のとき（欠車対応）")
    st.caption("欠車レースでは存在しない下位評価はNに含まれません。")

    df12_count, df12_pct = build_conditional_tables(pair12_total)

    st.markdown("### 回数（Nは条件付き総数）")
    st.dataframe(df12_count, use_container_width=True, hide_index=True)

    st.markdown("### 割合%（同評価セルは空欄）")
    st.dataframe(df12_pct, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("1→3 着評価分布（全体累積）｜1着が評価1〜7のとき（欠車対応）")
    st.caption("欠車レースでは存在しない下位評価はNに含まれません。")

    df13_count, df13_pct = build_conditional_tables_13(pair13_total)

    st.markdown("### 回数（Nは条件付き総数）")
    st.dataframe(df13_count, use_container_width=True, hide_index=True)

    st.markdown("### 割合%（同評価セルは空欄）")
    st.dataframe(df13_pct, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("評価別 入賞テーブル（全体累積）｜欠車対応")
    rows_out = []
    for r in range(1, 8):
        rec = rank_total.get(r, {"N": 0, "C1": 0, "C2": 0, "C3": 0})
        N, C1, C2, C3 = rec["N"], rec["C1"], rec["C2"], rec["C3"]
        rows_out.append(
            {
                "評価": rank_symbol(r),
                "出走数N": N,
                "1着回数": C1,
                "2着回数": C2,
                "3着回数": C3,
                "1着率%": rate(C1, N),
                "連対率%": rate(C1 + C2, N),
                "3着内率%": rate(C1 + C2 + C3, N),
            }
        )
    st.dataframe(pd.DataFrame(rows_out), use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("個別2車複 引継ぎ用累積表")
    st.caption(
        "1・2軸に加え、評価3軸・評価4軸の追加検証として "
        "3-4/3-5/3-6/3-7、4-5/4-6/4-7 を同じ表に追加しています。"
    )
    df_nishafuku_individual = pd.DataFrame([
        nishafuku_individual_row(nishafuku_label(a, b), payout_nishafuku_total[nishafuku_label(a, b)], pair12_total)
        for a, b in NISHAFUKU_PAIRS
        if nishafuku_label(a, b) in payout_nishafuku_total
    ])
    cols_nishafuku_individual = [
        "型",
        "ペアキー",
        "対象N",
        "払戻合計SUM",
        "的中H",
        "的中率%",
        "平均配当",
        "ペア基準配当",
        "想定ペア的%",
        "想定回収率%",
        "回収率%",
        "想定差",
        "回収差",
    ]
    render_sortable_table(
        df_nishafuku_individual[[c for c in cols_nishafuku_individual if c in df_nishafuku_individual.columns]]
    )

    st.divider()

    st.subheader("個別2車複 的中ゾーン分布")
    st.caption("的中時の払戻倍率帯。累積表とは独立表示にして、文字が小さくならないようにしています。")
    zone_recs = [
        payout_nishafuku_total[nishafuku_label(a, b)]
        for a, b in NISHAFUKU_PAIRS
        if nishafuku_label(a, b) in payout_nishafuku_total
    ]
    zone_rows = [
        zone_row(f"{a}-{b}", payout_nishafuku_total[nishafuku_label(a, b)])
        for a, b in NISHAFUKU_PAIRS
        if nishafuku_label(a, b) in payout_nishafuku_total
    ]
    zone_rows.append(zone_total_row(zone_recs))
    df_zone = pd.DataFrame(zone_rows)
    zone_cols = ["ペア", "的中H", "〜3倍", "3.1〜6倍", "6.1〜10倍", "10.1〜20倍", "20.1倍〜", "ゾーン確認"]
    render_sortable_table(df_zone[[c for c in zone_cols if c in df_zone.columns]])

    st.divider()

    st.markdown("### 123-123-4 / 124-124-3 三連複3点｜推定集計ゾーン")
    st.caption(
        "実三連複配当は入力しません。既存の1→2着評価分布と評価別3着回数から、"
        "123-123-4 と 124-124-3 の3点的中数を条件付き按分で推定します。"
        "金額・払戻・回収率は出しません。日次入力分だけは実着順から的中Hを出します。"
    )

    trio_1231234_est = estimate_trio_1231234_from_pair12_and_rank(pair12_total, rank_total)
    trio_1241243_est = estimate_trio_1241243_from_pair12_and_rank(pair12_total, rank_total)
    rec_trio_1231234_daily = payout_trio_1231234_daily.get(TRIO_1231234_LABEL, new_payout_rec())
    rec_trio_1241243_daily = payout_trio_1241243_daily.get(TRIO_1241243_LABEL, new_payout_rec())
    df_trio_1231234 = pd.DataFrame([
        trio_1231234_daily_row(rec_trio_1231234_daily),
        {k: v for k, v in trio_1231234_est.items() if k != "detail_rows"},
        trio_1241243_daily_row(rec_trio_1241243_daily),
        {k: v for k, v in trio_1241243_est.items() if k != "detail_rows"},
    ])
    cols_trio_1231234 = [
        "型",
        "構成",
        "対象N",
        "総点数KSUM",
        "的中H",
        "的中率%",
        "推定H",
        "推定的中率%",
    ]
    render_sortable_table(df_trio_1231234[[c for c in cols_trio_1231234 if c in df_trio_1231234.columns]])

    if trio_1231234_est.get("detail_rows"):
        with st.expander("123-123-4 推定内訳（1→2着ペア別）", expanded=False):
            render_sortable_table(pd.DataFrame(trio_1231234_est["detail_rows"]))

    if trio_1241243_est.get("detail_rows"):
        with st.expander("124-124-3 推定内訳（1→2着ペア別）", expanded=False):
            render_sortable_table(pd.DataFrame(trio_1241243_est["detail_rows"]))
