import json
import random
import os
import pandas as pd
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

GROQ_MODEL  = "llama-3.1-8b-instant"
DATA_PATH   = "data/final_interview_dataset.json"
SCORES_PATH = "data/scores.csv"

# ── Load everything once ──────────────────────────
@st.cache_resource
def load_quiz_resources():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=512
    )
    return data, model, llm


def pick_10_questions():
    """
    Pick 10 random questions covering ALL topics.
    Ensures every topic gets at least 1 question.
    """
    data, _, _ = load_quiz_resources()

    # Group by topic
    topics = {}
    for entry in data:
        t = entry["topic"]
        if t not in topics:
            topics[t] = []
        topics[t].append(entry)

    selected = []

    # Pick at least 1 from each topic (6 topics = 6 questions)
    for topic, questions in topics.items():
        selected.append(random.choice(questions))

    # Fill remaining 4 slots randomly from all data
    remaining = [q for q in data if q not in selected]
    extra = random.sample(remaining, min(4, len(remaining)))
    selected.extend(extra)

    # Shuffle final list
    random.shuffle(selected)
    return selected[:10]


def score_answer(user_answer: str, correct_answer: str) -> float:
    """
    Compare user answer with correct answer using cosine similarity.
    Returns score from 0 to 10.
    """
    _, model, _ = load_quiz_resources()

    if not user_answer.strip():
        return 0.0

    embeddings = model.encode([user_answer, correct_answer])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

    # Convert similarity (0-1) to score (0-10)
    score = round(float(similarity) * 10, 1)
    return min(score, 10.0)


def get_feedback(
    question: str,
    user_answer: str,
    correct_answer: str,
    score: float
) -> str:
    """
    Use Groq LLM to generate detailed feedback on what was missed.
    """
    _, _, llm = load_quiz_resources()

    prompt = f"""You are an expert AI interview coach evaluating a student's answer.

Question: {question}

Student's answer: {user_answer}

Correct/Expected answer: {correct_answer}

Score given: {score}/10

Please provide feedback in this EXACT format:

SCORE: {score}/10

WHAT YOU GOT RIGHT:
- [List what the student answered correctly]

WHAT YOU MISSED:
- [List key points the student missed]

IDEAL ANSWER SUMMARY:
[2-3 sentence summary of the ideal answer]

Keep feedback concise and encouraging."""

    response = llm.invoke(prompt)
    return response.content


def save_score(topic: str, question: str, score: float):
    """Save each question score to CSV for weak area tracking later."""
    os.makedirs("data", exist_ok=True)
    new_row = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic,
        "question": question[:80],
        "score": score
    }])

    if os.path.exists(SCORES_PATH):
        df = pd.read_csv(SCORES_PATH)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(SCORES_PATH, index=False)


def get_final_report(questions: list, scores: list) -> dict:
    """Generate final quiz report with strong/weak topics."""
    topic_scores = {}

    for q, s in zip(questions, scores):
        topic = q["topic"]
        if topic not in topic_scores:
            topic_scores[topic] = []
        topic_scores[topic].append(s)

    topic_averages = {
        t: round(sum(s)/len(s), 1)
        for t, s in topic_scores.items()
    }

    strong = [t for t, avg in topic_averages.items() if avg >= 6]
    weak   = [t for t, avg in topic_averages.items() if avg < 6]
    total  = round(sum(scores), 1)

    return {
        "total_score": total,
        "max_score": len(scores) * 10,
        "percentage": round((total / (len(scores)*10)) * 100, 1),
        "topic_averages": topic_averages,
        "strong_topics": strong,
        "weak_topics": weak,
        "scores": scores
    }
