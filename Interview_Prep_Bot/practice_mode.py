from rag import generate_practice_answer

print("="*60)
print("PRACTICE MODE — RAG PIPELINE TEST")
print("="*60)

# Test questions
test_questions = [
    "What is overfitting and how do you prevent it?",
    "Explain the difference between bagging and boosting",
    "How does an LSTM work?"
]

for question in test_questions:
    print(f"\n🎯 Question: {question}")
    print("-" * 50)
    result = generate_practice_answer(question)
    print(f"📚 Topics retrieved: {result['retrieved_topics']}")
    print(f"🔗 Top match: {result['top_match'][:60]}...")
    print(f"📊 Similarity score: {result['top_similarity']}")
    print(f"\n💬 Answer:\n{result['answer']}")
    print("="*60)