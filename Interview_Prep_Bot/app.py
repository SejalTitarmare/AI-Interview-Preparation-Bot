import streamlit as st
from rag import generate_practice_answer

st_html = st.components.v1.html

st.set_page_config(
    page_title="AI Interview Prep Bot",
    page_icon="🤖",
    layout="wide"
)



# ── Session state ─────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "auto_speak" not in st.session_state:
    st.session_state.auto_speak = True
if "pending_speech" not in st.session_state:
    st.session_state.pending_speech = ""
if "recognized_text" not in st.session_state:
    st.session_state.recognized_text = ""
if "submit_speech" not in st.session_state:
    st.session_state.submit_speech = False

# ── Sidebar ───────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")
    st.divider()
    st.subheader("🎤 Input Mode")
    input_mode = st.radio(
        "Choose input mode:",
        ["⌨️ Type", "🎤 Speak"],
        index=0
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
        st.session_state.submit_speech = False
        st.rerun()

# ── Main ──────────────────────────────────────────
st.title("🤖 AI Interview Preparation Bot")
st.caption("Practice Mode — Ask any Data Science or AI interview question")

c1, c2 = st.columns(2)
with c1:
    st.info(f"🎤 {'Speech Mode' if 'Speak' in input_mode else 'Text Mode'}")
with c2:
    st.info(f"🔊 Voice {'ON' if auto_speak else 'OFF'}")

st.divider()

# ── Chat history ──────────────────────────────────
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
                    var u = new SpeechSynthesisUtterance(`{clean}`);
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
    ### 👋 Welcome! Try these:
    - *"What is overfitting?"*
    - *"Explain bagging vs boosting"*
    - *"How does LSTM work?"*
    - *"What is gradient descent?"*
    """)

st.divider()


# ── SHARED: process any question ─────────────────
def process_question(question: str):
    """Called from both text and speech mode"""
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
            if st.button("🔊 Speak Answer", key=f"spk_ans_{len(st.session_state.messages)}"):
                clean = answer.replace(
                    '"', "'"
                ).replace('\n', ' ').replace('`', '')[:3000]
                st_html(f"""
                <script>
                window.speechSynthesis.cancel();
                var u = new SpeechSynthesisUtterance(`{clean}`);
                u.lang='en-US'; u.rate=0.9;
                window.speechSynthesis.speak(u);
                </script>""", height=0)
        with c2:
            if st.button("⏹️ Stop", key=f"stp_ans_{len(st.session_state.messages)}"):
                st_html(
                    "<script>window.speechSynthesis.cancel();</script>",
                    height=0
                )

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    st.session_state.pending_speech = answer


# ════════════════════════════════════════════════
# SPEECH MODE
# ════════════════════════════════════════════════
if "Speak" in input_mode:
    st.subheader("🎤 Speak Your Question")
    st.info("🟢 Step 1: Click mic & speak  →  Step 2: Click **Use This Text**  →  Step 3: Click **Get Answer**")

    # ── SPEECH COMPONENT ─────────────────────────
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
    var recognition = null;
    var isListening = false;
    var finalText = '';

    function toggleMic() {
        if (isListening) { stopMic(); } else { startMic(); }
    }

    function startMic() {
        var API = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!API) {
            setStatus('❌ Use Google Chrome!', '#c62828', '#ffebee');
            return;
        }
        recognition = new API();
        recognition.lang = 'en-US';
        recognition.continuous = true;
        recognition.interimResults = true;
        finalText = '';
        isListening = true;

        document.getElementById('mic-btn').style.background = '#cc0000';
        document.getElementById('mic-btn').innerText = '🔴 Stop Listening';
        document.getElementById('transcript-box').innerText = '...';
        setStatus('🔴 Listening — speak your question now...', '#c62828', '#ffebee');

        recognition.onresult = function(e) {
            finalText = '';
            var interim = '';
            for (var i = 0; i < e.results.length; i++) {
                if (e.results[i].isFinal) {
                    finalText += e.results[i][0].transcript + ' ';
                } else {
                    interim += e.results[i][0].transcript;
                }
            }
            document.getElementById('transcript-box').innerText =
                (finalText + interim).trim();
        };

        recognition.onerror = function(e) {
            isListening = false; resetMic();
            setStatus('❌ Error: ' + e.error + '. Try again.', '#c62828', '#ffebee');
        };

        recognition.onend = function() {
            isListening = false; resetMic();
            if (finalText.trim()) {
                setStatus(
                    '✅ Got it! Now click "Use This Text" button below.',
                    '#1b5e20', '#e8f5e9'
                );
            }
        };

        recognition.start();
    }

    function stopMic() {
        if (recognition) recognition.stop();
        isListening = false; resetMic();
    }

    function resetMic() {
        document.getElementById('mic-btn').style.background = '#ff4b4b';
        document.getElementById('mic-btn').innerText = '🎤 Start Speaking';
    }

    function setStatus(msg, color, bg) {
        var b = document.getElementById('status-box');
        b.innerText = msg; b.style.color = color; b.style.background = bg;
    }

    function useThisText() {
        // Get the final recognized text
        var text = finalText.trim() ||
            document.getElementById('transcript-box').innerText.trim();

        if (!text || text === '(nothing heard yet)' ||
            text === '...' || text.length < 2) {
            setStatus('❌ No speech detected. Click mic and speak first!',
                '#c62828', '#ffebee');
            return;
        }

        setStatus('✅ Text sent to box below! Click "Get Answer".', '#1b5e20', '#e8f5e9');

        // ── FIND THE STREAMLIT TEXT AREA AND FILL IT ─────────────────────
        // We look in the PARENT window for a textarea and fill it
        // using React's native setter so Streamlit detects the change
        setTimeout(function() {
            try {
                var areas = window.parent.document.querySelectorAll('textarea');
                for (var i = 0; i < areas.length; i++) {
                    var area = areas[i];
                    // Target our specific textarea by placeholder text
                    if (area.placeholder &&
                        area.placeholder.indexOf('Use This Text') !== -1) {

                        // Use React's internal setter
                        var setter = Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype, 'value'
                        ).set;
                        setter.call(area, text);

                        // Dispatch input event so React/Streamlit detects change
                        area.dispatchEvent(new Event('input', { bubbles: true }));
                        area.dispatchEvent(new Event('change', { bubbles: true }));

                        // Scroll to the textarea
                        area.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        area.focus();
                        break;
                    }
                }
            } catch(err) {
                console.log('Direct fill error:', err);
            }
        }, 200);
    }
    </script>
    """

    st_html(speech_html, height=340)

    st.markdown("---")
    st.markdown("**✏️ Your question (edit if needed, then click Get Answer):**")

    # Text area — placeholder MUST match what JS looks for
    question_input = st.text_area(
        label="q",
        value=st.session_state.recognized_text,
        height=110,
        placeholder="After clicking 'Use This Text' above — text appears here automatically. Or type directly.",
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
            st.session_state.pending_speech = st.session_state.messages[-1]["content"] if st.session_state.messages else ""
            st.rerun()
        else:
            st.warning("⚠️ Please speak or type a question first!")

# ════════════════════════════════════════════════
# TEXT MODE
# ════════════════════════════════════════════════
else:
    user_input = st.chat_input(
        "Type your interview question here..."
    )
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
        var u = new SpeechSynthesisUtterance(`{clean}`);
        u.lang='en-US'; u.rate=0.85;
        u.pitch=1.0; u.volume=1.0;
        window.speechSynthesis.speak(u);
    }}, 500);
    </script>
    """, height=55)