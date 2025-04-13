# 🥼 WhiteCoatAI

An AI-powered medical analysis platform that transforms prescriptions, lab reports, and doctor's notes into simplified summaries, visual charts, and a chat-based interface using LLMs.

## 🔧 Features

- 📁 Upload support for PDF and TXT medical documents
- 🧠 LLM-powered report summarization using Google Gemini
- 📊 Automatic visualization of lab results and health metrics
- 💬 Chat interface for asking questions about uploaded reports
- 📋 Searchable report history with downloads and statistics

## ⚙️ Setup

1. Clone the repository  
2. Create a `.env` file with your API keys:

   `
   GEMINI_API_KEY=your_google_gemini_api_key  
   MONGODB_URL=your_mongodb_connection_string
   `

3. Install dependencies:  
   `pip install -r requirements.txt`

4. Run the app:  
   `streamlit run app.py`

## 🧪 Usage

- Upload your medical document through the sidebar
- View an AI-generated summary in simple language
- Explore auto-generated charts for vital signs, blood work, etc.
- Ask health-related questions based on your document
- Browse and manage previously uploaded reports

## 📁 File Structure

- `app.py` – Main Streamlit interface and logic
- `db.py` – MongoDB handlers (save, retrieve, search)
- `.env` – API keys (not tracked in git)
- `requirements.txt` – Python dependencies

## 📌 Notes

This is a prototype/demo application intended for educational and research purposes.  
**Always consult a qualified healthcare provider for medical advice.**
