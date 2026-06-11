import streamlit as st
import random
import time
import json
from datetime import datetime, date, timedelta
import pandas as pd
from streamlit_local_storage import LocalStorage

# ---------- Page config ----------
st.set_page_config(page_title="Mnemonics Trainer", page_icon="🧠")

# ---------- Local storage setup ----------
localS = LocalStorage()
STORAGE_KEY = "mnemonics_history"

def load_history():
    raw = localS.getItem(STORAGE_KEY)
    if raw is None or raw == "":
        return []
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []

def save_history(history):
    localS.setItem(STORAGE_KEY, json.dumps(history))

def add_session_to_history(sequence, answers, settings, mode):
    history = load_history()
    # Convert sequence/answers to strings for storage so all modes are uniform
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "sequence": [str(s) for s in sequence],
        "answers": [str(a) if a is not None else None for a in answers],
        "settings": settings,
    }
    history.append(entry)
    save_history(history)

# ---------- Streak calculation ----------
def compute_streak(history):
    if not history:
        return 0
    # Get unique training dates
    dates = set()
    for h in history:
        try:
            d = datetime.fromisoformat(h["timestamp"]).date()
            dates.add(d)
        except Exception:
            pass
    if not dates:
        return 0

    today = date.today()
    yesterday = today - timedelta(days=1)
    # Streak counts only if the user trained today or yesterday (still alive)
    if today not in dates and yesterday not in dates:
        return 0

    streak = 0
    current = today if today in dates else yesterday
    while current in dates:
        streak += 1
        current -= timedelta(days=1)
    return streak

# ---------- Item generation per mode ----------
CARD_SUITS = ["♠", "♥", "♦", "♣"]
CARD_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def build_card_deck(num_decks):
    deck = []
    for _ in range(num_decks):
        for suit in CARD_SUITS:
            for rank in CARD_RANKS:
                deck.append(f"{rank}{suit}")
    return deck

def generate_sequence(mode, count, settings):
    if mode == "Numbers":
        return [str(random.randint(settings["min"], settings["max"])) for _ in range(count)]
    elif mode == "Letters":
        case = settings.get("case", "Uppercase")
        if case == "Uppercase":
            pool = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        elif case == "Lowercase":
            pool = [chr(c) for c in range(ord("a"), ord("z") + 1)]
        else:  # Both
            pool = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + \
                   [chr(c) for c in range(ord("a"), ord("z") + 1)]
        return [random.choice(pool) for _ in range(count)]
    elif mode == "Cards":
        num_decks = settings.get("num_decks", 1)
        deck = build_card_deck(num_decks)
        if settings.get("with_replacement", False):
            return [random.choice(deck) for _ in range(count)]
        else:
            random.shuffle(deck)
            return deck[:count]
    return []

def normalize_answer(mode, raw):
    """Convert user input to canonical string for comparison."""
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None

    if mode == "Numbers":
        try:
            return str(int(raw))
        except ValueError:
            return raw  # will fail comparison → counts as wrong
    elif mode == "Letters":
        return raw  # case-sensitive comparison
    elif mode == "Cards":
        # Accept formats like "AS", "A S", "as", "10H", "10h", "A♠"
        s = raw.upper().replace(" ", "")
        # Replace suit letters with symbols
        suit_map = {"S": "♠", "H": "♥", "D": "♦", "C": "♣",
                    "♠": "♠", "♥": "♥", "♦": "♦", "♣": "♣"}
        if len(s) < 2:
            return raw
        # Last char is suit, rest is rank
        suit_char = s[-1]
        rank_part = s[:-1]
        suit = suit_map.get(suit_char, suit_char)
        # Validate rank
        if rank_part in CARD_RANKS:
            return f"{rank_part}{suit}"
        return raw
    return raw

# ---------- Session state initialization ----------
if "phase" not in st.session_state:
    st.session_state.phase = "settings"
if "sequence" not in st.session_state:
    st.session_state.sequence = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "session_saved" not in st.session_state:
    st.session_state.session_saved = False

# ---------- Helpers ----------
def start_session(mode, count, seconds, settings):
    st.session_state.mode = mode
    st.session_state.sequence = generate_sequence(mode, count, settings)
    st.session_state.answers = []
    st.session_state.current_index = 0
    st.session_state.seconds_per_item = seconds
    st.session_state.settings = settings
    st.session_state.session_saved = False
    st.session_state.phase = "memorize"

def go_to_recall():
    st.session_state.current_index = 0
    st.session_state.answers = [None] * len(st.session_state.sequence)
    st.session_state.phase = "recall"

def reset_to_settings():
    st.session_state.phase = "settings"
    st.session_state.sequence = []
    st.session_state.answers = []
    st.session_state.current_index = 0
    st.session_state.session_saved = False

# ---------- Sidebar ----------
page = st.sidebar.radio("Navigate", ["Trainer", "Statistics"])

# Streak display in sidebar
streak = compute_streak(load_history())
if streak > 0:
    st.sidebar.markdown(f"### 🔥 Streak: **{streak}** day{'s' if streak > 1 else ''}")
else:
    st.sidebar.markdown("### 🔥 Streak: 0 days")
    st.sidebar.caption("Train today to start a streak!")

# ============================================================
# PAGE: TRAINER
# ============================================================
if page == "Trainer":

    # ---------- PHASE 1: SETTINGS ----------
    if st.session_state.phase == "settings":
        st.title("🧠 Mnemonics Trainer")

        mode = st.selectbox("Training mode", ["Numbers", "Letters", "Cards"])

        settings = {}

        if mode == "Numbers":
            col1, col2 = st.columns(2)
            with col1:
                settings["min"] = int(st.number_input("Minimum", min_value=0, max_value=9999, value=1))
            with col2:
                settings["max"] = int(st.number_input("Maximum", min_value=1, max_value=9999, value=99))
            valid_range = settings["min"] < settings["max"]
            if not valid_range:
                st.error("Minimum must be less than Maximum.")
        elif mode == "Letters":
            settings["case"] = st.radio("Letter case", ["Uppercase", "Lowercase", "Both"], horizontal=True)
            valid_range = True
        elif mode == "Cards":
            settings["num_decks"] = int(st.number_input("Number of decks", min_value=1, max_value=10, value=1))
            settings["with_replacement"] = st.checkbox(
                "Allow same card to repeat",
                value=False,
                help="If unchecked, cards in the sequence will be unique (limited by deck size)."
            )
            valid_range = True

        # Max count depends on mode
        if mode == "Cards" and not settings.get("with_replacement", False):
            max_count = 52 * settings.get("num_decks", 1)
        else:
            max_count = 200
        default_count = min(20, max_count)

        count = int(st.number_input(
            f"How many items to memorize? (max {max_count})",
            min_value=1, max_value=max_count, value=default_count
        ))
        seconds = int(st.number_input("Seconds to display each item", min_value=1, max_value=60, value=5))

        if valid_range:
            if st.button("▶️ Start session", type="primary", use_container_width=True):
                start_session(mode, count, seconds, settings)
                st.rerun()

    # ---------- PHASE 2: MEMORIZATION (with fade) ----------
    elif st.session_state.phase == "memorize":
        idx = st.session_state.current_index
        total = len(st.session_state.sequence)
        seconds = st.session_state.seconds_per_item

        st.progress((idx + 1) / total, text=f"Item {idx + 1} of {total}")

        current_item = st.session_state.sequence[idx]

        # Color suits red for hearts/diamonds
        color = "white"
        if isinstance(current_item, str) and (current_item.endswith("♥") or current_item.endswith("♦")):
            color = "#ff4b4b"

        # Unique class + keyframe name per index → forces fresh animation each time
        anim_name = f"fadeOut_{idx}"
        class_name = f"fading-item-{idx}"

        fade_html = f"""
        <style>
        @keyframes {anim_name} {{
            0%   {{ opacity: 1; }}
            70%  {{ opacity: 1; }}
            100% {{ opacity: 0; }}
        }}
        .{class_name} {{
            text-align: center;
            font-size: 150px;
            margin-top: 50px;
            color: {color};
            opacity: 1;
            animation: {anim_name} {seconds}s ease-in forwards;
        }}
        </style>
        <div class="{class_name}">{current_item}</div>
        """
        st.markdown(fade_html, unsafe_allow_html=True)

        time.sleep(seconds)
        st.session_state.current_index += 1
        if st.session_state.current_index >= total:
            go_to_recall()
        st.rerun()
        
    # ---------- PHASE 3: RECALL ----------
    elif st.session_state.phase == "recall":
        st.title("✍️ Recall phase")

        mode = st.session_state.mode
        if mode == "Cards":
            st.write("Type each card you remember (e.g. `AS`, `10H`, `KD`, `7C`). Use S/H/D/C for suits.")
        elif mode == "Letters":
            st.write("Type each letter you remember. **Case-sensitive** if you chose Both.")
        else:
            st.write("Type each number you remember.")
        st.caption("Leave blank and click **Skip** if you don't remember.")

        idx = st.session_state.current_index
        total = len(st.session_state.sequence)

        st.progress((idx) / total, text=f"Item {idx + 1} of {total}")

        user_input = st.text_input(
            f"Item {idx + 1}",
            key=f"answer_{idx}",
            placeholder="Type here...",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Skip", use_container_width=True):
                st.session_state.answers[idx] = None
                st.session_state.current_index += 1
                if st.session_state.current_index >= total:
                    st.session_state.phase = "results"
                st.rerun()
        with col2:
            if st.button("Submit ➡️", type="primary", use_container_width=True):
                if user_input.strip() == "":
                    st.warning("Type something or click Skip.")
                else:
                    normalized = normalize_answer(mode, user_input)
                    st.session_state.answers[idx] = normalized
                    st.session_state.current_index += 1
                    if st.session_state.current_index >= total:
                        st.session_state.phase = "results"
                    st.rerun()

    # ---------- PHASE 4: RESULTS ----------
    elif st.session_state.phase == "results":
        st.title("📊 Results")

        sequence = st.session_state.sequence
        answers = st.session_state.answers
        mode = st.session_state.mode

        if not st.session_state.session_saved:
            add_session_to_history(sequence, answers, st.session_state.settings, mode)
            st.session_state.session_saved = True

        correct = sum(1 for s, a in zip(sequence, answers) if a is not None and a == s)
        total = len(sequence)
        score_pct = (correct / total) * 100

        st.metric("Score", f"{correct} / {total}", f"{score_pct:.1f}%")

        # Streak feedback
        new_streak = compute_streak(load_history())
        if new_streak > 1:
            st.success(f"🔥 You're on a **{new_streak}-day streak**! Keep it up.")
        elif new_streak == 1:
            st.success("🔥 Streak started! Come back tomorrow to keep it alive.")

        st.subheader("Detail")
        for i, (shown, given) in enumerate(zip(sequence, answers)):
            if given is None:
                st.write(f"**{i+1}.** Shown: `{shown}` — ⏭️ Skipped")
            elif given == shown:
                st.write(f"**{i+1}.** Shown: `{shown}` — ✅ You said: `{given}`")
            else:
                st.write(f"**{i+1}.** Shown: `{shown}` — ❌ You said: `{given}`")

        st.divider()
        if st.button("🔄 New session", type="primary", use_container_width=True):
            reset_to_settings()
            st.rerun()

# ============================================================
# PAGE: STATISTICS
# ============================================================
elif page == "Statistics":
    st.title("📈 Statistics")

    history = load_history()

    if not history:
        st.info("No sessions recorded yet. Complete a training session to see stats here.")
    else:
        # --- Streak ---
        st.subheader("🔥 Streak")
        st.metric("Consecutive training days", compute_streak(history))

        # Mode filter
        all_modes = sorted(set(h.get("mode", "Numbers") for h in history))
        selected_modes = st.multiselect("Filter by mode", all_modes, default=all_modes)
        filtered = [h for h in history if h.get("mode", "Numbers") in selected_modes]

        if not filtered:
            st.warning("No sessions for selected modes.")
        else:
            # --- Overview ---
            st.subheader("Overview")
            rows = []
            for h in filtered:
                seq = h["sequence"]
                ans = h["answers"]
                total = len(seq)
                correct = sum(1 for s, a in zip(seq, ans) if a is not None and a == s)
                skipped = sum(1 for a in ans if a is None)
                wrong = total - correct - skipped
                rows.append({
                    "timestamp": h["timestamp"],
                    "mode": h.get("mode", "Numbers"),
                    "count": total,
                    "correct": correct,
                    "wrong": wrong,
                    "skipped": skipped,
                    "score_%": round(correct / total * 100, 1),
                })
            df = pd.DataFrame(rows)

            col1, col2, col3 = st.columns(3)
            col1.metric("Sessions", len(filtered))
            col2.metric("Avg score", f"{df['score_%'].mean():.1f}%")
            col3.metric("Best score", f"{df['score_%'].max():.1f}%")

            # --- Progress chart ---
            st.subheader("Progress over time")
            chart_df = df[["timestamp", "score_%"]].copy()
            chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"])
            chart_df = chart_df.set_index("timestamp")
            st.line_chart(chart_df)

            # --- Session history ---
            st.subheader("Session history")
            st.dataframe(df.iloc[::-1], use_container_width=True)

            # --- Weak items ---
            st.subheader("🎯 Items you struggle with")
            item_stats = {}
            for h in filtered:
                for s, a in zip(h["sequence"], h["answers"]):
                    if s not in item_stats:
                        item_stats[s] = {"shown": 0, "missed": 0}
                    item_stats[s]["shown"] += 1
                    if a is None or a != s:
                        item_stats[s]["missed"] += 1

            weak_rows = [
                {
                    "item": k,
                    "times_shown": v["shown"],
                    "times_missed": v["missed"],
                    "miss_rate_%": round(v["missed"] / v["shown"] * 100, 1),
                }
                for k, v in item_stats.items() if v["missed"] > 0
            ]
            if weak_rows:
                weak_df = pd.DataFrame(weak_rows).sort_values(
                    by=["miss_rate_%", "times_missed"], ascending=False
                )
                st.dataframe(weak_df, use_container_width=True, hide_index=True)
            else:
                st.success("No weak items yet — great job!")

            # --- Confusions ---
            st.subheader("🔀 Common confusions")
            confusions = {}
            for h in filtered:
                for s, a in zip(h["sequence"], h["answers"]):
                    if a is not None and a != s:
                        key = (s, a)
                        confusions[key] = confusions.get(key, 0) + 1

            if confusions:
                conf_rows = [
                    {"shown": k[0], "you_typed": k[1], "times": v}
                    for k, v in confusions.items()
                ]
                conf_df = pd.DataFrame(conf_rows).sort_values(by="times", ascending=False)
                st.dataframe(conf_df, use_container_width=True, hide_index=True)
            else:
                st.info("No confusion patterns detected yet.")

        # --- Reset ---
        st.divider()
        with st.expander("⚠️ Danger zone"):
            if st.button("Delete all statistics", type="secondary"):
                save_history([])
                st.success("All statistics deleted. Refresh the page.")
