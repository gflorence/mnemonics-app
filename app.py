import streamlit as st
import random
import time

# ---------- Page config ----------
st.set_page_config(page_title="Mnemonics Trainer", page_icon="🧠")

# ---------- Session state initialization ----------
# Session state keeps variables alive between reruns (Streamlit re-runs the whole script on each interaction)
if "phase" not in st.session_state:
    st.session_state.phase = "settings"  # settings -> memorize -> recall -> results
if "sequence" not in st.session_state:
    st.session_state.sequence = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# ---------- Helper functions ----------
def start_session(min_n, max_n, count, seconds):
    st.session_state.sequence = [random.randint(min_n, max_n) for _ in range(count)]
    st.session_state.answers = []
    st.session_state.current_index = 0
    st.session_state.seconds_per_number = seconds
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

    # Big number display
    current_number = st.session_state.sequence[idx]
    st.markdown(
        f"<h1 style='text-align:center; font-size:150px; margin-top:50px;'>{current_number}</h1>",
        unsafe_allow_html=True,
    )

    # Wait the configured seconds, then advance
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

    # Use a unique key per input so Streamlit doesn't mix them up
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
