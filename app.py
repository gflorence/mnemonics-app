import streamlit as st
import random
import time
import json
from datetime import datetime
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

def add_session_to_history(sequence, answers, settings):
    history = load_history()
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "sequence": sequence,
        "answers": [a if a is not None else None for a in answers],
        "settings": settings,
    }
    history.append(entry)
    save_history(history)

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

# ---------- Helper functions ----------
def start_session(min_n, max_n, count, seconds):
    st.session_state.sequence = [random.randint(min_n, max_n) for _ in range(count)]
    st.session_state.answers = []
    st.session_state.current_index = 0
    st.session_state.seconds_per_number = seconds
    st.session_state.settings = {"min": min_n, "max": max_n, "count": count, "seconds": seconds}
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

# ---------- Sidebar navigation ----------
page = st.sidebar.radio("Navigate", ["Trainer", "Statistics"])

# ============================================================
# PAGE: TRAINER
# ============================================================
if page == "Trainer":

    # ---------- PHASE 1: SETTINGS ----------
    if st.session_state.phase == "settings":
        st.title("🧠 Mnemonics Trainer")
        st.write("Configure your training session:")

        col1, col2 = st.columns(2)
        with col1:
            min_n = st.number_input("Minimum number", min_value=0, max_value=9999, value=1)
        with col2:
            max_n = st.number_input("Maximum number", min_value=1, max_value=9999, value=99)

        count = st.number_input("How many numbers to memorize?", min_value=1, max_value=200, value=20)
        seconds = st.number_input("Seconds to display each number", min_value=1, max_value=60, value=5)

        if min_n >= max_n:
            st.error("Minimum must be less than Maximum.")
        else:
            if st.button("▶️ Start session", type="primary", use_container_width=True):
                start_session(int(min_n), int(max_n), int(count), int(seconds))
                st.rerun()

    # ---------- PHASE 2: MEMORIZATION ----------
    elif st.session_state.phase == "memorize":
        idx = st.session_state.current_index
        total = len(st.session_state.sequence)

        st.progress((idx + 1) / total, text=f"Number {idx + 1} of {total}")

        current_number = st.session_state.sequence[idx]
        st.markdown(
            f"<h1 style='text-align:center; font-size:150px; margin-top:50px;'>{current_number}</h1>",
            unsafe_allow_html=True,
        )

        time.sleep(st.session_state.seconds_per_number)
        st.session_state.current_index += 1
        if st.session_state.current_index >= total:
            go_to_recall()
        st.rerun()

    # ---------- PHASE 3: RECALL ----------
    elif st.session_state.phase == "recall":
        st.title("✍️ Recall phase")
        st.write("Type each number you remember. Leave blank and click **Skip** if you don't remember.")

        idx = st.session_state.current_index
        total = len(st.session_state.sequence)

        st.progress((idx) / total, text=f"Number {idx + 1} of {total}")

        user_input = st.text_input(
            f"Number {idx + 1}",
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
                    st.warning("Type a number or click Skip.")
                else:
                    try:
                        st.session_state.answers[idx] = int(user_input)
                        st.session_state.current_index += 1
                        if st.session_state.current_index >= total:
                            st.session_state.phase = "results"
                        st.rerun()
                    except ValueError:
                        st.error("Please enter a valid integer.")

    # ---------- PHASE 4: RESULTS ----------
    elif st.session_state.phase == "results":
        st.title("📊 Results")

        sequence = st.session_state.sequence
        answers = st.session_state.answers

        # Save to history once
        if not st.session_state.session_saved:
            add_session_to_history(sequence, answers, st.session_state.settings)
            st.session_state.session_saved = True

        correct = sum(1 for s, a in zip(sequence, answers) if a is not None and a == s)
        total = len(sequence)
        score_pct = (correct / total) * 100

        st.metric("Score", f"{correct} / {total}", f"{score_pct:.1f}%")

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
        # --- Overview ---
        st.subheader("Overview")
        total_sessions = len(history)

        # Build session summary dataframe
        rows = []
        for h in history:
            seq = h["sequence"]
            ans = h["answers"]
            total = len(seq)
            correct = sum(1 for s, a in zip(seq, ans) if a is not None and a == s)
            skipped = sum(1 for a in ans if a is None)
            wrong = total - correct - skipped
            rows.append({
                "timestamp": h["timestamp"],
                "count": total,
                "correct": correct,
                "wrong": wrong,
                "skipped": skipped,
                "score_%": round(correct / total * 100, 1),
                "range": f"{h['settings']['min']}–{h['settings']['max']}",
                "seconds": h["settings"]["seconds"],
            })
        df = pd.DataFrame(rows)

        col1, col2, col3 = st.columns(3)
        col1.metric("Sessions", total_sessions)
        col2.metric("Avg score", f"{df['score_%'].mean():.1f}%")
        col3.metric("Best score", f"{df['score_%'].max():.1f}%")

        # --- Progress chart ---
        st.subheader("Progress over time")
        chart_df = df[["timestamp", "score_%"]].copy()
        chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"])
        chart_df = chart_df.set_index("timestamp")
        st.line_chart(chart_df)

        # --- Session history table ---
        st.subheader("Session history")
        st.dataframe(df.iloc[::-1], use_container_width=True)  # most recent first

        # --- Weak numbers analysis ---
        st.subheader("🎯 Numbers you struggle with")
        st.caption("Numbers that were shown to you but you got wrong or skipped (across all sessions).")

        number_stats = {}  # number -> {"shown": n, "wrong_or_skipped": n}
        for h in history:
            for s, a in zip(h["sequence"], h["answers"]):
                if s not in number_stats:
                    number_stats[s] = {"shown": 0, "missed": 0}
                number_stats[s]["shown"] += 1
                if a is None or a != s:
                    number_stats[s]["missed"] += 1

        weak_rows = []
        for num, stats in number_stats.items():
            if stats["missed"] > 0:
                weak_rows.append({
                    "number": num,
                    "times_shown": stats["shown"],
                    "times_missed": stats["missed"],
                    "miss_rate_%": round(stats["missed"] / stats["shown"] * 100, 1),
                })
        if weak_rows:
            weak_df = pd.DataFrame(weak_rows).sort_values(
                by=["miss_rate_%", "times_missed"], ascending=False
            )
            st.dataframe(weak_df, use_container_width=True, hide_index=True)
        else:
            st.success("No weak numbers yet — great job!")

        # --- Confusion pairs ---
        st.subheader("🔀 Common confusions")
        st.caption("When a number was shown, which wrong answers did you give most often?")

        confusions = {}  # (shown, given) -> count
        for h in history:
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

        # --- Reset button ---
        st.divider()
        with st.expander("⚠️ Danger zone"):
            if st.button("Delete all statistics", type="secondary"):
                save_history([])
                st.success("All statistics deleted. Refresh the page.")
