import os
from dotenv import load_dotenv

print("Step 1: Checking environment variables...")
load_dotenv()
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    print("✅ GROQ_API_KEY found in .env file")
else:
    print("❌ GROQ_API_KEY not found - check your .env file")

print("\nStep 2: Checking LangChain imports...")
try:
    from langchain_community.document_loaders import JSONLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_groq import ChatGroq
    print("✅ All LangChain imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")

print("\nStep 3: Checking ChromaDB...")
try:
    import chromadb
    print("✅ ChromaDB installed correctly")
except ImportError as e:
    print(f"❌ ChromaDB error: {e}")

print("\nStep 4: Checking Streamlit...")
try:
    import streamlit
    print("✅ Streamlit installed correctly")
except ImportError as e:
    print(f"❌ Streamlit error: {e}")

print("\nStep 5: Checking Pandas...")
try:
    import pandas as pd
    print("✅ Pandas installed correctly")
except ImportError as e:
    print(f"❌ Pandas error: {e}")

print("\nStep 6: Testing Groq LLM connection...")
try:
    from langchain_groq import ChatGroq
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=groq_key
    )
    response = llm.invoke("Say 'Setup successful!' in 3 words")
    print(f"✅ Groq LLM responded: {response.content}")
except Exception as e:
    print(f"❌ Groq connection error: {e}")

print("\nStep 7: Checking dataset file...")
import json
try:
    with open("data/final_interview_dataset.json") as f:
        data = json.load(f)
    print(f"✅ Dataset loaded successfully - {len(data)} questions found")
except FileNotFoundError:
    print("❌ Dataset file not found - check data/ folder")

print("\n" + "="*50)
print("ENVIRONMENT SETUP CHECK COMPLETE")
print("="*50)