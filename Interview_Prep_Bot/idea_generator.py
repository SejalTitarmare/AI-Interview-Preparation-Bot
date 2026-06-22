"""
idea_generator.py
─────────────────
Self-contained Project Idea Generator.
Called from app.py when st.session_state.mode == "ideas".
Uses the same Groq LLM that Practice and Quiz modes already use.
No new installs needed — only langchain_groq + json + os.
"""

import os
import json
import streamlit as st
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


# ── Groq LLM (same model as the rest of your project) ────────────────
def get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.8   # slightly high = more creative ideas
    )


# ── Build the prompt from user form inputs ────────────────────────────
def build_prompt(domain, difficulty, timeline, tech_stack, goal, special_wish):
    tech_str = ", ".join(tech_stack) if tech_stack else "Python"
    wish_line = f"- Special requirement: {special_wish}" if special_wish.strip() else ""

    prompt = f"""
You are an expert project mentor for Data Science and AI students preparing for internships.

A student needs 3 project ideas with these exact requirements:
- Domain: {domain}
- Difficulty: {difficulty}
- Timeline: {timeline}
- Tech stack they already know: {tech_str}
- Goal: {goal}
{wish_line}

Generate exactly 3 project ideas. Each idea must strictly use only the tech stack listed above.
Return ONLY valid JSON — no extra text, no markdown, no backticks.

{{
  "ideas": [
    {{
      "title": "short project name",
      "difficulty": "Beginner or Intermediate or Advanced",
      "problem": "one sentence: what real problem does this solve?",
      "solution": "two sentences: how does the AI/code solve it?",
      "tech_stack": ["tool1", "tool2", "tool3"],
      "timeline": "{timeline}",
      "architecture": [
        "Step 1: ...",
        "Step 2: ...",
        "Step 3: ...",
        "Step 4: ..."
      ],
      "day_plan": {{
        "Day 1": "what to build today",
        "Day 2": "what to build today",
        "Day 3": "what to build today"
      }},
      "core_features": ["feature 1", "feature 2", "feature 3"],
      "bonus_features": ["bonus 1", "bonus 2"],
      "why_impressive": "one sentence: why this stands out for internship/portfolio",
      "github_tips": "one sentence: how to present this well on GitHub"
    }}
  ]
}}

Rules:
- Make day_plan match the timeline exactly (e.g. 7 entries for 7 days, 14 for 14 days)
- Make idea 1 beginner-friendly, idea 2 intermediate, idea 3 advanced
- Each idea must be different — different problem, different approach
- Use only tools from the tech stack the student selected
- Return ONLY the JSON object, nothing else
""".strip()
    return prompt


# ── Call Groq and parse JSON response ────────────────────────────────
def generate_ideas(domain, difficulty, timeline, tech_stack, goal, special_wish):
    try:
        llm = get_llm()
        prompt = build_prompt(domain, difficulty, timeline, tech_stack, goal, special_wish)
        response = llm.invoke(prompt)
        raw = response.content.strip()

        # Strip markdown fences if model added them anyway
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        return data.get("ideas", [])

    except json.JSONDecodeError:
        st.error("⚠️ The AI returned an unexpected format. Please try again.")
        return []
    except Exception as e:
        err = str(e)
        if "429" in err:
            st.error("⏳ Groq rate limit hit. Wait 1 minute and try again.")
        else:
            st.error(f"❌ Error: {err}")
        return []


# ── Save idea to data/saved_ideas.json ───────────────────────────────
def save_idea(idea: dict):
    os.makedirs("data", exist_ok=True)
    path = "data/saved_ideas.json"

    saved = []
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                saved = json.load(f)
        except Exception:
            saved = []

    # Avoid duplicate saves
    existing_titles = [s.get("title") for s in saved]
    if idea["title"] not in existing_titles:
        saved.append(idea)
        with open(path, "w") as f:
            json.dump(saved, f, indent=2)
        return True
    return False   # already saved


# ── Load all saved ideas ──────────────────────────────────────────────
def load_saved_ideas():
    path = "data/saved_ideas.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []


# ── Format idea as plain text for download ───────────────────────────
def idea_to_text(idea: dict) -> str:
    day_plan = idea.get("day_plan", {})
    day_lines = "\n".join([f"  {k}: {v}" for k, v in day_plan.items()])

    arch = idea.get("architecture", [])
    arch_lines = "\n".join([f"  {step}" for step in arch])

    core = "\n".join([f"  - {f}" for f in idea.get("core_features", [])])
    bonus = "\n".join([f"  - {f}" for f in idea.get("bonus_features", [])])

    return f"""
╔══════════════════════════════════════════════╗
  PROJECT: {idea.get('title', '')}
  Difficulty: {idea.get('difficulty', '')}  |  Timeline: {idea.get('timeline', '')}
╚══════════════════════════════════════════════╝

📌 PROBLEM
{idea.get('problem', '')}

💡 SOLUTION
{idea.get('solution', '')}

🛠️ TECH STACK
{', '.join(idea.get('tech_stack', []))}

🏗️ ARCHITECTURE
{arch_lines}

📅 DAY BY DAY PLAN
{day_lines}

✅ CORE FEATURES
{core}

🎁 BONUS FEATURES
{bonus}

🌟 WHY IT'S IMPRESSIVE
{idea.get('why_impressive', '')}

📁 GITHUB TIP
{idea.get('github_tips', '')}
""".strip()


# ══════════════════════════════════════════════════════════════════════
# MAIN FUNCTION — called from app.py
# ══════════════════════════════════════════════════════════════════════
def show_idea_generator():

    # ── Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        st.title("💡 Idea Generator")
        st.divider()
        st.markdown("""
        **How it works:**
        1. Fill the form on the right
        2. Click **Generate Ideas**
        3. Browse 3 tailored project cards
        4. Click **Expand** to see the full plan
        5. Download or save ideas you like
        """)
        st.divider()

        saved = load_saved_ideas()
        st.subheader(f"🔖 Saved Ideas ({len(saved)})")
        if saved:
            for s in saved:
                st.success(f"✅ {s['title']}")
        else:
            st.info("No saved ideas yet. Save one below!")

        st.divider()
        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.mode = None
            # Clear idea generator session state
            for key in ["ig_ideas", "ig_expanded", "ig_generated"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # ── Page Header ───────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding:20px 0 10px 0;">
        <h1>💡 Project Idea Generator</h1>
        <p style="font-size:16px; color:#888;">
            Fill the form below — get 3 project ideas tailored to your
            stack, level, and timeline. Each comes with a full build plan.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # ── Session state for this page ───────────────────────────────────
    if "ig_ideas" not in st.session_state:
        st.session_state.ig_ideas = []
    if "ig_expanded" not in st.session_state:
        st.session_state.ig_expanded = None   # index of expanded card
    if "ig_generated" not in st.session_state:
        st.session_state.ig_generated = False

    # ══════════════════════════════════════════════════════════════════
    # FORM — user fills this in
    # ══════════════════════════════════════════════════════════════════
    with st.form("idea_form"):
        st.subheader("📋 Tell us about your project")

        col1, col2, col3 = st.columns(3)
        with col1:
            domain = st.selectbox("🎯 Domain", [
                "Machine Learning",
                "Natural Language Processing (NLP)",
                "Computer Vision",
                "Data Analysis & Visualization",
                "Web Scraping & Automation",
                "Recommendation System",
                "Chatbot / Conversational AI",
                "RAG Application",
                "Time Series Forecasting",
                "Other / Custom"
            ])
        with col2:
            difficulty = st.selectbox("📊 Difficulty", [
                "Beginner",
                "Intermediate",
                "Advanced"
            ])
        with col3:
            timeline = st.selectbox("⏰ Timeline", [
                "3 days",
                "7 days",
                "14 days",
                "1 month"
            ])

        st.markdown("**🛠️ Tech stack you already know** *(select all that apply)*")
        tech_cols = st.columns(4)
        tech_options = {
            "Python":       tech_cols[0].checkbox("Python",       value=True),
            "Streamlit":    tech_cols[0].checkbox("Streamlit",    value=True),
            "Groq API":     tech_cols[0].checkbox("Groq API",     value=True),
            "LangChain":    tech_cols[1].checkbox("LangChain"),
            "ChromaDB":     tech_cols[1].checkbox("ChromaDB"),
            "FastAPI":      tech_cols[1].checkbox("FastAPI"),
            "PyPDF2":       tech_cols[2].checkbox("PyPDF2"),
            "Pandas":       tech_cols[2].checkbox("Pandas"),
            "NumPy":        tech_cols[2].checkbox("NumPy"),
            "Matplotlib":   tech_cols[3].checkbox("Matplotlib"),
            "Scikit-learn": tech_cols[3].checkbox("Scikit-learn"),
            "HuggingFace":  tech_cols[3].checkbox("HuggingFace"),
        }

        col4, col5 = st.columns(2)
        with col4:
            goal = st.selectbox("🏆 Goal", [
                "Internship portfolio project",
                "Final year college project",
                "Personal learning",
                "GitHub portfolio",
                "Freelance demo"
            ])
        with col5:
            special_wish = st.text_input(
                "✨ Special wish (optional)",
                placeholder='e.g. "must use RAG", "healthcare domain", "include speech"'
            )

        st.markdown(" ")
        submitted = st.form_submit_button(
            "🚀 Generate 3 Project Ideas",
            type="primary",
            use_container_width=True
        )

    # ── Handle form submission ────────────────────────────────────────
    if submitted:
        selected_tech = [name for name, checked in tech_options.items() if checked]
        if not selected_tech:
            st.warning("⚠️ Please select at least one technology you know.")
        else:
            with st.spinner("🤖 Groq is thinking up 3 tailored ideas for you..."):
                ideas = generate_ideas(
                    domain, difficulty, timeline,
                    selected_tech, goal, special_wish
                )
            if ideas:
                st.session_state.ig_ideas = ideas
                st.session_state.ig_expanded = None
                st.session_state.ig_generated = True
                st.rerun()

    # ══════════════════════════════════════════════════════════════════
    # RESULTS — show idea cards
    # ══════════════════════════════════════════════════════════════════
    if st.session_state.ig_generated and st.session_state.ig_ideas:

        st.divider()
        st.subheader("✨ Here are your 3 project ideas")
        st.caption("Click **Expand** on any card to see the full day-by-day plan")
        st.markdown(" ")

        ideas = st.session_state.ig_ideas

        # ── 3 idea cards side by side ──────────────────────────────
        card_cols = st.columns(3)
        card_colors = ["#667eea", "#f093fb", "#43e97b"]
        card_bg     = ["#667eea11", "#f093fb11", "#43e97b11"]

        for idx, (idea, col) in enumerate(zip(ideas, card_cols)):
            with col:
                diff_badge = idea.get("difficulty", f"Idea {idx+1}")
                title      = idea.get("title", "Untitled")
                problem    = idea.get("problem", "")
                tech       = ", ".join(idea.get("tech_stack", [])[:3])
                color      = card_colors[idx]
                bg         = card_bg[idx]

                st.markdown(f"""
                <div style="
                    border:2px solid {color};
                    border-radius:15px; padding:20px;
                    background:{bg}; min-height:220px;">
                    <span style="
                        background:{color}33;
                        color:{color};
                        padding:3px 10px;
                        border-radius:20px;
                        font-size:12px;
                        font-weight:bold;">
                        {diff_badge}
                    </span>
                    <h3 style="color:{color}; margin:12px 0 8px 0;">
                        {title}
                    </h3>
                    <p style="font-size:13px; color:#888; margin:0 0 10px 0;">
                        {problem}
                    </p>
                    <p style="font-size:12px; color:#aaa; margin:0;">
                        🛠️ {tech}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(" ")

                # Expand / Collapse toggle
                is_expanded = (st.session_state.ig_expanded == idx)
                btn_label   = "🔼 Collapse" if is_expanded else "▶ Expand Idea"
                if st.button(btn_label, key=f"expand_{idx}", use_container_width=True):
                    st.session_state.ig_expanded = None if is_expanded else idx
                    st.rerun()

        # ── Expanded idea detail ───────────────────────────────────
        if st.session_state.ig_expanded is not None:
            idx  = st.session_state.ig_expanded
            idea = ideas[idx]
            color = card_colors[idx]

            st.divider()
            st.markdown(f"""
            <div style="
                border-left: 5px solid {color};
                padding-left: 20px;
                margin-bottom: 10px;">
                <h2 style="margin:0; color:{color};">
                    {idea.get('title', '')}
                </h2>
                <p style="margin:4px 0 0 0; color:#888; font-size:14px;">
                    {idea.get('difficulty','')} &nbsp;|&nbsp; {idea.get('timeline','')}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Overview row
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📌 Problem**")
                st.info(idea.get("problem", ""))
            with c2:
                st.markdown("**💡 Solution**")
                st.info(idea.get("solution", ""))

            # Tech stack
            st.markdown("**🛠️ Tech Stack**")
            tech_cols_out = st.columns(len(idea.get("tech_stack", [])) or 1)
            for ti, tech in enumerate(idea.get("tech_stack", [])):
                tech_cols_out[ti].markdown(
                    f"<div style='text-align:center; background:{color}22;"
                    f"border:1px solid {color}; border-radius:8px;"
                    f"padding:8px; font-size:13px; color:{color};"
                    f"font-weight:bold;'>{tech}</div>",
                    unsafe_allow_html=True
                )

            st.markdown(" ")

            # Architecture + Day Plan side by side
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🏗️ Architecture**")
                for step in idea.get("architecture", []):
                    st.markdown(f"→ {step}")

            with c2:
                st.markdown("**📅 Day by Day Plan**")
                day_plan = idea.get("day_plan", {})
                for day, task in day_plan.items():
                    st.markdown(
                        f"<div style='margin-bottom:6px;'>"
                        f"<span style='color:{color}; font-weight:bold;"
                        f"font-size:13px;'>{day}</span> — "
                        f"<span style='font-size:13px;'>{task}</span></div>",
                        unsafe_allow_html=True
                    )

            st.markdown(" ")

            # Features
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**✅ Core Features**")
                for f in idea.get("core_features", []):
                    st.success(f"✔ {f}")
            with c2:
                st.markdown("**🎁 Bonus Features**")
                for f in idea.get("bonus_features", []):
                    st.info(f"⭐ {f}")

            # Why impressive + GitHub tip
            st.markdown("**🌟 Why This Is Impressive for Internships**")
            st.markdown(
                f"<div style='background:{color}11; border-left:4px solid {color};"
                f"padding:12px 16px; border-radius:0 8px 8px 0; font-size:14px;'>"
                f"{idea.get('why_impressive','')}</div>",
                unsafe_allow_html=True
            )

            st.markdown("**📁 GitHub Tip**")
            st.markdown(f"> {idea.get('github_tips','')}")

            st.divider()

            # Action buttons
            btn1, btn2, btn3 = st.columns(3)

            # Download button
            with btn1:
                plan_text = idea_to_text(idea)
                safe_title = idea.get("title", "idea").replace(" ", "_").lower()
                st.download_button(
                    label="📥 Download Full Plan",
                    data=plan_text,
                    file_name=f"{safe_title}_plan.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            # Save idea button
            with btn2:
                if st.button("🔖 Save This Idea", use_container_width=True,
                             key=f"save_{idx}"):
                    was_saved = save_idea(idea)
                    if was_saved:
                        st.success("✅ Idea saved! See sidebar.")
                    else:
                        st.info("ℹ️ This idea is already saved.")
                    st.rerun()

            # Generate new ideas button
            with btn3:
                if st.button("🔄 Generate New Ideas", use_container_width=True,
                             key="regen"):
                    st.session_state.ig_ideas = []
                    st.session_state.ig_expanded = None
                    st.session_state.ig_generated = False
                    st.rerun()