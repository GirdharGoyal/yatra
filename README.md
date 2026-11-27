# Yatra — AI-Powered Travel Booking App

Full-stack travel booking platform (Flights, Hotels, Activities, Fake Payments, Receipts) powered by **FastAPI**, **SQLAlchemy**, **Vanilla JS**, and a **LangChain + LangGraph Agentic Assistant** with Human-in-the-Loop confirmation, Hybrid Policy RAG, and Self-Refine Trip Planning.

## Quick Start (Local)

1. **Create & activate virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure `.env`:**
   Open `.env` and add your `GEMINI_API_KEY` (or set `LLM_PROVIDER=groq` with `GROQ_API_KEY`).

4. **Run the FastAPI backend:**
   ```bash
   uvicorn backend.main:app --reload
   ```
   API docs available at: `http://127.0.0.1:8000/docs`

5. **Run the Frontend:**
   In a second terminal:
   ```bash
   python -m http.server 5500 --directory frontend
   ```
   Open `http://127.0.0.1:5500` in your browser.

6. **Run Tests:**
   ```bash
   pytest
   ```
