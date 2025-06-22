import streamlit as st
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="ライン競輪スコア計算（完全統一版）", layout="wide")

st.title("⭐ ライン競輪スコア計算（9車ライン＋欠番対応）⭐")

# --- 風向補正係数 ---
wind_coefficients = {
    "左上": -0.03,
    "上":   -0.05,
    "右上": -0.035,
    "左":   +0.05,
    "右":   -0.05,
    "左下": +0.035,
    "下":   +0.05,
    "右下": +0.035
}

# --- ライン順による影響倍率（先頭〜4番手、単騎） ---
position_multipliers = {
    0: 0.3,   # 単騎
    1: 0.32,  # 先頭
    2: 0.3,
    3: 0.25,
    4: 0.2
}

# --- 基本スコア（脚質ごとの基準値） ---
base_score = {'逃': 4.7, '両': 4.8, '追': 5.0}

# --- 状態保持 ---
if "selected_wind" not in st.session_state:
    st.session_state.selected_wind = "無風"

# --- 風＋ライン順に応じた補正スコア関数 ---
def wind_straight_combo_adjust(kakushitsu, wind_direction, wind_speed, straight_length, line_order):
    wind_adj = wind_coefficients.get(wind_direction, 0.0)
    pos_multi = position_multipliers.get(line_order, 0.3)

    if wind_direction == "無風" or wind_speed == 0:
        return 0.0

    if kakushitsu == "逃":
        return round(wind_speed * wind_adj * 1.0 * pos_multi, 3)
    elif kakushitsu == "両":
        return round(wind_speed * wind_adj * 0.7 * pos_multi, 3)
    elif kakushitsu == "追":
        return round(wind_speed * wind_adj * 0.4 * pos_multi, 3)
    return round(wind_speed * wind_adj * 0.5 * pos_multi, 3)

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
straight_length = st.number_input("みなし直線(m)", min_value=30.0, max_value=80.0, step=0.05,
                                  value=float(selected_info["straight_length"]))

bank_angle = st.number_input("バンク角(°)", min_value=20.0, max_value=45.0, step=0.05,
                             value=float(selected_info["bank_angle"]))

bank_length = st.number_input("バンク周長(m)", min_value=300.0, max_value=500.0, step=0.05,
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


# --- ライン構成入力（最大9ライン、単騎含む自由構成） ---
st.subheader("▼ ライン構成入力（最大9ライン：単騎も1ラインとして扱う）")

line_1 = st.text_input("ライン1（例：4）", key="line_1", max_chars=9)
line_2 = st.text_input("ライン2（例：12）", key="line_2", max_chars=9)
line_3 = st.text_input("ライン3（例：35）", key="line_3", max_chars=9)
line_4 = st.text_input("ライン4（例：7）", key="line_4", max_chars=9)
line_5 = st.text_input("ライン5（例：6）", key="line_5", max_chars=9)
line_6 = st.text_input("ライン6（任意）", key="line_6", max_chars=9)
line_7 = st.text_input("ライン7（任意）", key="line_7", max_chars=9)
line_8 = st.text_input("ライン8（任意）", key="line_8", max_chars=9)
line_9 = st.text_input("ライン9（任意）", key="line_9", max_chars=9)



# --- ライン構成入力に必要な補助関数 ---
def extract_car_list(input_data):
    if isinstance(input_data, str):
        return [int(c) for c in input_data if c.isdigit()]
    elif isinstance(input_data, list):
        return [int(c) for c in input_data if isinstance(c, (str, int)) and str(c).isdigit()]
    else:
        return []

def build_line_position_map():
    result = {}
    for line, name in zip([a_line, b_line, c_line, d_line, e_line, f_line, g_line, h_line, i_line], ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']):
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

    def extract_car_list(input_data):
        if isinstance(input_data, str):
            return [int(c) for c in input_data if c.isdigit()]
        elif isinstance(input_data, list):
            return [int(c) for c in input_data if isinstance(c, (str, int)) and str(c).isdigit()]
        else:
            return []

    def score_from_tenscore_list(tenscore_list):
        import pandas as pd
    
        df = pd.DataFrame({"得点": tenscore_list})
        df["順位"] = df["得点"].rank(ascending=False, method="min").astype(int)
    
        # 基準点：2〜8位の平均
        baseline = df[df["順位"].between(2, 8)]["得点"].mean()
    
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
    
        base = wind_coefficients.get(direction, 0.0)  # e.g. 上=+0.005
        pos_mult = position_multipliers.get(pos, 0.0)  # e.g. 先頭=0.5, 番手=0.3
    
        # 強化された脚質補正係数（±1.0スケールに）
        kaku_coeff = {
            '逃': +0.3,
            '両':  +0.15,
            '追': -0.3
        }.get(kaku, 0.0)
    
        total = base * speed * pos_mult * kaku_coeff  # 例: +0.1×10×1×1 = +1.0
        return round(total, 2)


    def convert_chaku_to_score(values):
        scores = []
        for i, v in enumerate(values):
            v = v.strip()
            try:
                chaku = int(v)
                if 1 <= chaku <= 9:
                    score = (10 - chaku) / 9
                    if i == 1:
                        score *= 0.35
                    scores.append(score)
            except ValueError:
                continue
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 2)





    def lap_adjust(kaku, laps):
        delta = max(laps - 2, 0)
        return {
            '逃': round(-0.1 * delta, 1),
            '追': round(+0.05 * delta, 1),
            '両': 0.0
        }.get(kaku, 0.0)

    def line_member_bonus(pos):
        return {
            0: 0.25,  # 単騎
            1: 0.25,  # 先頭（ライン1番手）
            2: 0.3,  # 2番手（番手）
            3: 0.3,  # 3番手（最後尾）
            4: 0.15   # 4番手（9車用：評価不要レベル）
        }.get(pos, 0.0)


    def bank_character_bonus(kaku, angle, straight):
        """
        カント角と直線長による脚質補正（スケール緩和済み）
        """
        straight_factor = (straight - 40.0) / 10.0
        angle_factor = (angle - 25.0) / 5.0
        total_factor = -0.1 * straight_factor + 0.1 * angle_factor
        return round({'逃': +total_factor, '追': -total_factor, '両': +0.25 * total_factor}.get(kaku, 0.0), 2)
        
    def bank_length_adjust(kaku, length):
        """
        バンク周長による補正（400基準を完全維持しつつ、±0.15に制限）
        """
        delta = (length - 411) / 100
        delta = max(min(delta, 0.075), -0.075)
        return round({'逃': 1.0 * delta, '両': 2.0 * delta, '追': 3.0 * delta}.get(kaku, 0.0), 2)

def compute_group_bonus(score_parts, line_def):
    group_scores = {k: 0.0 for k in line_def.keys()}
    group_counts = {k: 0 for k in line_def.keys()}

    # 各ラインの合計スコアと人数を集計
    for entry in score_parts:
        car_no, score = entry[0], entry[-1]
        for group in line_def:
            if car_no in line_def[group]:
                group_scores[group] += score
                group_counts[group] += 1
                break

    # 合計スコアで順位を決定（平均ではなく合計）
    sorted_lines = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)

    # 順位に応じてボーナス値を割当
    bonus_map = {
        group: [0.25, 0.2, 0.15, 0.1, 0.08, 0.05, 0.03, 0.02, 0.01][idx]
        for idx, (group, _) in enumerate(sorted_lines)
        if idx < 9
    }

    return bonus_map



    def get_group_bonus(car_no, line_def, group_bonus_map):
        for group in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:
            if car_no in line_def[group]:
                base_bonus = group_bonus_map.get(group, 0.0)
                s_bonus = 0.15 if group == 'A' else 0.0  # ← 無条件でAだけに+0.15
                return base_bonus + s_bonus
        if '単騎' in line_def and car_no in line_def['単騎']:
            return 0.2
        return 0.0

# --- ライン構成取得（最大7ライン。単騎含む。自由入力） ---
lines = []
for i in range(1, 10):
    input_value = st.session_state.get(f"line_{i}", "")
    if input_value.strip():
        lines.append(extract_car_list(input_value))

# --- 各車番のライン順を取得（1〜7番車） ---
def build_line_position_map(lines):
    line_order_map = {}
    for idx, line in enumerate(lines):
        for car in line:
            line_order_map[car] = idx + 1
    return line_order_map

line_order_map = build_line_position_map(lines)
line_order = [line_order_map.get(i + 1, 0) for i in range(9)]


# --- グループ補正関数（line_defに基づきボーナスマップを作成） ---
def compute_group_bonus(score_parts, line_def):
    group_scores = {k: 0.0 for k in line_def.keys()}
    group_counts = {k: 0 for k in line_def.keys()}

    for entry in score_parts:
        car_no, score = entry[0], entry[-1]
        for group in line_def:
            if car_no in line_def[group]:
                group_scores[group] += score
                group_counts[group] += 1
                break

    sorted_lines = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)
    bonus_values = [0.25, 0.2, 0.15, 0.1, 0.08, 0.05, 0.03, 0.02, 0.01]
    bonus_map = {
        group: bonus_values[idx] if idx < len(bonus_values) else 0.0
        for idx, (group, _) in enumerate(sorted_lines)
    }

    return bonus_map

# ✅ 追加：車番に対するグループ補正値の取得関数
def get_group_bonus(car_no, line_def, bonus_map):
    for group, members in line_def.items():
        if car_no in members:
            return bonus_map.get(group, 0.0)
    return 0.0

# ✅ 追加：競争得点補正値を返す関数
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

# --- スコア計算 ---
tenscore_score = score_from_tenscore_list(rating)
score_parts = []

for i in range(9):
    if not tairetsu[i].isdigit():
        continue

    num = i + 1
    kaku = car_to_kakushitsu.get(num, "追")  # 車番→脚質
    base = base_score.get(kaku, 0.0)         # 基本スコア取得

    wind = wind_straight_combo_adjust(
        kaku,
        st.session_state.selected_wind,
        wind_speed,
        straight_length,
        line_order[i]
    )

    chaku_values = chaku_inputs[i]
    kasai = convert_chaku_to_score(chaku_values) or 0.0
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


# --- グループ補正関数（line_defに基づきボーナスマップを作成） ---
def compute_group_bonus(score_parts, line_def):
    group_scores = {k: 0.0 for k in line_def.keys()}
    group_counts = {k: 0 for k in line_def.keys()}

    # 車番からグループを逆引き
    car_to_group = {}
    for group, members in line_def.items():
        for car in members:
            car_to_group[car] = group

    # 各グループの合計スコアを計算
    for entry in score_parts:
        car_no, score = entry[0], entry[-1]
        group = car_to_group.get(car_no)
        if group:
            group_scores[group] += score
            group_counts[group] += 1

    # 順位を決定（合計スコアベース）
    sorted_lines = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)
    bonus_values = [0.25, 0.2, 0.15, 0.1, 0.08, 0.05, 0.03, 0.02, 0.01]

    bonus_map = {
        group: bonus_values[idx] if idx < len(bonus_values) else 0.0
        for idx, (group, _) in enumerate(sorted_lines)
    }

    return bonus_map

# --- グループ補正スコアを取得 ---
def get_group_bonus(car_no, line_def, bonus_map):
    for group, members in line_def.items():
        if car_no in members:
            return bonus_map.get(group, 0.0)
    return 0.0  # 所属なし

# --- line_def 構築（空行除外） ---
labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
line_def = {}
for idx, line in enumerate(lines):
    if line:  # 空欄チェック
        line_def[labels[idx]] = line

# --- グループ補正マップ作成 ---
group_bonus_map = compute_group_bonus(score_parts, line_def)

# --- グループ補正を最終スコアに反映 ---
final_score_parts = []
for row in score_parts:
    group_corr = get_group_bonus(row[0], line_def, group_bonus_map)
    new_total = row[-1] + group_corr
    final_score_parts.append(row[:-1] + [group_corr, new_total])

# --- 表示用DataFrame ---
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
    

import pandas as pd
import streamlit as st

# --- B回数列の統一（バック → B回数）---
df.rename(columns={"バック": "B回数"}, inplace=True)

# --- ユーザー入力されたB回数（バック回数）をdfへ格納 ---
b_list = [st.session_state.get(f"b_point_{i+1}", 0) for i in range(len(df))]

# --- 再発防止のチェック ---
if len(b_list) != len(df):
    st.error(f"⚠ B回数の入力数と選手数が一致していません")
    st.stop()

# --- B回数をdfに格納 ---
df["B回数"] = b_list

# --- 競争得点（ratingリスト）と車番をDataFrameに変換（9車用） ---
score_df = pd.DataFrame({
    "車番": list(range(1, 10)),
    "得点": rating
})

# --- 得点順で2〜4位を抽出 ---
subset = score_df.sort_values(by="得点", ascending=False).iloc[1:4]
target_car_numbers = subset["車番"].tolist()

# --- 該当車番のスコア情報を抽出 ---
subset_scores = [row for row in final_score_parts if row[0] in target_car_numbers]

# --- スコア順で並べて中央（2番目）を◎に ---
subset_scores_sorted = sorted(subset_scores, key=lambda x: x[-1], reverse=True)
anchor_car = subset_scores_sorted[1][0]  # ◎決定

# --- ◎の所属ラインを本命ライン（A）として定義 ---
anchor_line_idx = next(i for i, line in enumerate(lines) if anchor_car in line)
line_roles = {i: "Z" for i in range(len(lines))}  # Z=非対象
line_roles[anchor_line_idx] = "A"

# --- 得点上位1〜4位を抽出（DataFrameとして残す） ---
top4_df = score_df.sort_values(by="得点", ascending=False).iloc[:4]

# --- ◎を除いた中で得点が最も高い選手を選出（対抗ラインB） ---
b_candidates = top4_df[top4_df["車番"] != anchor_car]
if not b_candidates.empty:
    top_b_car = b_candidates.iloc[0]["車番"]
    for i, line in enumerate(lines):
        if i == anchor_line_idx:
            continue
        if top_b_car in line:
            line_roles[i] = "B"
            break

# --- 漁夫ライン（C）：得点上位1〜4位に属し、AでもBでもないライン ---
top4_cars = set(top4_df["車番"])
for i, line in enumerate(lines):
    if line_roles[i] == "Z":
        if any(car in top4_cars for car in line):
            line_roles[i] = "C"

# --- 各役割ラインの車番抽出 ---
a_line = lines[anchor_line_idx]
b_cars = [car for idx, role in line_roles.items() if role == "B" for car in lines[idx]]
c_cars = [car for idx, role in line_roles.items() if role == "C" for car in lines[idx]]

# --- anchorライン内でスコア順ソート ---
anchor_score_sorted = sorted(
    [row for row in final_score_parts if row[0] in a_line],
    key=lambda x: x[-1],
    reverse=True
)
anchor_others = [row[0] for row in anchor_score_sorted if row[0] != anchor_car]

# --- パターン①（◎-◎ライン-漁夫）構成 ---
pattern_1 = [
    tuple(sorted([anchor_car, x, y]))
    for x in anchor_others
    for y in c_cars
    if len(set([anchor_car, x, y])) == 3
]

# --- パターン②（対抗-対抗-◎）構成 ---
b_only = [car for car in b_cars if car != anchor_car]
pattern_2 = [
    tuple(sorted([x, y, anchor_car]))
    for i, x in enumerate(b_only)
    for y in b_only[i+1:]
]

# --- 重複除去・ソート ---
pattern_1 = sorted(set(pattern_1))
pattern_2 = sorted(set(pattern_2))

# --- 表示 ---
st.markdown("### 🌟 フォーメーション構成")
st.markdown(f"◆ 本線ライン（◎が所属）: {anchor_car} in {a_line}")
st.markdown(f"◆ 対抗ライン: {b_cars} ／ 漁夫ライン: {c_cars}")

with st.expander("▶ パターン1：◎-◎ライン-漁夫", expanded=True):
    for p in pattern_1:
        st.write(f"三連複 {p}")

with st.expander("▶ パターン2：対抗-対抗-◎", expanded=True):
    for p in pattern_2:
        st.write(f"三連複 {p}")
