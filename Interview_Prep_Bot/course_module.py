"""
course_module.py  —  COMPLETE FULL WORKING VERSION
Company Admin: PDF upload → Groq extracts modules → save → get course code
Student: enter code → see modules → pick module → get 3 ideas → save/download
"""

import os
import json
import datetime
import streamlit as st
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


# ══════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════

def get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.7
    )

def ensure_data_files():
    os.makedirs("data", exist_ok=True)
    for fname in ["courses.json", "saved_projects.json"]:
        path = f"data/{fname}"
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)

def read_json(path: str) -> list:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []

def write_json(path: str, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def clean_llm_json(raw: str) -> str:
    """Strip markdown fences from LLM output before JSON parsing."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") or part.startswith("["):
                return part
    return raw


# ══════════════════════════════════════════════════
# PDF EXTRACTION
# ══════════════════════════════════════════════════

def extract_text_from_pdf(uploaded_file) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(uploaded_file)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append(f"[Page {i+1}]\n{text.strip()}")
        return "\n\n".join(pages)
    except ImportError:
        st.error("PyPDF2 not installed. Run: pip install PyPDF2")
        return ""
    except Exception as e:
        st.error(f"Could not read PDF: {e}")
        return ""


# ══════════════════════════════════════════════════
# GROQ — MODULE EXTRACTION FROM PDF TEXT
# ══════════════════════════════════════════════════

def extract_modules_with_groq(pdf_text: str) -> dict:
    """
    Sends PDF text to Groq.
    Returns dict with course_name and list of modules.
    """
    try:
        llm = get_llm()
        # Limit text to avoid token overflow
        text_chunk = pdf_text[:4000]

        prompt = f"""
You are an expert at reading course syllabi.
Read the following course syllabus text and extract ALL modules/weeks.

Return ONLY valid JSON — no markdown, no extra text, no backticks.

{{
  "course_name": "Full name of the course",
  "modules": [
    {{
      "name": "Module 1: Python Basics",
      "week": "Week 1-2",
      "topics": ["variables", "loops", "functions", "OOP"],
      "tools": ["Python", "Jupyter Notebook"]
    }},
    {{
      "name": "Module 2: Pandas and Data Analysis",
      "week": "Week 3-4",
      "topics": ["DataFrames", "data cleaning", "groupby"],
      "tools": ["Python", "Pandas", "NumPy", "Matplotlib"]
    }}
  ]
}}

Rules:
- Extract every module/week/unit you find
- topics = concepts taught in that module
- tools = libraries, software, frameworks mentioned for that module
- If week info is missing, use "Week N"
- Return ONLY the JSON object, nothing else

Syllabus text:
{text_chunk}
""".strip()

        response = llm.invoke(prompt)
        raw = clean_llm_json(response.content)
        data = json.loads(raw)
        return data

    except json.JSONDecodeError:
        st.error("Groq returned unexpected format. Try again.")
        return {}
    except Exception as e:
        err = str(e)
        if "429" in err:
            st.error("Rate limit hit. Wait 1 minute and try again.")
        else:
            st.error(f"Groq error: {err}")
        return {}


# ══════════════════════════════════════════════════
# GROQ — IDEA GENERATION FROM MODULE
# ══════════════════════════════════════════════════

def generate_ideas_for_module(module: dict) -> list:
    """
    Sends one module's content to Groq.
    Returns list of 3 project idea dicts.
    """
    try:
        llm = get_llm()

        topics_str = ", ".join(module.get("topics", []))
        tools_str  = ", ".join(module.get("tools", []))
        mod_name   = module.get("name", "this module")

        prompt = f"""
You are an expert project mentor for Data Science and AI students.

A student just completed: {mod_name}
Topics they learned: {topics_str}
Tools/libraries they now know: {tools_str}

Generate exactly 3 project ideas using ONLY the tools and topics listed above.
Do NOT suggest any tool or library that is NOT in the list above.
Make idea 1 beginner, idea 2 intermediate, idea 3 advanced.

Return ONLY valid JSON — no markdown, no extra text, no backticks.

{{
  "ideas": [
    {{
      "title": "short project name",
      "difficulty": "Beginner",
      "problem": "one sentence: what real problem does this solve?",
      "solution": "two sentences: how does the code solve it?",
      "tech_stack": ["tool1", "tool2"],
      "day_plan": {{
        "Day 1": "what to build",
        "Day 2": "what to build",
        "Day 3": "what to build",
        "Day 4": "what to build",
        "Day 5": "what to build",
        "Day 6": "what to build",
        "Day 7": "deploy and test"
      }},
      "core_features": ["feature 1", "feature 2", "feature 3"],
      "bonus_features": ["bonus 1", "bonus 2"],
      "why_impressive": "one sentence why this is great for internship"
    }}
  ]
}}

Return ONLY the JSON. Nothing else.
""".strip()

        response = llm.invoke(prompt)
        raw = clean_llm_json(response.content)
        data = json.loads(raw)
        return data.get("ideas", [])

    except json.JSONDecodeError:
        st.error("Groq returned unexpected format. Please try again.")
        return []
    except Exception as e:
        err = str(e)
        if "429" in err:
            st.error("Rate limit hit. Wait 1 minute and try again.")
        else:
            st.error(f"Groq error: {err}")
        return []


# ══════════════════════════════════════════════════
# COURSE CODE GENERATION + SAVE
# ══════════════════════════════════════════════════

def generate_course_code(course_name: str) -> str:
    """Generate unique course code like DSB-2026."""
    words = course_name.strip().split()
    initials = "".join(w[0].upper() for w in words if w)[:4]
    year = datetime.datetime.now().year
    base_code = f"{initials}-{year}"

    # If already exists, append counter
    courses = read_json("data/courses.json")
    existing_codes = [c.get("course_code", "") for c in courses]
    if base_code not in existing_codes:
        return base_code
    counter = 2
    while f"{base_code}-{counter}" in existing_codes:
        counter += 1
    return f"{base_code}-{counter}"


def save_course(course_name: str, modules: list) -> str:
    """Save course to courses.json. Returns the course code."""
    ensure_data_files()
    courses = read_json("data/courses.json")
    code = generate_course_code(course_name)
    course_entry = {
        "course_code": code,
        "course_name": course_name,
        "modules": modules,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    courses.append(course_entry)
    write_json("data/courses.json", courses)
    return code


def load_course_by_code(code: str) -> dict:
    """Find and return a course by its code. Returns {} if not found."""
    courses = read_json("data/courses.json")
    return next((c for c in courses
                 if c.get("course_code", "").upper() == code.upper()), {})


def save_project(idea: dict, module_name: str, course_code: str):
    """Save a project idea to saved_projects.json."""
    ensure_data_files()
    projects = read_json("data/saved_projects.json")
    existing = [p.get("title") for p in projects]
    if idea.get("title") not in existing:
        projects.append({
            **idea,
            "module": module_name,
            "course_code": course_code,
            "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        write_json("data/saved_projects.json", projects)
        return True
    return False


def idea_to_text(idea: dict, module_name: str) -> str:
    """Format idea as plain text for download."""
    day_plan = idea.get("day_plan", {})
    days = "\n".join([f"  {k}: {v}" for k, v in day_plan.items()])
    core = "\n".join([f"  - {f}" for f in idea.get("core_features", [])])
    bonus = "\n".join([f"  - {f}" for f in idea.get("bonus_features", [])])
    return f"""
PROJECT: {idea.get('title', '')}
Module:  {module_name}
Difficulty: {idea.get('difficulty', '')}  |  Timeline: 7 days
{'='*50}

PROBLEM
{idea.get('problem', '')}

SOLUTION
{idea.get('solution', '')}

TECH STACK
{', '.join(idea.get('tech_stack', []))}

DAY BY DAY PLAN
{days}

CORE FEATURES
{core}

BONUS FEATURES
{bonus}

WHY IT IS IMPRESSIVE
{idea.get('why_impressive', '')}
""".strip()


# ══════════════════════════════════════════════════
# COMPANY ADMIN — FULL FLOW
# ══════════════════════════════════════════════════

def show_company_admin():
    st.markdown("""
    <div style="border-left:5px solid #fa8231;
        padding-left:20px; margin-bottom:20px;">
        <h2 style="margin:0; color:#fa8231;">🏢 Company Admin Panel</h2>
        <p style="margin:6px 0 0 0; color:#888; font-size:14px;">
            Upload PDF → Groq extracts modules → confirm → get course code to share
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Progress steps indicator
    step = st.session_state.get("cm_step", 1)
    steps = ["1️⃣ Upload PDF", "2️⃣ Review Modules", "3️⃣ Course Code Ready"]
    cols = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, steps)):
        active = (i + 1 == step)
        col.markdown(
            f"<div style='text-align:center; padding:8px; border-radius:8px;"
            f"background:{'#fa823133' if active else '#f0f0f0'};"
            f"border:{'2px solid #fa8231' if active else '1px solid #ddd'};"
            f"font-weight:{'bold' if active else 'normal'}; font-size:13px;'>"
            f"{label}</div>",
            unsafe_allow_html=True
        )
    st.divider()

    # ════════════════════════════════
    # STEP 1 — PDF Upload + Extraction
    # ════════════════════════════════
    if step == 1:
        st.subheader("📄 Upload Your Course Syllabus PDF")
        st.caption("PDF should list module names, topics per module, and tools/libraries used")

        uploaded_file = st.file_uploader(
            "Choose PDF file",
            type=["pdf"],
            key="course_pdf_uploader"
        )

        if uploaded_file:
            st.markdown(f"""
            <div style="background:#fa823111; border:1px solid #fa8231;
                border-radius:10px; padding:12px 16px; margin:10px 0;">
                📎 <b style="color:#fa8231;">{uploaded_file.name}</b>
                <span style="color:#888; font-size:13px; margin-left:8px;">
                ({round(uploaded_file.size/1024, 1)} KB)</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(" ")

            # Also allow pasting text directly
            st.markdown("**Or paste syllabus text directly (if no PDF):**")
            pasted_text = st.text_area(
                "Paste syllabus text here (optional — leave blank if using PDF)",
                height=120,
                placeholder="Module 1: Python Basics\n  Topics: variables, loops...\n  Tools: Python, Jupyter\n\nModule 2: ...",
                key="pasted_syllabus"
            )

            st.markdown(" ")
            if st.button("📖 Extract Text & Identify Modules",
                         type="primary", use_container_width=True,
                         key="extract_and_identify_btn"):

                # Use pasted text if provided, else extract from PDF
                if pasted_text.strip():
                    raw_text = pasted_text.strip()
                    st.session_state.cm_extracted_text = raw_text
                    source = "pasted text"
                else:
                    with st.spinner("📖 Reading PDF..."):
                        raw_text = extract_text_from_pdf(uploaded_file)
                    st.session_state.cm_extracted_text = raw_text
                    st.session_state.cm_pdf_name = uploaded_file.name
                    source = uploaded_file.name

                if not raw_text.strip():
                    st.error("Could not extract text. Try pasting the syllabus text directly.")
                else:
                    st.info(f"✅ Text extracted from {source} ({len(raw_text):,} chars). Now sending to Groq...")
                    with st.spinner("🤖 Groq is reading the syllabus and identifying modules..."):
                        result = extract_modules_with_groq(raw_text)

                    if result and result.get("modules"):
                        st.session_state.cm_extracted_course = result
                        st.session_state.cm_step = 2
                        st.success(f"✅ Found {len(result['modules'])} modules!")
                        st.rerun()
                    else:
                        st.error("Groq could not identify modules. Check that your PDF has clear module headings.")

        else:
            # No file yet — show expected format
            st.divider()
            st.markdown("**📌 Your PDF should look like this:**")
            st.code("""
Course: Data Science Bootcamp

Module 1: Python Basics (Week 1-2)
  Topics: variables, loops, functions, OOP
  Tools: Python 3, Jupyter Notebook

Module 2: Pandas & Data Analysis (Week 3-4)
  Topics: DataFrames, cleaning, groupby, merging
  Tools: Python, Pandas, NumPy, Matplotlib

Module 3: Machine Learning (Week 5-6)
  Topics: regression, classification, evaluation
  Tools: Python, Scikit-learn, Pandas
            """, language="text")

    # ════════════════════════════════
    # STEP 2 — Review Modules + Confirm
    # ════════════════════════════════
    elif step == 2:
        result = st.session_state.get("cm_extracted_course", {})
        course_name = result.get("course_name", "Unknown Course")
        modules = result.get("modules", [])

        st.subheader("📋 Review Extracted Modules")
        st.caption("Groq identified these modules from your syllabus — review before saving")

        # Editable course name
        course_name_input = st.text_input(
            "Course Name (edit if needed)",
            value=course_name,
            key="course_name_input"
        )

        st.markdown(f"**{len(modules)} modules found:**")
        st.markdown(" ")

        # Display each module as a card
        for i, mod in enumerate(modules):
            with st.expander(f"📘 {mod.get('name', f'Module {i+1}')} — {mod.get('week', '')}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Topics:**")
                    for t in mod.get("topics", []):
                        st.markdown(f"• {t}")
                with c2:
                    st.markdown("**Tools/Libraries:**")
                    for t in mod.get("tools", []):
                        st.markdown(f"🛠 {t}")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm & Save Course",
                         type="primary", use_container_width=True,
                         key="confirm_save_btn"):
                with st.spinner("Saving course..."):
                    # Update course name if edited
                    result["course_name"] = course_name_input.strip() or course_name
                    code = save_course(result["course_name"], modules)
                    st.session_state.cm_generated_code = code
                    st.session_state.cm_confirmed_name = result["course_name"]
                    st.session_state.cm_step = 3
                st.rerun()

        with col2:
            if st.button("🔄 Re-extract (try again)",
                         use_container_width=True, key="reextract_btn"):
                st.session_state.cm_step = 1
                st.session_state.cm_extracted_course = {}
                st.rerun()

    # ════════════════════════════════
    # STEP 3 — Course Code Ready
    # ════════════════════════════════
    elif step == 3:
        code = st.session_state.get("cm_generated_code", "")
        name = st.session_state.get("cm_confirmed_name", "Your Course")

        st.success("🎉 Course saved successfully!")
        st.markdown(" ")

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fa823122, #f7b73122);
            border: 3px solid #fa8231;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            margin: 20px 0;">
            <p style="color:#888; font-size:16px; margin:0 0 8px 0;">
                {name}
            </p>
            <h1 style="color:#fa8231; font-size:3.5rem; margin:0;
                letter-spacing:6px; font-family:monospace;">
                {code}
            </h1>
            <p style="color:#888; font-size:14px; margin:16px 0 0 0;">
                Share this code with your students
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(" ")
        st.info("""
        **What to do next:**
        - Copy the code above and send it to your students
        - Students enter this code in the **Student Portal**
        - They pick which module they completed
        - They get 3 project ideas using only that module's tools
        """)

        st.divider()

        # Show all saved courses
        all_courses = read_json("data/courses.json")
        if len(all_courses) > 1:
            st.subheader(f"📚 All Saved Courses ({len(all_courses)})")
            for c in all_courses:
                st.markdown(
                    f"<div style='background:#f8f9fa; border:1px solid #dee2e6;"
                    f"border-radius:8px; padding:10px 14px; margin-bottom:8px;'>"
                    f"<b style='color:#fa8231;'>{c.get('course_code','')}</b>"
                    f" — {c.get('course_name','')} "
                    f"<span style='color:#aaa; font-size:12px;'>"
                    f"({len(c.get('modules',[]))} modules · {c.get('created_at','')})</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown(" ")
        if st.button("➕ Add Another Course", use_container_width=True,
                     key="add_another_btn"):
            st.session_state.cm_step = 1
            st.session_state.cm_extracted_course = {}
            st.session_state.cm_generated_code = ""
            st.rerun()


# ══════════════════════════════════════════════════
# STUDENT PORTAL — FULL FLOW
# ══════════════════════════════════════════════════

def show_student_portal():
    st.markdown("""
    <div style="border-left:5px solid #43e97b;
        padding-left:20px; margin-bottom:20px;">
        <h2 style="margin:0; color:#2ecc71;">🎓 Student Portal</h2>
        <p style="margin:6px 0 0 0; color:#888; font-size:14px;">
            Enter your course code → pick your module → get 3 tailored project ideas
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Progress steps
    s_step = st.session_state.get("cm_s_step", 1)
    steps = ["1️⃣ Load Course", "2️⃣ Pick Module", "3️⃣ View Ideas"]
    cols = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, steps)):
        active = (i + 1 == s_step)
        col.markdown(
            f"<div style='text-align:center; padding:8px; border-radius:8px;"
            f"background:{'#2ecc7133' if active else '#f0f0f0'};"
            f"border:{'2px solid #2ecc71' if active else '1px solid #ddd'};"
            f"font-weight:{'bold' if active else 'normal'}; font-size:13px;'>"
            f"{label}</div>",
            unsafe_allow_html=True
        )
    st.divider()

    # ════════════════════════════════
    # STUDENT STEP 1 — Enter Code + Load Course
    # ════════════════════════════════
    if s_step == 1:
        st.subheader("🔑 Enter Your Course Code")
        st.caption("Get this code from your company or institute")

        col1, col2 = st.columns([3, 1])
        with col1:
            course_code_input = st.text_input(
                "Course Code",
                placeholder="e.g. DSB-2026",
                key="s_course_code_input"
            ).strip().upper()
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            load_btn = st.button("🔍 Load", type="primary",
                                 use_container_width=True, key="s_load_btn")

        if load_btn:
            if not course_code_input:
                st.warning("Please enter a course code first.")
            else:
                course = load_course_by_code(course_code_input)
                if course:
                    st.session_state.cm_s_course = course
                    st.session_state.cm_s_step = 2
                    st.success(f"✅ Course found: **{course.get('course_name','')}**")
                    st.rerun()
                else:
                    st.error(f"❌ No course found with code **{course_code_input}**. "
                             f"Check with your company for the correct code.")

        # Show all available codes (helpful for demo/testing)
        all_courses = read_json("data/courses.json")
        if all_courses:
            st.divider()
            st.markdown("**Available course codes (for reference):**")
            for c in all_courses:
                st.markdown(
                    f"<div style='background:#f8f9fa; border:1px solid #dee2e6;"
                    f"border-radius:8px; padding:8px 14px; margin-bottom:6px;'>"
                    f"<b style='color:#2ecc71; font-family:monospace;'>"
                    f"{c.get('course_code','')}</b>"
                    f" — {c.get('course_name','')} "
                    f"<span style='color:#aaa; font-size:12px;'>"
                    f"({len(c.get('modules',[]))} modules)</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.divider()
            st.info("No courses have been saved yet. Ask your company to upload a syllabus in Company Admin first.")

    # ════════════════════════════════
    # STUDENT STEP 2 — Pick Module
    # ════════════════════════════════
    elif s_step == 2:
        course = st.session_state.get("cm_s_course", {})
        modules = course.get("modules", [])

        st.markdown(f"""
        <div style="background:#2ecc7111; border:2px solid #2ecc71;
            border-radius:12px; padding:14px 20px; margin-bottom:16px;">
            <h3 style="margin:0; color:#2ecc71;">📚 {course.get('course_name','')}</h3>
            <p style="margin:4px 0 0 0; color:#888; font-size:13px;">
                Code: {course.get('course_code','')} &nbsp;|&nbsp;
                {len(modules)} modules total
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("📋 Which module did you complete?")
        st.caption("You will get project ideas using ONLY the tools from that module")

        # Show all modules
        for i, mod in enumerate(modules):
            tools = ", ".join(mod.get("tools", []))
            topics = ", ".join(mod.get("topics", []))
            st.markdown(
                f"<div style='background:#f8f9fa; border:1px solid #dee2e6;"
                f"border-radius:10px; padding:12px 16px; margin-bottom:8px;'>"
                f"<b>Module {i+1}: {mod.get('name','')}</b>"
                f"<span style='color:#888; font-size:12px; margin-left:8px;'>"
                f"{mod.get('week','')}</span><br>"
                f"<span style='color:#555; font-size:13px;'>Topics: {topics}</span><br>"
                f"<span style='color:#2ecc71; font-size:13px;'>🛠 Tools: {tools}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown(" ")
        module_names = [f"Module {i+1}: {m.get('name','')}" for i, m in enumerate(modules)]
        selected_label = st.selectbox(
            "Select the module you completed:",
            options=module_names,
            key="s_module_select"
        )

        selected_idx = module_names.index(selected_label)
        selected_module = modules[selected_idx]

        st.markdown(" ")
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🚀 Generate 3 Project Ideas",
                         type="primary", use_container_width=True,
                         key="s_gen_btn"):
                with st.spinner(f"🤖 Groq is creating ideas based on {selected_module.get('name','')}..."):
                    ideas = generate_ideas_for_module(selected_module)
                if ideas:
                    st.session_state.cm_s_ideas = ideas
                    st.session_state.cm_s_selected_module = selected_module
                    st.session_state.cm_s_step = 3
                    st.session_state.cm_s_expanded = None
                    st.rerun()
                else:
                    st.error("Could not generate ideas. Please try again.")
        with col2:
            if st.button("← Back", use_container_width=True, key="s_back_btn"):
                st.session_state.cm_s_step = 1
                st.session_state.cm_s_course = {}
                st.rerun()

    # ════════════════════════════════
    # STUDENT STEP 3 — View Ideas
    # ════════════════════════════════
    elif s_step == 3:
        ideas   = st.session_state.get("cm_s_ideas", [])
        module  = st.session_state.get("cm_s_selected_module", {})
        course  = st.session_state.get("cm_s_course", {})

        st.markdown(f"""
        <div style="background:#2ecc7111; border:2px solid #2ecc71;
            border-radius:12px; padding:12px 20px; margin-bottom:16px;">
            <b style="color:#2ecc71;">Ideas based on: {module.get('name','')}</b>
            <span style="color:#888; font-size:13px; margin-left:8px;">
            Tools used: {', '.join(module.get('tools',[]))}</span>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("✨ Your 3 Project Ideas")
        st.caption("Click Expand on any card to see the full day-by-day build plan")
        st.markdown(" ")

        card_colors = ["#667eea", "#f093fb", "#43e97b"]
        card_bgs    = ["#667eea11", "#f093fb11", "#43e97b11"]

        # ── 3 idea cards ──────────────────────────────────────────────
        card_cols = st.columns(3)
        for idx, (idea, col) in enumerate(zip(ideas, card_cols)):
            color = card_colors[idx]
            bg    = card_bgs[idx]
            with col:
                st.markdown(f"""
                <div style="border:2px solid {color}; border-radius:15px;
                    padding:20px; background:{bg}; min-height:200px;">
                    <span style="background:{color}33; color:{color};
                        padding:3px 10px; border-radius:20px; font-size:12px;
                        font-weight:bold;">{idea.get('difficulty','')}</span>
                    <h3 style="color:{color}; margin:12px 0 8px 0;">
                        {idea.get('title','')}</h3>
                    <p style="font-size:13px; color:#888; margin:0 0 8px 0;">
                        {idea.get('problem','')}
                    </p>
                    <p style="font-size:12px; color:#aaa; margin:0;">
                        🛠 {', '.join(idea.get('tech_stack',[])[:3])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(" ")
                is_exp = (st.session_state.get("cm_s_expanded") == idx)
                btn_lbl = "🔼 Collapse" if is_exp else "▶ Expand Idea"
                if st.button(btn_lbl, key=f"exp_{idx}", use_container_width=True):
                    st.session_state.cm_s_expanded = None if is_exp else idx
                    st.rerun()

        # ── Expanded idea detail ──────────────────────────────────────
        exp = st.session_state.get("cm_s_expanded")
        if exp is not None and exp < len(ideas):
            idea  = ideas[exp]
            color = card_colors[exp]

            st.divider()
            st.markdown(f"""
            <div style="border-left:5px solid {color}; padding-left:20px; margin-bottom:12px;">
                <h2 style="margin:0; color:{color};">{idea.get('title','')}</h2>
                <p style="margin:4px 0 0 0; color:#888; font-size:14px;">
                    {idea.get('difficulty','')} &nbsp;|&nbsp; 7 days
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Problem + Solution
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📌 Problem**")
                st.info(idea.get("problem", ""))
            with c2:
                st.markdown("**💡 Solution**")
                st.info(idea.get("solution", ""))

            # Tech stack badges
            st.markdown("**🛠 Tech Stack**")
            tech_cols = st.columns(len(idea.get("tech_stack", [])) or 1)
            for ti, tech in enumerate(idea.get("tech_stack", [])):
                tech_cols[ti].markdown(
                    f"<div style='text-align:center; background:{color}22;"
                    f"border:1px solid {color}; border-radius:8px; padding:8px;"
                    f"font-size:13px; color:{color}; font-weight:bold;'>{tech}</div>",
                    unsafe_allow_html=True
                )

            st.markdown(" ")

            # Day plan + Features
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📅 Day by Day Plan**")
                for day, task in idea.get("day_plan", {}).items():
                    st.markdown(
                        f"<div style='margin-bottom:6px;'>"
                        f"<span style='color:{color}; font-weight:bold; font-size:13px;'>"
                        f"{day}</span> — <span style='font-size:13px;'>{task}</span></div>",
                        unsafe_allow_html=True
                    )
            with c2:
                st.markdown("**✅ Core Features**")
                for f in idea.get("core_features", []):
                    st.success(f"✔ {f}")
                st.markdown("**🎁 Bonus Features**")
                for f in idea.get("bonus_features", []):
                    st.info(f"⭐ {f}")

            st.markdown("**🌟 Why Impressive**")
            st.markdown(
                f"<div style='background:{color}11; border-left:4px solid {color};"
                f"padding:12px 16px; border-radius:0 8px 8px 0; font-size:14px;'>"
                f"{idea.get('why_impressive','')}</div>",
                unsafe_allow_html=True
            )

            st.divider()

            # Action buttons
            b1, b2, b3 = st.columns(3)
            with b1:
                plan_text = idea_to_text(idea, module.get("name", ""))
                safe_title = idea.get("title","idea").replace(" ","_").lower()
                st.download_button(
                    "📥 Download Plan",
                    data=plan_text,
                    file_name=f"{safe_title}_plan.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"dl_{exp}"
                )
            with b2:
                if st.button("🔖 Save Idea", use_container_width=True, key=f"save_{exp}"):
                    saved = save_project(idea, module.get("name",""),
                                         course.get("course_code",""))
                    if saved:
                        st.success("✅ Saved! Check sidebar.")
                    else:
                        st.info("Already saved.")
                    st.rerun()
            with b3:
                if st.button("🔄 New Ideas", use_container_width=True, key="regen_ideas"):
                    st.session_state.cm_s_step = 2
                    st.session_state.cm_s_ideas = []
                    st.session_state.cm_s_expanded = None
                    st.rerun()

        st.divider()
        if st.button("← Pick Different Module", use_container_width=True, key="s_back2"):
            st.session_state.cm_s_step = 2
            st.session_state.cm_s_ideas = []
            st.session_state.cm_s_expanded = None
            st.rerun()


# ══════════════════════════════════════════════════
# MAIN — called from app.py
# ══════════════════════════════════════════════════

def show_course_module():
    ensure_data_files()

    # Init all session state keys
    defaults = {
        "cm_sub_mode":          None,
        "cm_step":              1,
        "cm_extracted_text":    "",
        "cm_pdf_name":          "",
        "cm_extracted_course":  {},
        "cm_generated_code":    "",
        "cm_confirmed_name":    "",
        "cm_s_step":            1,
        "cm_s_course":          {},
        "cm_s_selected_module": {},
        "cm_s_ideas":           [],
        "cm_s_expanded":        None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        st.title("📚 Course Module Ideas")
        st.divider()
        st.markdown("**Select your role:**")

        if st.button("🏢 Company / Admin", use_container_width=True,
                     type="primary" if st.session_state.cm_sub_mode == "company" else "secondary",
                     key="sb_company"):
            st.session_state.cm_sub_mode = "company"
            st.session_state.cm_step = 1
            st.rerun()

        st.markdown(" ")

        if st.button("🎓 Student", use_container_width=True,
                     type="primary" if st.session_state.cm_sub_mode == "student" else "secondary",
                     key="sb_student"):
            st.session_state.cm_sub_mode = "student"
            st.session_state.cm_s_step = 1
            st.rerun()

        st.divider()

        # Saved projects count
        projects = read_json("data/saved_projects.json")
        courses  = read_json("data/courses.json")
        st.metric("Courses saved", len(courses))
        st.metric("Projects saved", len(projects))

        if projects:
            st.markdown("**🔖 Saved projects:**")
            for p in projects[-3:]:  # show last 3
                st.markdown(f"• {p.get('title','')[:30]}")

        st.divider()
        if st.button("🏠 Back to Home", use_container_width=True, key="cm_home"):
            st.session_state.mode = None
            for k in list(defaults.keys()):
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # ── Page header ───────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding:20px 0 10px 0;">
        <h1>📚 Course Module Idea Generator</h1>
        <p style="font-size:16px; color:#888;">
            Company uploads syllabus → Groq extracts modules →
            student picks module → gets ideas using <b>only</b> what they learned
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # ── Role landing ──────────────────────────────────────────────────
    if st.session_state.cm_sub_mode is None:
        st.markdown("### 👋 Who are you? Select your role:")
        st.markdown(" ")
        c1, c2 = st.columns(2, gap="large")

        with c1:
            st.markdown("""
            <div style="border:2px solid #fa8231; border-radius:15px; padding:28px;
                background:linear-gradient(135deg,#fa823111,#f7b73111); min-height:220px;">
                <h2 style="color:#fa8231; margin-top:0;">🏢 Company / Admin</h2>
                <p>Upload your course syllabus PDF. Groq AI will extract all modules
                automatically. Share the course code with your students.</p>
                <ul>
                    <li>Upload PDF or paste syllabus</li>
                    <li>Groq identifies all modules</li>
                    <li>Review and confirm</li>
                    <li>Get course code to share</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(" ")
            if st.button("🏢 I am a Company / Admin", type="primary",
                         use_container_width=True, key="enter_company"):
                st.session_state.cm_sub_mode = "company"
                st.session_state.cm_step = 1
                st.rerun()

        with c2:
            st.markdown("""
            <div style="border:2px solid #43e97b; border-radius:15px; padding:28px;
                background:linear-gradient(135deg,#43e97b11,#38f9d711); min-height:220px;">
                <h2 style="color:#2ecc71; margin-top:0;">🎓 Student</h2>
                <p>Enter the course code your company gave you. Select which module
                you finished. Get 3 project ideas using only what you have learned —
                nothing from future modules.</p>
                <ul>
                    <li>Enter course code</li>
                    <li>See all course modules</li>
                    <li>Pick completed module</li>
                    <li>Get 3 matched ideas + full plan</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(" ")
            if st.button("🎓 I am a Student", type="primary",
                         use_container_width=True, key="enter_student"):
                st.session_state.cm_sub_mode = "student"
                st.session_state.cm_s_step = 1
                st.rerun()

    elif st.session_state.cm_sub_mode == "company":
        show_company_admin()

    elif st.session_state.cm_sub_mode == "student":
        show_student_portal()