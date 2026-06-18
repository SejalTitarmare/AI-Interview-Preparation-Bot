# Add this at the TOP of pages/q_app.py, before any imports:
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Now this import works:
from quiz_mode import (
    pick_10_questions,
    score_answer,
    get_feedback,
    save_score,
    get_final_report
)

st_html = st.components.v1.html

st.set_page_config(
    page_title="Quiz Mode — AI Interview Bot",
    page_icon="🏆",
    layout="wide"
)

# Hide deploy button
st.markdown("""
<style>
    .stDeployButton { display: none !important; }
    footer { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────
defaults = {
    "quiz_started":      False,
    "questions":         [],
    "current_q":         0,
    "scores":            [],
    "feedbacks":         [],
    "quiz_done":         False,
    "answer_submitted":  False,
    "current_answer":    "",
    "pending_speech":    "",
    "auto_speak":        True,
    "answer_mode":       "type",
    "recognized_answer": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Read speech from URL params ───────────────────
qp = st.query_params
if "answer" in qp and qp["answer"].strip():
    st.session_state.recognized_answer = qp["answer"].strip()
    st.query_params.clear()

# ── Sidebar ───────────────────────────────────────
with st.sidebar:
    st.title("🏆 Quiz Mode")
    st.divider()

    st.subheader("🎤 Answer Mode")
    answer_mode = st.radio(
        "How do you want to answer?",
        ["⌨️ Type", "🎤 Speak"],
        index=0
    )
    st.session_state.answer_mode = (
        "speak" if "Speak" in answer_mode else "type"
    )

    st.divider()
    st.subheader("🔊 Bot Voice")
    auto_speak = st.toggle("Bot reads questions aloud", value=True)
    st.session_state.auto_speak = auto_speak
    if auto_speak:
        st.success("🔊 Voice ON")
    else:
        st.info("🔇 Voice OFF")

    st.divider()

    # Progress bar
    if st.session_state.quiz_started and not st.session_state.quiz_done:
        current = st.session_state.current_q
        st.subheader("📊 Progress")
        st.progress(current / 10)
        st.write(f"Question {current + 1} of 10")

        # Running scores
        if st.session_state.scores:
            avg = sum(st.session_state.scores) / len(st.session_state.scores)
            st.metric("Average Score", f"{avg:.1f}/10")

    st.divider()

    # Restart button
    if st.session_state.quiz_started:
        if st.button("🔄 Restart Quiz", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()

# ── Main ──────────────────────────────────────────
st.title("🏆 AI Interview Quiz Mode")
st.caption("Test your knowledge — 10 questions covering all topics")

st.divider()

# ════════════════════════════════════════════════
# START SCREEN
# ════════════════════════════════════════════════
if not st.session_state.quiz_started:
    st.markdown("""
    ## 📋 How Quiz Mode Works

    1. 🎲 Bot picks **10 random questions** covering all 6 topics
    2. 🔊 Bot **reads each question aloud** + shows it as text
    3. ✍️ You **answer by typing or speaking**
    4. 🤖 Bot **scores your answer** using AI (cosine similarity)
    5. 📝 Bot shows **what you missed** with detailed feedback
    6. 📊 Final report shows your **strong and weak topics**

    ### 📚 Topics covered:
    """)

    cols = st.columns(3)
    topics = [
        ("🧠", "Machine Learning"),
        ("🔬", "Deep Learning"),
        ("💬", "NLP"),
        ("📊", "Statistics"),
        ("🐍", "Python & SQL"),
        ("🏗️", "System Design")
    ]
    for i, (icon, topic) in enumerate(topics):
        with cols[i % 3]:
            st.info(f"{icon} {topic}")

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🚀 Start Quiz",
            type="primary",
            use_container_width=True
        ):
            with st.spinner("🎲 Picking 10 questions..."):
                st.session_state.questions = pick_10_questions()
            st.session_state.quiz_started = True
            st.session_state.current_q = 0
            st.rerun()

# ════════════════════════════════════════════════
# QUIZ IN PROGRESS
# ════════════════════════════════════════════════
elif st.session_state.quiz_started and not st.session_state.quiz_done:

    current_idx = st.session_state.current_q
    question_data = st.session_state.questions[current_idx]

    # ── Question display ──────────────────────────
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 2px solid #667eea;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;">
        <h3 style="color:#667eea; margin:0 0 10px 0;">
            Question {current_idx + 1} of 10
            <span style="font-size:14px; color:#888; margin-left:10px;">
                [{question_data['topic']} — {question_data['difficulty']}]
            </span>
        </h3>
        <h2 style="margin:0; color: var(--text-color, #333);">
            {question_data['question']}
        </h2>
    </div>
    """, unsafe_allow_html=True)

    # ── Auto speak question ───────────────────────
    if (st.session_state.auto_speak and
            not st.session_state.answer_submitted):
        q_text = question_data['question'].replace(
            '"', "'"
        ).replace('`', '')
        intro = f"Question {current_idx + 1}. {q_text}"
        st_html(f"""
        <script>
        setTimeout(function() {{
            window.speechSynthesis.cancel();
            var u = new SpeechSynthesisUtterance(`{intro}`);
            u.lang='en-US'; u.rate=0.85; u.pitch=1.0;
            window.speechSynthesis.speak(u);
        }}, 300);
        </script>
        """, height=0)

    # ── Previous scores display ───────────────────
    if st.session_state.scores:
        cols = st.columns(len(st.session_state.scores))
        for i, s in enumerate(st.session_state.scores):
            color = "#28a745" if s >= 6 else "#dc3545"
            cols[i].markdown(
                f"<div style='text-align:center; color:{color};"
                f"font-weight:bold; font-size:13px;'>Q{i+1}<br>{s}/10</div>",
                unsafe_allow_html=True
            )
        st.divider()

    # ── Answer section ────────────────────────────
    if not st.session_state.answer_submitted:

        st.subheader("✍️ Your Answer")

        # ── SPEECH ANSWER MODE ────────────────────
        if st.session_state.answer_mode == "speak":
            st.info("🎤 Click mic → speak your answer → click Use This Answer")

            speech_html = """
            <div style="font-family:Arial; padding:10px; text-align:center;">
                <button id="mic-btn" onclick="toggleMic()" style="
                    background:#ff4b4b; color:white; border:none;
                    padding:12px 24px; border-radius:50px;
                    font-size:16px; cursor:pointer; width:200px; margin:6px;">
                    🎤 Start Speaking
                </button>

                <div id="status" style="
                    background:#f0f2f6; border-radius:8px;
                    padding:10px; font-size:14px; color:#555;
                    margin:8px auto; max-width:500px;">
                    Click mic and speak your answer
                </div>

                <div id="transcript" style="
                    background:white; border:2px solid #ddd;
                    border-radius:10px; padding:12px;
                    font-size:15px; color:#333;
                    min-height:80px; max-width:560px;
                    margin:8px auto; text-align:left;
                    white-space:pre-wrap;">
                    (nothing heard yet)
                </div>

                <button onclick="useAnswer()" style="
                    background:#28a745; color:white; border:none;
                    padding:12px 24px; border-radius:50px;
                    font-size:16px; cursor:pointer;
                    width:200px; margin:6px;">
                    ✅ Use This Answer
                </button>
            </div>

            <script>
            var recog = null, listening = false, finalText = '';

            function toggleMic() {
                listening ? stopMic() : startMic();
            }

            function startMic() {
                var API = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!API) {
                    setStatus('❌ Use Chrome!', '#c62828', '#ffebee'); return;
                }
                recog = new API();
                recog.lang = 'en-US';
                recog.continuous = true;
                recog.interimResults = true;
                finalText = ''; listening = true;

                document.getElementById('mic-btn').style.background = '#cc0000';
                document.getElementById('mic-btn').innerText = '🔴 Stop';
                document.getElementById('transcript').innerText = '...';
                setStatus('🔴 Listening — speak your answer...', '#c62828', '#ffebee');

                recog.onresult = function(e) {
                    finalText = '';
                    var interim = '';
                    for (var i = 0; i < e.results.length; i++) {
                        if (e.results[i].isFinal) finalText += e.results[i][0].transcript + ' ';
                        else interim += e.results[i][0].transcript;
                    }
                    document.getElementById('transcript').innerText =
                        (finalText + interim).trim();
                };

                recog.onerror = function(e) {
                    listening = false; resetMic();
                    setStatus('❌ Error: ' + e.error, '#c62828', '#ffebee');
                };

                recog.onend = function() {
                    listening = false; resetMic();
                    if (finalText.trim())
                        setStatus('✅ Done! Click "Use This Answer"', '#1b5e20', '#e8f5e9');
                };

                recog.start();
            }

            function stopMic() {
                if (recog) recog.stop();
                listening = false; resetMic();
            }

            function resetMic() {
                document.getElementById('mic-btn').style.background = '#ff4b4b';
                document.getElementById('mic-btn').innerText = '🎤 Start Speaking';
            }

            function setStatus(msg, color, bg) {
                var b = document.getElementById('status');
                b.innerText = msg; b.style.color = color; b.style.background = bg;
            }

            function useAnswer() {
                var text = finalText.trim() ||
                    document.getElementById('transcript').innerText.trim();
                if (!text || text === '(nothing heard yet)' || text.length < 2) {
                    setStatus('❌ Speak first!', '#c62828', '#ffebee'); return;
                }
                setStatus('📤 Sending answer...', '#0d47a1', '#e3f2fd');
                var encoded = encodeURIComponent(text);
                window.parent.location.href =
                    window.parent.location.pathname + '?answer=' + encoded;
            }
            </script>
            """
            st_html(speech_html, height=300)

            st.markdown("**✏️ Your answer (edit if needed):**")
            user_answer = st.text_area(
                "answer",
                value=st.session_state.recognized_answer,
                height=120,
                placeholder="Speak above → click Use This Answer → appears here. Or type directly.",
                label_visibility="collapsed",
                key="speech_answer_area"
            )

        # ── TYPE ANSWER MODE ──────────────────────
        else:
            user_answer = st.text_area(
                "Type your answer here:",
                height=150,
                placeholder="Type your answer here... Be as detailed as you can!",
                key="type_answer_area"
            )

        st.divider()

        col1, col2 = st.columns([3, 1])
        with col1:
            submit = st.button(
                "📝 Submit Answer",
                type="primary",
                use_container_width=True
            )
        with col2:
            skip = st.button(
                "⏭️ Skip",
                use_container_width=True
            )

        # ── PROCESS SUBMITTED ANSWER ──────────────
        if submit or skip:
            if skip:
                user_answer = ""

            if not user_answer.strip() and not skip:
                st.warning("⚠️ Please write or speak your answer first!")
            else:
                with st.spinner("🤖 Scoring your answer..."):
                    score = score_answer(
                        user_answer,
                        question_data["answer"]
                    ) if user_answer.strip() else 0.0

                    feedback = get_feedback(
                        question_data["question"],
                        user_answer if user_answer.strip() else "(skipped)",
                        question_data["answer"],
                        score
                    )

                # Save score
                save_score(
                    question_data["topic"],
                    question_data["question"],
                    score
                )

                st.session_state.scores.append(score)
                st.session_state.feedbacks.append(feedback)
                st.session_state.current_answer = user_answer
                st.session_state.recognized_answer = ""
                st.session_state.answer_submitted = True
                st.session_state.pending_speech = feedback
                st.rerun()

    # ── FEEDBACK DISPLAY ──────────────────────────
    else:
        score = st.session_state.scores[-1]
        feedback = st.session_state.feedbacks[-1]

        # Score badge
        color = "#28a745" if score >= 7 else "#ffc107" if score >= 5 else "#dc3545"
        emoji = "🌟" if score >= 7 else "👍" if score >= 5 else "📚"

        st.markdown(f"""
        <div style="
            background:{color}22;
            border:2px solid {color};
            border-radius:15px;
            padding:20px;
            text-align:center;
            margin-bottom:20px;">
            <h1 style="color:{color}; margin:0;">
                {emoji} {score}/10
            </h1>
            <p style="color:{color}; margin:5px 0 0 0; font-size:18px;">
                {'Excellent!' if score>=7 else 'Good effort!' if score>=5 else 'Keep practicing!'}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Your answer
        if st.session_state.current_answer:
            with st.expander("👤 Your Answer", expanded=False):
                st.write(st.session_state.current_answer)

        # Feedback
        st.markdown("### 📝 Feedback")
        st.markdown(feedback)

        # Speak feedback button
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔊 Hear Feedback", key="speak_feedback"):
                clean = feedback.replace(
                    '"', "'"
                ).replace('\n', ' ').replace('`', '')[:2000]
                st_html(f"""
                <script>
                window.speechSynthesis.cancel();
                var u = new SpeechSynthesisUtterance(`{clean}`);
                u.lang='en-US'; u.rate=0.85;
                window.speechSynthesis.speak(u);
                </script>""", height=0)
        with c2:
            if st.button("⏹️ Stop", key="stop_feedback"):
                st_html(
                    "<script>window.speechSynthesis.cancel();</script>",
                    height=0
                )

        st.divider()

        # Next question button
        is_last = (current_idx >= 9)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            btn_label = "🏁 See Final Results" if is_last else f"➡️ Next Question ({current_idx + 2}/10)"
            if st.button(btn_label, type="primary", use_container_width=True):
                if is_last:
                    st.session_state.quiz_done = True
                else:
                    st.session_state.current_q += 1
                    st.session_state.answer_submitted = False
                    st.session_state.current_answer = ""
                    st.session_state.recognized_answer = ""
                st.rerun()

    # ── Auto speak feedback ───────────────────────
    if st.session_state.pending_speech and st.session_state.auto_speak:
        text = st.session_state.pending_speech
        clean = text.replace('"', "'").replace('\n', ' ').replace('`', '')[:2000]
        st.session_state.pending_speech = ""
        st_html(f"""
        <div style="background:#e8f5e9; padding:8px;
            border-radius:8px; font-size:13px; margin:5px 0;">
            🔊 <b>Speaking feedback...</b>
            <button onclick="window.speechSynthesis.cancel()" style="
                margin-left:8px; background:#ff4b4b; color:white;
                border:none; padding:3px 10px; border-radius:4px; cursor:pointer;">
                ⏹️ Stop
            </button>
        </div>
        <script>
        setTimeout(function() {{
            window.speechSynthesis.cancel();
            var u = new SpeechSynthesisUtterance(`{clean}`);
            u.lang='en-US'; u.rate=0.85;
            window.speechSynthesis.speak(u);
        }}, 600);
        </script>
        """, height=50)

# ════════════════════════════════════════════════
# FINAL RESULTS
# ════════════════════════════════════════════════
elif st.session_state.quiz_done:
    report = get_final_report(
        st.session_state.questions,
        st.session_state.scores
    )

    # ── Total score banner ────────────────────────
    pct = report["percentage"]
    color = "#28a745" if pct >= 70 else "#ffc107" if pct >= 50 else "#dc3545"
    grade = "Excellent! 🌟" if pct >= 70 else "Good job! 👍" if pct >= 50 else "Keep practicing! 📚"

    st.markdown(f"""
    <div style="
        background:{color}22; border:3px solid {color};
        border-radius:20px; padding:30px;
        text-align:center; margin-bottom:25px;">
        <h1 style="color:{color}; font-size:3rem; margin:0;">
            {report['total_score']}/{report['max_score']}
        </h1>
        <h2 style="color:{color}; margin:5px 0;">{pct}%</h2>
        <h3 style="color:{color}; margin:5px 0;">{grade}</h3>
    </div>
    """, unsafe_allow_html=True)

    # ── Score breakdown ───────────────────────────
    st.subheader("📊 Question by Question")
    cols = st.columns(10)
    for i, (s, q) in enumerate(
        zip(st.session_state.scores, st.session_state.questions)
    ):
        c = "#28a745" if s >= 7 else "#ffc107" if s >= 5 else "#dc3545"
        cols[i].markdown(
            f"<div style='text-align:center; background:{c}22;"
            f"border:1px solid {c}; border-radius:8px; padding:8px;'>"
            f"<b style='color:{c}'>Q{i+1}</b><br>"
            f"<span style='color:{c}; font-size:18px;'>{s}</span>"
            f"<br><span style='font-size:10px; color:#888;'>{q['topic'][:6]}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.divider()

    # ── Topic breakdown ───────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💪 Strong Topics")
        if report["strong_topics"]:
            for t in report["strong_topics"]:
                avg = report["topic_averages"].get(t, 0)
                st.success(f"✅ {t} — {avg}/10")
        else:
            st.info("Keep practicing to build strong topics!")

    with col2:
        st.subheader("📚 Weak Topics (need revision)")
        if report["weak_topics"]:
            for t in report["weak_topics"]:
                avg = report["topic_averages"].get(t, 0)
                st.error(f"⚠️ {t} — {avg}/10")
        else:
            st.success("No weak topics — excellent work!")

    st.divider()

    # ── Recommendations ───────────────────────────
    if report["weak_topics"]:
        st.subheader("🎯 What to Study Next")
        for topic in report["weak_topics"]:
            st.markdown(f"- Revise **{topic}** concepts and practice more questions")

    st.divider()

    # ── Action buttons ────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Take Quiz Again", use_container_width=True, type="primary"):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()
    with col2:
        if st.button("📖 Go to Practice Mode", use_container_width=True):
            st.switch_page("app.py")
    with col3:
        # Download score report
        import pandas as pd
        score_df = pd.DataFrame({
            "Question": [q["question"][:60] for q in st.session_state.questions],
            "Topic": [q["topic"] for q in st.session_state.questions],
            "Score": st.session_state.scores
        })
        st.download_button(
            "📥 Download Report",
            score_df.to_csv(index=False),
            "quiz_report.csv",
            "text/csv",
            use_container_width=True
        )