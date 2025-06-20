import streamlit as st
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="ライン競輪スコア計算（完全統一版）", layout="wide")

st.title("⭐ ライン競輪スコア計算（9車ライン＋欠番対応）⭐")

wind_coefficients = {
    "左上": -0.07,   # ホーム寄りからの風 → 差し有利（逃げやや不利）
    "上":   -0.10,   # バック向かい風 → 逃げ最大不利
    "右上": -0.07,   # 差しやや有利

    "左":   +0.10,   # ホーム向かい風 → 差し不利、逃げ有利
    "右":   -0.10,   # バック追い風 → 差し不利、逃げ有利

    "左下": +0.07,   # ゴール寄り追い風 → 差しやや有利
    "下":   +0.10,   # ゴール強追い風 → 差し最大有利（逃げ最大不利）
    "右下": +0.07    # 差しやや有利
}
position_multipliers = {
    0: 0.6,  # 単騎
    1: 0.65,  # 先頭
    2: 0.6,
    3: 0.5,
    4: 0.4  # 4番手
}


# --- 基本スコア（脚質ごとの基準値） ---
base_score = {'逃': 4.7, '両': 4.8, '追': 5.0}

# --- 状態保持 ---
if "selected_wind" not in st.session_state:
    st.session_state.selected_wind = "無風"

# --- バンク・風条件セクション ---
st.header("【バンク・風条件】")

cols_top = st.columns(3)
cols_mid = st.columns(3)
cols_bot = st.columns(3)

with cols_top[0]:
    if st.button("左上"):
        st.session_state.selected_wind = "左上"
with cols_top[1]:
    if st.button("上"):
        st.session_state.selected_wind = "上"
with cols_top[2]:
    if st.button("右上"):
        st.session_state.selected_wind = "右上"
with cols_mid[0]:
    if st.button("左"):
        st.session_state.selected_wind = "左"
with cols_mid[1]:
    st.markdown("""
    <div style='text-align:center; font-size:16px; line-height:1.6em;'>
        ↑<br>［上］<br>
        ← 左　　　右 →<br>
        ［下］<br>↓<br>
        □ ホーム→（ ゴール）
    </div>
    """, unsafe_allow_html=True)
with cols_mid[2]:
    if st.button("右"):
        st.session_state.selected_wind = "右"
with cols_bot[0]:
    if st.button("左下"):
        st.session_state.selected_wind = "左下"
with cols_bot[1]:
    if st.button("下"):
        st.session_state.selected_wind = "下"
with cols_bot[2]:
    if st.button("右下"):
        st.session_state.selected_wind = "右下"

st.subheader(f"✅ 選択中の風向き：{st.session_state.selected_wind}")

# ▼ 競輪場選択による自動入力
keirin_data = {
    "函館": {"bank_angle": 30.6, "straight_length": 51.3, "bank_length": 400},
    "青森": {"bank_angle": 32.3, "straight_length": 58.9, "bank_length": 400},
    "いわき平": {"bank_angle": 32.9, "straight_length": 62.7, "bank_length": 400},
    "弥彦": {"bank_angle": 32.4, "straight_length": 63.1, "bank_length": 400},
    "前橋": {"bank_angle": 36.0, "straight_length": 46.7, "bank_length": 335},
    "取手": {"bank_angle": 31.5, "straight_length": 54.8, "bank_length": 400},
    "宇都宮": {"bank_angle": 25.8, "straight_length": 63.3, "bank_length": 500},
    "大宮": {"bank_angle": 26.3, "straight_length": 66.7, "bank_length": 500},
    "西武園": {"bank_angle": 29.4, "straight_length": 47.6, "bank_length": 400},
    "京王閣": {"bank_angle": 32.2, "straight_length": 51.5, "bank_length": 400},
    "立川": {"bank_angle": 31.2, "straight_length": 58.0, "bank_length": 400},
    "松戸": {"bank_angle": 29.8, "straight_length": 38.2, "bank_length": 333},
    "川崎": {"bank_angle": 32.2, "straight_length": 58.0, "bank_length": 400},
    "平塚": {"bank_angle": 31.5, "straight_length": 54.2, "bank_length": 400},
    "小田原": {"bank_angle": 35.6, "straight_length": 36.1, "bank_length": 333},
    "伊東": {"bank_angle": 34.7, "straight_length": 46.6, "bank_length": 333},
    "静岡": {"bank_angle": 30.7, "straight_length": 56.4, "bank_length": 400},
    "名古屋": {"bank_angle": 34.0, "straight_length": 58.8, "bank_length": 400},
    "岐阜": {"bank_angle": 32.3, "straight_length": 59.3, "bank_length": 400},
    "大垣": {"bank_angle": 30.6, "straight_length": 56.0, "bank_length": 400},
    "豊橋": {"bank_angle": 33.8, "straight_length": 60.3, "bank_length": 400},
    "富山": {"bank_angle": 33.7, "straight_length": 43.0, "bank_length": 333},
    "松坂": {"bank_angle": 34.4, "straight_length": 61.5, "bank_length": 400},
    "四日市": {"bank_angle": 32.3, "straight_length": 62.4, "bank_length": 400},
    "福井": {"bank_angle": 31.5, "straight_length": 52.8, "bank_length": 400},
    "奈良": {"bank_angle": 33.4, "straight_length": 38.0, "bank_length": 333},
    "向日町": {"bank_angle": 30.5, "straight_length": 47.3, "bank_length": 400},
    "和歌山": {"bank_angle": 32.3, "straight_length": 59.9, "bank_length": 400},
    "岸和田": {"bank_angle": 30.9, "straight_length": 56.7, "bank_length": 400},
    "玉野": {"bank_angle": 30.6, "straight_length": 47.9, "bank_length": 400},
    "広島": {"bank_angle": 30.8, "straight_length": 57.9, "bank_length": 400},
    "防府": {"bank_angle": 34.7, "straight_length": 42.5, "bank_length": 333},
    "高松": {"bank_angle": 33.3, "straight_length": 54.8, "bank_length": 400},
    "小松島": {"bank_angle": 29.8, "straight_length": 55.5, "bank_length": 400},
    "高知": {"bank_angle": 24.5, "straight_length": 52.0, "bank_length": 500},
    "松山": {"bank_angle": 34.0, "straight_length": 58.6, "bank_length": 400},
    "小倉": {"bank_angle": 34.0, "straight_length": 56.9, "bank_length": 400},
    "久留米": {"bank_angle": 31.5, "straight_length": 50.7, "bank_length": 400},
    "武雄": {"bank_angle": 32.0, "straight_length": 64.4, "bank_length": 400},
    "佐世保": {"bank_angle": 31.5, "straight_length": 40.2, "bank_length": 400},
    "別府": {"bank_angle": 33.7, "straight_length": 59.9, "bank_length": 400},
    "熊本": {"bank_angle": 34.3, "straight_length": 60.3, "bank_length": 400},
    "手入力": {"bank_angle": 30.0, "straight_length": 52.0, "bank_length": 400}
}


selected_track = st.selectbox("▼ 競輪場選択（自動入力）", list(keirin_data.keys()))
selected_info = keirin_data[selected_track]

# ▼ 風速入力（手動）
wind_speed = st.number_input("風速(m/s)", min_value=0.0, max_value=30.0, step=0.1, value=3.0)

# ▼ 自動反映される直線長さ・バンク角・周長
straight_length = st.number_input("みなし直線(m)", min_value=30.0, max_value=80.0, step=0.1,
                                  value=float(selected_info["straight_length"]))

bank_angle = st.number_input("バンク角(°)", min_value=20.0, max_value=45.0, step=0.1,
                             value=float(selected_info["bank_angle"]))

bank_length = st.number_input("バンク周長(m)", min_value=300.0, max_value=500.0, step=0.1,
                              value=float(selected_info["bank_length"]))


# ▼ 周回数の入力（通常は4、高松などは5）
laps = st.number_input("周回数（通常は4、高松などは5）", min_value=1, max_value=10, value=4, step=1)

# --- 【選手データ入力】 ---
st.header("【選手データ入力】")

st.subheader("▼ 位置入力（逃＝先頭・両＝番手・追＝３番手以降&単騎：車番を半角数字で入力）")

kakushitsu_keys = ['逃', '両', '追']
kakushitsu_inputs = {}
cols = st.columns(3)
for i, k in enumerate(kakushitsu_keys):
    with cols[i]:
        st.markdown(f"**{k}**")
        kakushitsu_inputs[k] = st.text_input("", key=f"kaku_{k}", max_chars=14)

# 車番 → 脚質の辞書を構築
car_to_kakushitsu = {}
for k, val in kakushitsu_inputs.items():
    for c in val:
        if c.isdigit():
            n = int(c)
            if 1 <= n <= 9:
                car_to_kakushitsu[n] = k

st.subheader("▼ 前々走・前走の着順入力（1〜9着 または 0＝落車）")

# 7選手 × 2走分
chaku_inputs = []  # [[前々走, 前走], ..., [前々走, 前走]]

for i in range(9):
    col1, col2 = st.columns(2)
    with col1:
        chaku1 = st.text_input(f"{i+1}番【前々走】", value="", key=f"chaku1_{i}")
    with col2:
        chaku2 = st.text_input(f"{i+1}番【前走】", value="", key=f"chaku2_{i}")
    chaku_inputs.append([chaku1, chaku2])



st.subheader("▼ 競争得点入力")
rating = [st.number_input(f"{i+1}番得点", value=55.0, step=0.1, key=f"rate_{i}") for i in range(9)]

st.subheader("▼ 予想隊列入力（数字、欠の場合は空欄）")
tairetsu = [st.text_input(f"{i+1}番隊列順位", key=f"tai_{i}") for i in range(9)]


# --- S・B 入力（回数を数値で入力） ---
st.subheader("▼ S・B 入力（各選手のS・B回数を入力）")

for i in range(9):
    st.markdown(f"**{i+1}番**")
    s_val = st.number_input("S回数", min_value=0, max_value=99, value=0, step=1, key=f"s_point_{i+1}")
    b_val = st.number_input("B回数", min_value=0, max_value=99, value=0, step=1, key=f"b_point_{i+1}")


# --- ライン構成入力（A〜Dライン＋単騎） ---
st.subheader("▼ ライン構成入力（A〜Dライン＋単騎）")
a_line = st.text_input("Aライン（例：13）", key="a_line", max_chars=9)
b_line = st.text_input("Bライン（例：25）", key="b_line", max_chars=9)
c_line = st.text_input("Cライン（例：47）", key="c_line", max_chars=9)
d_line = st.text_input("Dライン（例：68）", key="d_line", max_chars=9)
solo_line = st.text_input("単騎枠（例：9）", key="solo_line", max_chars=9)


# --- ライン構成入力に必要な補助関数 ---
def extract_car_list(input_str):
    return [int(c) for c in input_str if c.isdigit()]

def build_line_position_map():
    result = {}
    for line, name in zip([a_line, b_line, c_line, d_line, solo_line], ['A', 'B', 'C', 'D', 'S']):
        cars = extract_car_list(line)
        for i, car in enumerate(cars):
            if name == 'S':
                result[car] = 0
            else:
                result[car] = i + 1
    return result

# --- スコア計算ボタン表示 ---
st.subheader("▼ スコア計算")
if st.button("スコア計算実行"):

    def extract_car_list(input_str):
        return [int(c) for c in input_str if c.isdigit()]

    def score_from_tenscore_list(tenscore_list):
        import pandas as pd
    
        df = pd.DataFrame({"得点": tenscore_list})
        df["順位"] = df["得点"].rank(ascending=False, method="min").astype(int)
    
        # 基準点：2〜6位の平均
        baseline = df[df["順位"].between(2, 6)]["得点"].mean()
    
        # 2〜4位だけ補正（差分の3％、必ず正の加点）
        def apply_targeted_correction(row):
            if row["順位"] in [2, 3, 4]:
                correction = abs(baseline - row["得点"]) * 0.03
                return round(correction, 3)
            else:
                return 0.0
    
        df["最終補正値"] = df.apply(apply_targeted_correction, axis=1)
        return df["最終補正値"].tolist()

    def wind_straight_combo_adjust(kaku, direction, speed, straight, pos):
        if direction == "無風" or speed < 0.5:
            return 0
    
        base = wind_coefficients.get(direction, 0.0)  # e.g. 上=+0.10
        pos_mult = position_multipliers.get(pos, 0.0)  # e.g. 先頭=1.0, 番手=0.6
    
        # 強化された脚質補正係数（±1.0スケールに）
        kaku_coeff = {
            '逃': +1.0,
            '両':  0.5,
            '追': -1.0
        }.get(kaku, 0.0)
    
        total = base * speed * pos_mult * kaku_coeff  # 例: +0.1×10×1×1 = +1.0
        return round(total, 2)


    def convert_chaku_to_score(values):
        scores = []
        for i, v in enumerate(values):  # i=0: 前走, i=1: 前々走
            v = v.strip()
            try:
                chaku = int(v)
                if 1 <= chaku <= 9:
                    score = (10 - chaku) / 9
                    if i == 1:  # 前々走のみ補正
                        score *= 0.7
                    scores.append(score)
            except ValueError:
                continue
        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)



    def lap_adjust(kaku, laps):
        delta = max(laps - 4, 0)
        return {
            '逃': round(-0.2 * delta, 2),
            '追': round(+0.1 * delta, 2),
            '両': 0.0
        }.get(kaku, 0.0)

    def line_member_bonus(pos):
        return {
            0: 0.5,  # 単騎
            1: 0.5,  # 先頭（ライン1番手）
            2: 0.6,  # 2番手（番手）
            3: 0.4,  # 3番手（最後尾）
            4: 0.3   # 4番手（9車用：評価不要レベル）
        }.get(pos, 0.0)


    def bank_character_bonus(kaku, angle, straight):
        """
        カント角と直線長による脚質補正（スケール緩和済み）
        """
        straight_factor = (straight - 40.0) / 10.0
        angle_factor = (angle - 25.0) / 5.0
        total_factor = -0.2 * straight_factor + 0.2 * angle_factor
        return round({'逃': +total_factor, '追': -total_factor, '両': +0.5 * total_factor}.get(kaku, 0.0), 2)
        
    def bank_length_adjust(kaku, length):
        """
        バンク周長による補正（400基準を完全維持しつつ、±0.15に制限）
        """
        delta = (length - 411) / 100
        delta = max(min(delta, 0.075), -0.075)
        return round({'逃': 2.0 * delta, '両': 4.0 * delta, '追': 6.0 * delta}.get(kaku, 0.0), 2)

    def compute_group_bonus(score_parts, line_def):
        group_scores = {k: 0.0 for k in ['A', 'B', 'C', 'D']}
        group_counts = {k: 0 for k in ['A', 'B', 'C', 'D']}

            # 各ラインの合計スコアと人数を集計
        for entry in score_parts:
            car_no, score = entry[0], entry[-1]
            for group in ['A', 'B', 'C', 'D']:
                if car_no in line_def[group]:
                    group_scores[group] += score
                    group_counts[group] += 1
                    break
        # 合計スコアで順位を決定（平均ではない）
        sorted_lines = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)
    
        # 上位グループから順に 0.5 → 0.4 → 0.3→0.2 のボーナスを付与
        bonus_map = {group: [0.5, 0.4, 0.3, 0.2][idx] for idx, (group, _) in enumerate(sorted_lines)}
    
        return bonus_map


    def get_group_bonus(car_no, line_def, group_bonus_map):
        for group in ['A', 'B', 'C', 'D']:
            if car_no in line_def[group]:
                base_bonus = group_bonus_map.get(group, 0.0)
                s_bonus = 0.3 if group == 'A' else 0.0  # ← 無条件でAだけに+0.3
                return base_bonus + s_bonus
        if '単騎' in line_def and car_no in line_def['単騎']:
            return 0.3
        return 0.0

 # ライン構成取得
    line_def = {
        'A': extract_car_list(a_line),
        'B': extract_car_list(b_line),
        'C': extract_car_list(c_line),
        'D': extract_car_list(c_line),
        '単騎': extract_car_list(solo_line)  # tanki → solo_line に合わせて
        }

    line_order_map = build_line_position_map()
    line_order = [line_order_map.get(i + 1, 0) for i in range(9)]


    # スコア計算
    tenscore_score = score_from_tenscore_list(rating)
    score_parts = []

    for i in range(9):
        if not tairetsu[i].isdigit():
            continue

        num = i + 1
        kaku = car_to_kakushitsu.get(num, "追")
        base = base_score[kaku]

        wind = wind_straight_combo_adjust(
            kaku,
            st.session_state.selected_wind,
            wind_speed,
            straight_length,
            line_order[i]
        )

        chaku_values = chaku_inputs[i]
        kasai = convert_chaku_to_score(chaku_inputs[i]) or 0.0
        rating_score = tenscore_score[i]
        rain_corr = lap_adjust(kaku, laps)
        s_bonus = -0.01 * st.session_state.get(f"s_point_{num}", 0)
        b_bonus = 0.05 * st.session_state.get(f"b_point_{num}", 0)
        symbol_score = s_bonus + b_bonus
        line_bonus = line_member_bonus(line_order[i])
        bank_bonus = bank_character_bonus(kaku, bank_angle, straight_length)
        length_bonus = bank_length_adjust(kaku, bank_length)

        total = base + wind + kasai + rating_score + rain_corr + symbol_score + line_bonus + bank_bonus + length_bonus

        score_parts.append([
            num, kaku, base, wind, kasai, rating_score,
            rain_corr, symbol_score, line_bonus, bank_bonus, length_bonus, total
        ])


    # グループ補正
    group_bonus_map = compute_group_bonus(score_parts, line_def)
    final_score_parts = []
    for row in score_parts:
        group_corr = get_group_bonus(row[0], line_def, group_bonus_map)
        new_total = row[-1] + group_corr
        final_score_parts.append(row[:-1] + [group_corr, new_total])


    # 表示
    df = pd.DataFrame(final_score_parts, columns=[
        '車番', '脚質', '基本', '風補正', '着順補正', '得点補正',
        '周回補正', 'SB印補正', 'ライン補正', 'バンク補正', '周長補正',
        'グループ補正', '合計スコア'
    ])
    st.dataframe(df.sort_values(by='合計スコア', ascending=False).reset_index(drop=True))
    
try:
    if not final_score_parts:
        st.warning("スコアが計算されていません。入力や処理を確認してください。")
        st.stop()
except NameError:
    st.warning("スコアデータが定義されていません。入力に問題がある可能性があります。")
    st.stop()
    

from itertools import combinations
import pandas as pd
import streamlit as st

# --- B回数列の統一 ---
df.rename(columns={"バック": "B回数"}, inplace=True)
b_list = [st.session_state.get(f"b_point_{i+1}", 0) for i in range(len(df))]
if len(b_list) != len(df):
    st.error("⚠ B回数の数が選手数と一致していません")
    st.stop()
df["B回数"] = b_list

# --- ライン構成取得 ---
line_def_raw = {
    'A': extract_car_list(a_line),
    'B': extract_car_list(b_line),
    'C': extract_car_list(c_line),
    'D': extract_car_list(d_line),
    '単騎': extract_car_list(solo_line)
}

# 単騎が複数ある場合は個別化
line_def = {k: v for k, v in line_def_raw.items() if k != '単騎'}
solo_members = line_def_raw.get('単騎', [])
for i, solo_car in enumerate(solo_members):
    line_def[f'単騎{i+1}'] = [solo_car]

# --- ◎決定 ---
df_sorted = df.sort_values(by="合計スコア", ascending=False).reset_index(drop=True)
top_score = df_sorted.iloc[0]["合計スコア"]
df_top_range = df[df["合計スコア"] >= top_score - 0.5].copy()
df_top_range["構成評価"] = (
    df_top_range["着順補正"] * 0.8 +
    df_top_range["SB印補正"] * 1.2 +
    df_top_range["ライン補正"] * 0.4 +
    df_top_range["グループ補正"] * 0.2
)
anchor_row = df_top_range.sort_values(by="構成評価", ascending=False).iloc[0]
anchor = int(anchor_row["車番"])

# --- ライン分類 ---
def find_line(car_no):
    for k, v in line_def.items():
        if car_no in v:
            return k
    return None

main_line_key = find_line(anchor)
main_line = line_def.get(main_line_key, [])

# 潰しライン（スコア上位3から本命を除外）
score_top3 = df_sorted.iloc[:3].copy()
tsubushi_line_key = None
for i in range(1, 3):
    candidate = int(score_top3.iloc[i]["車番"])
    line_k = find_line(candidate)
    if line_k and line_k != main_line_key:
        tsubushi_line_key = line_k
        break

# 漁夫ライン
gyofu_keys = [k for k in line_def if k not in [main_line_key, tsubushi_line_key]]

a_line = main_line
b_line = line_def.get(tsubushi_line_key, [])
c_line = []
for k in gyofu_keys:
    c_line.extend(line_def[k])

# --- 三連複構成抽出 ---
a_others = [a for a in a_line if a != anchor]
kumi_awase = {"構成①": [], "構成②": [], "構成③": []}
selection_reason = {"構成①": [], "構成②": [], "構成③": []}

# 構成①：◎–A–C（本命＋漁夫）
if len(a_others) >= 1 and len(c_line) >= 1:
    a_df = df[df["車番"].isin(a_others)].copy()
    c_df = df[df["車番"].isin(c_line)].copy()
    for d in [a_df, c_df]:
        d["構成評価"] = (
            d["着順補正"] * 0.8 +
            d["SB印補正"] * 1.2 +
            d["ライン補正"] * 0.4 +
            d["グループ補正"] * 0.2
        )
    a_top2 = list(a_df.sort_values(by="構成評価", ascending=False)["車番"][:2])
    c_top2 = list(c_df.sort_values(by="構成評価", ascending=False)["車番"][:2])
    count = 0
    for a in a_top2:
        for c in c_top2:
            if count >= 2:
                break
            if a == c:
                continue
            kumi = tuple(sorted([anchor, a, c]))
            kumi_awase["構成①"].append(kumi)
            selection_reason["構成①"].append(f"◎({anchor})–A({a})–C({c})：本命＋漁夫構成")
            count += 1
        if count >= 2:
            break

# 構成②：Bスコア上位2車＋Aラインから1車
if len(b_line) >= 2 and len(a_line) >= 1:
    b_df = df[df["車番"].isin(b_line)].copy()
    b_df["構成評価"] = (
        b_df["着順補正"] * 0.8 +
        b_df["SB印補正"] * 1.2 +
        b_df["ライン補正"] * 0.4 +
        b_df["グループ補正"] * 0.2
    )
    b_top2 = list(b_df.sort_values(by="構成評価", ascending=False)["車番"][:2])
    a_df = df[df["車番"].isin(a_line)].copy()
    a_df["構成評価"] = (
        a_df["着順補正"] * 0.8 +
        a_df["SB印補正"] * 1.2 +
        a_df["ライン補正"] * 0.4 +
        a_df["グループ補正"] * 0.2
    )
    a_top2 = list(a_df.sort_values(by="構成評価", ascending=False)["車番"][:2])
    max_combinations_struct2 = 1 if len(b_line) <= 2 else 2
    count = 0
    for a in a_top2:
        kumi = tuple(sorted([b_top2[0], b_top2[1], a]))
        if kumi not in kumi_awase["構成①"] + kumi_awase["構成②"] + kumi_awase["構成③"]:
            kumi_awase["構成②"].append(kumi)
            selection_reason["構成②"].append(f"B({b_top2[0]},{b_top2[1]})–A({a}):潰れ残り保険")
            count += 1
        if count >= max_combinations_struct2:
            break

# 構成③：C–A–B（荒れ展開）→ 1点
if len(c_line) >= 1 and len(a_others) >= 1 and len(b_line) >= 1:
    c = c_line[0]
    a = a_others[0]
    b = b_line[0]
    kumi = tuple(sorted([c, a, b]))
    if kumi not in kumi_awase["構成①"] + kumi_awase["構成②"]:
        kumi_awase["構成③"].append(kumi)
        selection_reason["構成③"].append(f"C({c})–A({a})–B({b})：荒れ展開対応")

# --- 最終出力（構成順に並べる） ---
final_candidates = kumi_awase["構成①"] + kumi_awase["構成②"] + kumi_awase["構成③"]
selection_reason_flat = selection_reason["構成①"] + selection_reason["構成②"] + selection_reason["構成③"]

# ライン表示まとめ
st.markdown("### 🔹 ライン定義")
st.markdown(f"- 本命ライン（A）：{sorted(a_line)}")
st.markdown(f"- 対抗ライン（B）：{sorted(b_line)}")
st.markdown(f"- 漁夫の利ライン（C）：{sorted(c_line)}")

# 表示
st.markdown("### 🎯 フォーメーション構成")
for reason in selection_reason_flat:
    st.markdown(f"- {reason}")
for i, kumi in enumerate(final_candidates, 1):
    st.markdown(f"{i}. **{kumi[0]} - {kumi[1]} - {kumi[2]}**")


# --- B回数列の統一 ---
df.rename(columns={"バック": "B回数"}, inplace=True)
b_list = [st.session_state.get(f"b_point_{i+1}", 0) for i in range(len(df))]
if len(b_list) != len(df):
    st.error("⚠ B回数の数が選手数と一致していません")
    st.stop()
df["B回数"] = b_list

# --- ライン構成取得 ---
line_def_raw = {
    'A': extract_car_list(a_line),
    'B': extract_car_list(b_line),
    'C': extract_car_list(c_line),
    'D': extract_car_list(d_line),
    '単騎': extract_car_list(solo_line)
}

# 単騎が複数ある場合は分割して個別ライン扱いに変更
line_def = {k: v for k, v in line_def_raw.items() if k != '単騎'}
solo_members = line_def_raw.get('単騎', [])
for i, solo_car in enumerate(solo_members):
    line_def[f'単騎{i+1}'] = [solo_car]

# --- 合計スコアで並び替え ---
df_sorted = df.sort_values(by="合計スコア", ascending=False).reset_index(drop=True)
top_score = df_sorted.iloc[0]["合計スコア"]
df_top_range = df[df["合計スコア"] >= top_score - 0.5].copy()
df_top_range["構成評価"] = (
    df_top_range["着順補正"] * 0.8 +
    df_top_range["SB印補正"] * 1.2 +
    df_top_range["ライン補正"] * 0.4 +
    df_top_range["グループ補正"] * 0.2
)
anchor_row = df_top_range.sort_values(by="構成評価", ascending=False).iloc[0]
anchor_index = int(anchor_row["車番"])

# --- main_line 定義 ---
def find_line(car_no):
    for k, v in line_def.items():
        if car_no in v:
            return k
    return None

main_line_key = find_line(anchor_index)
main_line_cars = line_def.get(main_line_key, [])

# --- 潰しライン（スコア上位3から main_line を除いたライン） ---
score_top3 = df_sorted.iloc[:3].copy()
tsubushi_line_key = None
for i in range(1, 3):
    candidate = int(score_top3.iloc[i]["車番"])
    line_k = find_line(candidate)
    if line_k and line_k != main_line_key:
        tsubushi_line_key = line_k
        break

# --- フォーメーション構成選出 ---
selection_reason = [f"◎（起点）：{anchor_index}（構成評価上位）"]
final_candidates = [anchor_index]

if len(main_line_cars) >= 4:
    for car in main_line_cars:
        if car != anchor_index:
            final_candidates.append(car)
            selection_reason.append(f"メインライン：{car}")
        if len(final_candidates) >= 4:
            break
else:
    main_df = df[df["車番"].isin(main_line_cars) & (df["車番"] != anchor_index)].copy()
    main_df["構成評価"] = (
        main_df["着順補正"] * 0.8 +
        main_df["SB印補正"] * 1.2 +
        main_df["ライン補正"] * 0.4 +
        main_df["グループ補正"] * 0.2
    )
    for _, row in main_df.sort_values(by="構成評価", ascending=False).iterrows():
        picked = int(row["車番"])
        final_candidates.append(picked)
        selection_reason.append(f"メインライン：{picked}")
        if len(final_candidates) >= 4:
            break

    if len(final_candidates) < 4:
        gyofu_line_keys = [k for k in line_def.keys() if k not in [main_line_key, tsubushi_line_key]]
        gyofu_line_candidates = []
        for k in gyofu_line_keys:
            members = line_def[k]
            if not members:
                continue
            sub_df = df[df["車番"].isin(members)].copy()
            sub_df["構成評価"] = (
                sub_df["着順補正"] * 0.8 +
                sub_df["SB印補正"] * 1.2 +
                sub_df["ライン補正"] * 0.4 +
                sub_df["グループ補正"] * 0.2
            )
            if len(sub_df) >= 1:
                avg_score = sub_df["構成評価"].mean()
                gyofu_line_candidates.append((k, avg_score, sub_df))

        gyofu_line_candidates.sort(key=lambda x: x[1], reverse=True)
        if gyofu_line_candidates:
            best_gyofu_line = gyofu_line_candidates[0][2].sort_values(by="構成評価", ascending=False)
            for _, row in best_gyofu_line.iterrows():
                if len(final_candidates) >= 4:
                    break
                picked = int(row["車番"])
                if picked not in final_candidates:
                    final_candidates.append(picked)
                    selection_reason.append(f"漁夫の利ライン：{picked}")

# --- 最終出力（4車に制限） ---
final_candidates = final_candidates[:4]
selection_reason = selection_reason[:4]

# --- 表示関数で出力を統一 ---
def show_final_output(reasons, candidates):
    st.markdown("### 🎯 フォーメーション構成")
    for reason in reasons:
        st.markdown(f"- {reason}")
    st.markdown(f"👉 **三連複4点：BOX（{', '.join(map(str, candidates))}）**")

# 出力表示（1回だけ）
show_final_output(selection_reason, final_candidates)
