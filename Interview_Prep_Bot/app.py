import streamlit as st
from rag import generate_practice_answer

st_html = st.components.v1.html

st.set_page_config(
    page_title="AI Interview Prep Bot",
    page_icon="🤖",
    layout="wide"
)

# Hide deploy button and footer
st.markdown("""
<style>
/* Hide only the Deploy button */
.stAppDeployButton {
    display: none !important;
}

/* Optional: hide footer */
footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Hide only the page labels */
[data-testid="stSidebarNav"] ul {
    display: none;
}
</style>
""", unsafe_allow_html=True)




# ── Session state defaults — MUST run before query param reading ──
if "mode" not in st.session_state:
    st.session_state.mode = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "auto_speak" not in st.session_state:
    st.session_state.auto_speak = True
if "pending_speech" not in st.session_state:
    st.session_state.pending_speech = ""
if "recognized_text" not in st.session_state:
    st.session_state.recognized_text = ""
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "type"
if "recognized_answer" not in st.session_state:
    st.session_state.recognized_answer = ""

# ── READ SPEECH/ANSWER FROM URL PARAMS — runs every rerun, after defaults exist ──
qp = st.query_params

if "speech" in qp and qp["speech"].strip():
    incoming = qp["speech"].strip()
    if incoming != st.session_state.recognized_text:
        st.session_state.recognized_text = incoming
        st.query_params.clear()
        st.rerun()

if "answer" in qp and qp["answer"].strip():
    incoming = qp["answer"].strip()
    if incoming != st.session_state.recognized_answer:
        st.session_state.recognized_answer = incoming
        st.query_params.clear()
        st.rerun()


# ══════════════════════════════════════════════════
# SCREEN 1 — MODE SELECTOR
# ══════════════════════════════════════════════════
if st.session_state.mode is None:

    st.markdown("""
    <div style="text-align:center; padding:30px 0 10px 0;">
        <h1>🤖 AI Interview Preparation Bot</h1>
        <p style="font-size:18px; color:#888;">
            215 real Data Science &amp; AI interview questions —
            practice free, anytime
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("## Choose your mode")
    st.markdown(" ")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div style="
            border:2px solid #667eea;
            border-radius:15px; padding:28px;
            min-height:280px;
            background:linear-gradient(135deg,#667eea11,#764ba211);">
            <h2 style="color:#667eea; margin-top:0;">💬 Practice Mode</h2>
            <p>Ask <b>any</b> Data Science or AI interview question freely.
            The bot retrieves relevant answers from 215 curated Q&amp;As
            and generates a detailed, interview-style explanation.</p>
            <ul>
                <li>Ask questions in any order</li>
                <li>Get code examples included</li>
                <li>Type <b>or</b> speak your question</li>
                <li>Bot speaks answers aloud</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(" ")
        if st.button(
            "▶ Start Practice Mode",
            type="primary",
            use_container_width=True,
            key="btn_practice"
        ):
            st.session_state.mode = "practice"
            st.rerun()

    with col2:
        st.markdown("""
        <div style="
            border:2px solid #f093fb;
            border-radius:15px; padding:28px;
            min-height:280px;
            background:linear-gradient(135deg,#f093fb11,#f5576c11);">
            <h2 style="color:#f093fb; margin-top:0;">🏆 Quiz Mode</h2>
            <p>Get tested with <b>10 random questions</b> covering all
            6 topics. The bot reads each question aloud, you answer by
            typing or speaking, then get AI score + detailed feedback.</p>
            <ul>
                <li>10 random questions covering all topics</li>
                <li>Bot speaks each question aloud</li>
                <li>Answer by typing <b>or</b> speaking</li>
                <li>AI scores using cosine similarity</li>
                <li>Final report: strong vs weak topics</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(" ")
        if st.button(
            "▶ Start Quiz Mode",
            type="primary",
            use_container_width=True,
            key="btn_quiz"
        ):
            st.session_state.mode = "quiz"
            st.rerun()

    st.divider()
    st.markdown("""
    <div style="text-align:center; color:#888; font-size:14px;">
        📚 Topics: Machine Learning · Deep Learning · NLP ·
        Statistics · Python &amp; SQL · System Design
    </div>
    """, unsafe_allow_html=True)

    st.stop()


# ══════════════════════════════════════════════════
# SCREEN 2 — QUIZ MODE
# ══════════════════════════════════════════════════
if st.session_state.mode == "quiz":

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from quiz_mode import (
        pick_10_questions, score_answer,
        get_feedback, save_score, get_final_report
    )

    # NOTE: recognized_answer is NOT in this dict — it's already
    # initialized above (top of file) so it must never be reset here,
    # otherwise the speech-to-textarea value gets wiped on every rerun.
    quiz_defaults = {
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
    }
    for k, v in quiz_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Quiz Sidebar ──────────────────────────────
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

        if st.session_state.quiz_started and not st.session_state.quiz_done:
            current = st.session_state.current_q
            st.subheader("📊 Progress")
            st.progress(current / 10)
            st.write(f"Question {current + 1} of 10")
            if st.session_state.scores:
                avg = sum(st.session_state.scores) / len(st.session_state.scores)
                st.metric("Average Score", f"{avg:.1f}/10")

        st.divider()

        if st.session_state.quiz_started:
            if st.button("🔄 Restart Quiz", use_container_width=True):
                for k, v in quiz_defaults.items():
                    st.session_state[k] = v
                st.session_state.recognized_answer = ""
                st.rerun()

        st.divider()
        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.mode = None
            for k, v in quiz_defaults.items():
                st.session_state[k] = v
            st.session_state.recognized_answer = ""
            st.rerun()

        if st.button("💬 Switch to Practice", use_container_width=True):
            st.session_state.mode = "practice"
            for k, v in quiz_defaults.items():
                st.session_state[k] = v
            st.session_state.recognized_answer = ""
            st.rerun()

    # ── Quiz Main UI ──────────────────────────────
    st.title("🏆 AI Interview Quiz Mode")
    st.caption("Test your knowledge — 10 questions covering all topics")
    st.divider()

    # ── START SCREEN ──────────────────────────────
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

    # ── QUIZ IN PROGRESS ──────────────────────────
    elif st.session_state.quiz_started and not st.session_state.quiz_done:

        current_idx = st.session_state.current_q
        question_data = st.session_state.questions[current_idx]

        # Question box
        st.markdown(f"""
        <div style="
            background:linear-gradient(135deg,#667eea22,#764ba222);
            border:2px solid #667eea;
            border-radius:15px; padding:25px; margin-bottom:20px;">
            <h3 style="color:#667eea; margin:0 0 10px 0;">
                Question {current_idx + 1} of 10
                <span style="font-size:14px; color:#888; margin-left:10px;">
                    [{question_data['topic']} — {question_data['difficulty']}]
                </span>
            </h3>
            <h2 style="margin:0;">{question_data['question']}</h2>
        </div>
        """, unsafe_allow_html=True)

        # Auto speak question
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

        # Previous scores
        if st.session_state.scores:
            cols = st.columns(len(st.session_state.scores))
            for i, s in enumerate(st.session_state.scores):
                color = "#28a745" if s >= 6 else "#dc3545"
                cols[i].markdown(
                    f"<div style='text-align:center; color:{color};"
                    f"font-weight:bold; font-size:13px;'>"
                    f"Q{i+1}<br>{s}/10</div>",
                    unsafe_allow_html=True
                )
            st.divider()

        # ── ANSWER SECTION ────────────────────────
        if not st.session_state.answer_submitted:
            st.subheader("✍️ Your Answer")

            # SPEECH ANSWER MODE
            if st.session_state.answer_mode == "speak":
                st.info("🎤 Click mic → speak → click **Use This Answer** → edit if needed → click **Submit**")

                speech_html = """
                <div style="font-family:Arial; padding:10px; text-align:center;">
                    <button id="mic-btn" onclick="toggleMic()" style="
                        background:#ff4b4b; color:white; border:none;
                        padding:12px 24px; border-radius:50px;
                        font-size:16px; cursor:pointer;
                        width:220px; margin:6px;">
                        🎤 Start Speaking
                    </button>

                    <div id="status" style="
                        background:#f0f2f6; border-radius:8px;
                        padding:10px; font-size:14px; color:#555;
                        margin:8px auto; max-width:520px;">
                        Click mic and speak your answer
                    </div>

                    <div style="text-align:left; max-width:520px;
                        margin:0 auto 6px auto;
                        font-size:13px; color:#888;">
                        📝 Recognized text:
                    </div>

                    <div id="transcript" style="
                        background:white; border:2px solid #ddd;
                        border-radius:10px; padding:12px;
                        font-size:15px; color:#333;
                        min-height:80px; max-width:520px;
                        margin:0 auto 12px auto;
                        text-align:left; white-space:pre-wrap;">
                        (nothing heard yet)
                    </div>

                    <button onclick="useAnswer()" style="
                        background:#28a745; color:white; border:none;
                        padding:12px 24px; border-radius:50px;
                        font-size:16px; cursor:pointer;
                        width:220px; margin:6px;">
                        ✅ Use This Answer
                    </button>
                </div>

                <script>
                var recog=null, listening=false, finalText='';

                function toggleMic(){
                    listening ? stopMic() : startMic();
                }

                function startMic(){
                    var API=window.SpeechRecognition||window.webkitSpeechRecognition;
                    if(!API){
                        setStatus('❌ Use Chrome!','#c62828','#ffebee');
                        return;
                    }
                    recog=new API();
                    recog.lang='en-US';
                    recog.continuous=true;
                    recog.interimResults=true;
                    finalText=''; listening=true;

                    document.getElementById('mic-btn').style.background='#cc0000';
                    document.getElementById('mic-btn').innerText='🔴 Stop';
                    document.getElementById('transcript').innerText='...';
                    setStatus('🔴 Listening — speak your answer...','#c62828','#ffebee');

                    recog.onresult=function(e){
                        finalText=''; var interim='';
                        for(var i=0;i<e.results.length;i++){
                            if(e.results[i].isFinal)
                                finalText+=e.results[i][0].transcript+' ';
                            else
                                interim+=e.results[i][0].transcript;
                        }
                        document.getElementById('transcript').innerText=
                            (finalText+interim).trim();
                    };

                    recog.onerror=function(e){
                        listening=false; resetMic();
                        setStatus('❌ Error: '+e.error,'#c62828','#ffebee');
                    };

                    recog.onend=function(){
                        listening=false; resetMic();
                        if(finalText.trim())
                            setStatus('✅ Done! Click "Use This Answer"',
                                '#1b5e20','#e8f5e9');
                    };

                    recog.start();
                }

                function stopMic(){
                    if(recog) recog.stop();
                    listening=false; resetMic();
                }

                function resetMic(){
                    document.getElementById('mic-btn').style.background='#ff4b4b';
                    document.getElementById('mic-btn').innerText='🎤 Start Speaking';
                }

                function setStatus(msg,color,bg){
                    var b=document.getElementById('status');
                    b.innerText=msg; b.style.color=color; b.style.background=bg;
                }

                function useAnswer(){
                    var text=finalText.trim()||
                        document.getElementById('transcript').innerText.trim();
                    if(!text||text==='(nothing heard yet)'||text.length<2){
                        setStatus('❌ Speak first!','#c62828','#ffebee');
                        return;
                    }
                    if(listening){ stopMic(); }
                    setStatus('🔎 Filling answer box...','#0d47a1','#e3f2fd');
                    setTimeout(function(){
                        try {
                            var areas = window.parent.document.querySelectorAll('textarea');
                            var filled = false;
                            for (var i = 0; i < areas.length; i++) {
                                var area = areas[i];
                                if (area.placeholder && area.placeholder.indexOf('Use This Answer') !== -1) {
                                    var setter = Object.getOwnPropertyDescriptor(
                                        window.HTMLTextAreaElement.prototype, 'value'
                                    ).set;
                                    setter.call(area, text);
                                    area.dispatchEvent(new Event('input', { bubbles: true }));
                                    area.dispatchEvent(new Event('change', { bubbles: true }));
                                    area.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    area.focus();
                                    filled = true;
                                    break;
                                }
                            }
                            if (filled) {
                                setStatus('✅ Answer box filled! Edit if needed, then Submit.','#1b5e20','#e8f5e9');
                            } else {
                                setStatus('⚠️ Could not find answer box. Please type manually.','#c62828','#ffebee');
                            }
                        } catch(err) {
                            setStatus('⚠️ Could not fill automatically. Please type manually.','#c62828','#ffebee');
                            console.log('Fill error:', err);
                        }
                    }, 150);
                }
                </script>
                """
                st_html(speech_html, height=320)

                st.markdown("**✏️ Your answer (edit if needed):**")
                user_answer = st.text_area(
                    "answer_area",
                    value=st.session_state.recognized_answer,
                    height=130,
                    placeholder="Speak above → click Use This Answer → text appears here. Or type directly.",
                    label_visibility="collapsed",
                    key="quiz_speech_answer"
                )

            # TYPE ANSWER MODE
            else:
                user_answer = st.text_area(
                    "Type your answer here:",
                    height=150,
                    placeholder="Type your answer in detail...",
                    key="quiz_type_answer"
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

            # Process answer
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

        # ── FEEDBACK DISPLAY ──────────────────────
        else:
            score    = st.session_state.scores[-1]
            feedback = st.session_state.feedbacks[-1]

            color = (
                "#28a745" if score >= 7 else
                "#ffc107" if score >= 5 else
                "#dc3545"
            )
            emoji = (
                "🌟" if score >= 7 else
                "👍" if score >= 5 else
                "📚"
            )
            label = (
                "Excellent!" if score >= 7 else
                "Good effort!" if score >= 5 else
                "Keep practicing!"
            )

            st.markdown(f"""
            <div style="
                background:{color}22; border:2px solid {color};
                border-radius:15px; padding:20px;
                text-align:center; margin-bottom:20px;">
                <h1 style="color:{color}; margin:0;">{emoji} {score}/10</h1>
                <p style="color:{color}; margin:5px 0 0 0; font-size:18px;">
                    {label}
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.current_answer:
                with st.expander("👤 Your Answer", expanded=False):
                    st.write(st.session_state.current_answer)

            st.markdown("### 📝 Feedback")
            st.markdown(feedback)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔊 Hear Feedback", key="speak_fb"):
                    clean = feedback.replace(
                        '"', "'"
                    ).replace('\n', ' ').replace('`', '')[:2000]
                    st_html(f"""
                    <script>
                    window.speechSynthesis.cancel();
                    var u=new SpeechSynthesisUtterance(`{clean}`);
                    u.lang='en-US'; u.rate=0.85;
                    window.speechSynthesis.speak(u);
                    </script>""", height=0)
            with c2:
                if st.button("⏹️ Stop", key="stop_fb"):
                    st_html(
                        "<script>window.speechSynthesis.cancel();</script>",
                        height=0
                    )

            st.divider()
            is_last = (current_idx >= 9)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                btn_label = (
                    "🏁 See Final Results" if is_last
                    else f"➡️ Next Question ({current_idx + 2}/10)"
                )
                if st.button(
                    btn_label,
                    type="primary",
                    use_container_width=True
                ):
                    if is_last:
                        st.session_state.quiz_done = True
                    else:
                        st.session_state.current_q += 1
                        st.session_state.answer_submitted = False
                        st.session_state.current_answer = ""
                        st.session_state.recognized_answer = ""
                    st.rerun()

        # Auto speak feedback
        if st.session_state.pending_speech and st.session_state.auto_speak:
            text = st.session_state.pending_speech
            clean = text.replace(
                '"', "'"
            ).replace('\n', ' ').replace('`', '')[:2000]
            st.session_state.pending_speech = ""
            st_html(f"""
            <div style="background:#e8f5e9; padding:8px;
                border-radius:8px; font-size:13px; margin:5px 0;">
                🔊 <b>Speaking feedback...</b>
                <button onclick="window.speechSynthesis.cancel()" style="
                    margin-left:8px; background:#ff4b4b; color:white;
                    border:none; padding:3px 10px;
                    border-radius:4px; cursor:pointer;">
                    ⏹️ Stop
                </button>
            </div>
            <script>
            setTimeout(function() {{
                window.speechSynthesis.cancel();
                var u=new SpeechSynthesisUtterance(`{clean}`);
                u.lang='en-US'; u.rate=0.85;
                window.speechSynthesis.speak(u);
            }}, 600);
            </script>
            """, height=50)

    # ── FINAL RESULTS ─────────────────────────────
    elif st.session_state.quiz_done:
        import pandas as pd

        report = get_final_report(
            st.session_state.questions,
            st.session_state.scores
        )
        pct   = report["percentage"]
        color = (
            "#28a745" if pct >= 70 else
            "#ffc107" if pct >= 50 else
            "#dc3545"
        )
        grade = (
            "Excellent! 🌟" if pct >= 70 else
            "Good job! 👍"  if pct >= 50 else
            "Keep practicing! 📚"
        )

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

        st.subheader("📊 Question by Question")
        cols = st.columns(10)
        for i, (s, q) in enumerate(zip(
            st.session_state.scores,
            st.session_state.questions
        )):
            c = (
                "#28a745" if s >= 7 else
                "#ffc107" if s >= 5 else
                "#dc3545"
            )
            cols[i].markdown(
                f"<div style='text-align:center; background:{c}22;"
                f"border:1px solid {c}; border-radius:8px; padding:8px;'>"
                f"<b style='color:{c}'>Q{i+1}</b><br>"
                f"<span style='color:{c}; font-size:18px;'>{s}</span><br>"
                f"<span style='font-size:10px; color:#888;'>"
                f"{q['topic'][:6]}</span></div>",
                unsafe_allow_html=True
            )

        st.divider()
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
            st.subheader("📚 Weak Topics")
            if report["weak_topics"]:
                for t in report["weak_topics"]:
                    avg = report["topic_averages"].get(t, 0)
                    st.error(f"⚠️ {t} — {avg}/10")
            else:
                st.success("No weak topics — excellent!")

        st.divider()
        if report["weak_topics"]:
            st.subheader("🎯 What to Study Next")
            for topic in report["weak_topics"]:
                st.markdown(
                    f"- Revise **{topic}** concepts and practice more questions"
                )

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "🔄 Take Quiz Again",
                use_container_width=True,
                type="primary"
            ):
                for k, v in quiz_defaults.items():
                    st.session_state[k] = v
                st.session_state.recognized_answer = ""
                st.rerun()
        with col2:
            if st.button(
                "💬 Go to Practice Mode",
                use_container_width=True
            ):
                st.session_state.mode = "practice"
                for k, v in quiz_defaults.items():
                    st.session_state[k] = v
                st.session_state.recognized_answer = ""
                st.rerun()
        with col3:
            score_df = pd.DataFrame({
                "Question": [
                    q["question"][:60]
                    for q in st.session_state.questions
                ],
                "Topic": [
                    q["topic"]
                    for q in st.session_state.questions
                ],
                "Score": st.session_state.scores
            })
            st.download_button(
                "📥 Download Report",
                score_df.to_csv(index=False),
                "quiz_report.csv",
                "text/csv",
                use_container_width=True
            )

    st.stop()


# ══════════════════════════════════════════════════
# SCREEN 3 — PRACTICE MODE
# ══════════════════════════════════════════════════
with st.sidebar:
    st.title("⚙️ Settings")
    st.divider()

    st.subheader("🎤 Input Mode")
    input_mode = st.radio(
        "How do you want to ask?",
        ["⌨️ Type", "🎤 Speak"],
        index=0
    )
    st.session_state.input_mode = (
        "speak" if "Speak" in input_mode else "type"
    )

    st.divider()
    st.subheader("🔊 Bot Voice")
    auto_speak = st.toggle("Bot speaks answers aloud", value=True)
    st.session_state.auto_speak = auto_speak
    if auto_speak:
        st.success("🔊 Voice is ON")
    else:
        st.info("🔇 Voice is OFF")

    st.divider()
    st.subheader("📚 Topics")
    for t in ["Machine Learning", "Deep Learning", "NLP",
              "Statistics", "Python & SQL", "System Design"]:
        st.write(f"✅ {t}")

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_speech = ""
        st.session_state.recognized_text = ""
        st.rerun()

    st.divider()
    st.subheader("🏆 Quiz Mode")
    if st.button(
        "🎯 Switch to Quiz",
        use_container_width=True,
        type="primary"
    ):
        st.session_state.mode = "quiz"
        st.rerun()

    st.divider()
    if st.button("🏠 Back to Home", use_container_width=True):
        st.session_state.mode = None
        st.session_state.messages = []
        st.session_state.pending_speech = ""
        st.session_state.recognized_text = ""
        st.rerun()

# ── Practice main ─────────────────────────────────
st.title("🤖 AI Interview Preparation Bot")
st.caption("Practice Mode — Ask any Data Science or AI interview question")

c1, c2 = st.columns(2)
with c1:
    st.info(
        f"🎤 {'Speech Mode' if st.session_state.input_mode == 'speak' else 'Text Mode'}"
    )
with c2:
    st.info(f"🔊 Voice {'ON' if st.session_state.auto_speak else 'OFF'}")

st.divider()

# Chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔊 Speak", key=f"sp_{i}"):
                    clean = msg["content"].replace(
                        '"', "'"
                    ).replace('\n', ' ').replace('`', '')[:3000]
                    st_html(f"""
                    <script>
                    window.speechSynthesis.cancel();
                    var u=new SpeechSynthesisUtterance(`{clean}`);
                    u.lang='en-US'; u.rate=0.9;
                    window.speechSynthesis.speak(u);
                    </script>""", height=0)
            with c2:
                if st.button("⏹️ Stop", key=f"st_{i}"):
                    st_html(
                        "<script>window.speechSynthesis.cancel();</script>",
                        height=0
                    )

if len(st.session_state.messages) == 0:
    st.markdown("""
    ### 👋 Welcome! Try asking:
    - *"What is overfitting?"*
    - *"Explain bagging vs boosting"*
    - *"How does LSTM work?"*
    - *"What is gradient descent?"*
    - *"Explain the bias-variance tradeoff"*
    """)

st.divider()


def process_question(question: str):
    question = question.strip()
    if not question:
        st.warning("⚠️ Please enter a question first.")
        return

    with st.chat_message("user"):
        st.markdown(f"**{question}**")
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("assistant"):
        with st.spinner("⚡ Getting your answer..."):
            result = generate_practice_answer(question)
        answer = result["answer"]
        st.markdown(answer)

        with st.expander("📊 RAG details"):
            st.write(f"**Topics:** {result['retrieved_topics']}")
            st.write(f"**Match:** {result['top_match'][:60]}...")
            st.write(f"**Score:** {result['top_similarity']}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "🔊 Speak Answer",
                key=f"spk_{len(st.session_state.messages)}"
            ):
                clean = answer.replace(
                    '"', "'"
                ).replace('\n', ' ').replace('`', '')[:3000]
                st_html(f"""
                <script>
                window.speechSynthesis.cancel();
                var u=new SpeechSynthesisUtterance(`{clean}`);
                u.lang='en-US'; u.rate=0.9;
                window.speechSynthesis.speak(u);
                </script>""", height=0)
        with c2:
            if st.button(
                "⏹️ Stop",
                key=f"stp_{len(st.session_state.messages)}"
            ):
                st_html(
                    "<script>window.speechSynthesis.cancel();</script>",
                    height=0
                )

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    st.session_state.pending_speech = answer


# ── SPEECH INPUT MODE ─────────────────────────────
if st.session_state.input_mode == "speak":
    st.subheader("🎤 Speak Your Question")
    st.info("🟢 Click mic → speak → click **Use This Text** → edit → click **Get Answer**")

    speech_html = """
    <div style="font-family:Arial; padding:10px; text-align:center;">
        <button id="mic-btn" onclick="toggleMic()" style="
            background:#ff4b4b; color:white; border:none;
            padding:14px 28px; border-radius:50px;
            font-size:18px; cursor:pointer;
            width:240px; margin:6px;">
            🎤 Start Speaking
        </button>
        <div id="status-box" style="
            background:#f0f2f6; border-radius:8px;
            padding:10px; font-size:14px; color:#555;
            margin:10px auto; max-width:560px;">
            Click mic to begin
        </div>
        <div style="text-align:left; max-width:560px;
            margin:0 auto 6px auto; font-size:13px; color:#888;">
            📝 Recognized text:
        </div>
        <div id="transcript-box" style="
            background:white; border:2px solid #ddd;
            border-radius:10px; padding:14px;
            font-size:16px; font-weight:bold; color:#333;
            min-height:60px; max-width:560px;
            margin:0 auto 14px auto;
            text-align:left; white-space:pre-wrap;">
            (nothing heard yet)
        </div>
        <button onclick="useThisText()" style="
            background:#28a745; color:white; border:none;
            padding:14px 28px; border-radius:50px;
            font-size:18px; cursor:pointer;
            width:240px; margin:6px;">
            ✅ Use This Text
        </button>
    </div>
    <script>
    var recognition=null, isListening=false, finalText='';
    function toggleMic(){if(isListening){stopMic();}else{startMic();}}
    function startMic(){
        var API=window.SpeechRecognition||window.webkitSpeechRecognition;
        if(!API){setStatus('❌ Use Google Chrome!','#c62828','#ffebee');return;}
        recognition=new API();
        recognition.lang='en-US';
        recognition.continuous=true;
        recognition.interimResults=true;
        finalText=''; isListening=true;
        document.getElementById('mic-btn').style.background='#cc0000';
        document.getElementById('mic-btn').innerText='🔴 Stop Listening';
        document.getElementById('transcript-box').innerText='...';
        setStatus('🔴 Listening — speak now...','#c62828','#ffebee');
        recognition.onresult=function(e){
            finalText=''; var interim='';
            for(var i=0;i<e.results.length;i++){
                if(e.results[i].isFinal) finalText+=e.results[i][0].transcript+' ';
                else interim+=e.results[i][0].transcript;
            }
            document.getElementById('transcript-box').innerText=
                (finalText+interim).trim();
        };
        recognition.onerror=function(e){
            isListening=false; resetMic();
            setStatus('❌ Error: '+e.error,'#c62828','#ffebee');
        };
        recognition.onend=function(){
            isListening=false; resetMic();
            if(finalText.trim())
                setStatus('✅ Done! Click "Use This Text"','#1b5e20','#e8f5e9');
        };
        recognition.start();
    }
    function stopMic(){if(recognition)recognition.stop();isListening=false;resetMic();}
    function resetMic(){
        document.getElementById('mic-btn').style.background='#ff4b4b';
        document.getElementById('mic-btn').innerText='🎤 Start Speaking';
    }
    function setStatus(msg,color,bg){
        var b=document.getElementById('status-box');
        b.innerText=msg; b.style.color=color; b.style.background=bg;
    }
    function useThisText(){
        var text=finalText.trim()||
            document.getElementById('transcript-box').innerText.trim();
        if(!text||text==='(nothing heard yet)'||text==='...'||text.length<2){
            setStatus('❌ No speech. Click mic first!','#c62828','#ffebee');
            return;
        }
        if(isListening){ stopMic(); }
        setStatus('🔎 Filling question box...','#0d47a1','#e3f2fd');
        setTimeout(function(){
            try {
                var areas = window.parent.document.querySelectorAll('textarea');
                var filled = false;
                for (var i = 0; i < areas.length; i++) {
                    var area = areas[i];
                    if (area.placeholder && area.placeholder.indexOf('Use This Text') !== -1) {
                        var setter = Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype, 'value'
                        ).set;
                        setter.call(area, text);
                        area.dispatchEvent(new Event('input', { bubbles: true }));
                        area.dispatchEvent(new Event('change', { bubbles: true }));
                        area.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        area.focus();
                        filled = true;
                        break;
                    }
                }
                if (filled) {
                    setStatus('✅ Question box filled! Edit if needed, then Get Answer.','#1b5e20','#e8f5e9');
                } else {
                    setStatus('⚠️ Could not find question box. Please type manually.','#c62828','#ffebee');
                }
            } catch(err) {
                setStatus('⚠️ Could not fill automatically. Please type manually.','#c62828','#ffebee');
                console.log('Fill error:', err);
            }
        }, 150);
    }
    </script>
    """
    st_html(speech_html, height=340)

    st.markdown("---")
    st.markdown("**✏️ Your question (edit if needed):**")

    question_input = st.text_area(
        label="q",
        value=st.session_state.recognized_text,
        height=110,
        placeholder="Speak above → click 'Use This Text' → appears here. Or type directly.",
        label_visibility="collapsed",
        key="speech_question_area"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        get_ans = st.button(
            "🚀 Get Answer",
            type="primary",
            use_container_width=True,
            key="speech_get_answer"
        )
    with col2:
        if st.button("🗑️ Clear", use_container_width=True, key="speech_clear"):
            st.session_state.recognized_text = ""
            st.rerun()

    if get_ans:
        if question_input.strip():
            st.session_state.recognized_text = ""
            process_question(question_input)
            st.rerun()
        else:
            st.warning("⚠️ Please speak or type a question first!")

# ── TEXT INPUT MODE ───────────────────────────────
else:
    user_input = st.chat_input("Type your interview question here...")
    if user_input:
        process_question(user_input)
        st.rerun()

# ── AUTO SPEAK ────────────────────────────────────
if st.session_state.pending_speech and st.session_state.auto_speak:
    text = st.session_state.pending_speech
    clean = text.replace('"', "'").replace('\n', ' ').replace('`', '')[:3000]
    st.session_state.pending_speech = ""
    st_html(f"""
    <div style="background:#e8f5e9; padding:10px;
        border-radius:8px; margin:5px 0; font-size:14px;">
        🔊 <b>Speaking answer...</b>
        <button onclick="window.speechSynthesis.cancel()" style="
            margin-left:10px; background:#ff4b4b; color:white;
            border:none; padding:4px 12px;
            border-radius:5px; cursor:pointer;">
            ⏹️ Stop
        </button>
    </div>
    <script>
    setTimeout(function() {{
        window.speechSynthesis.cancel();
        var u=new SpeechSynthesisUtterance(`{clean}`);
        u.lang='en-US'; u.rate=0.85; u.pitch=1.0; u.volume=1.0;
        window.speechSynthesis.speak(u);
    }}, 500);
    </script>
    """, height=55)