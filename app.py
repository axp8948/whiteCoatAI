import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import pdfplumber
import os
from dotenv import load_dotenv
import google.generativeai as genai
from db import save_report
from db import get_report, add_chat

# Load .env variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Set page configuration
st.set_page_config(
    page_title="WhiteCoatAI - Medical Data Analysis",
    page_icon="👨‍⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Extract text from uploaded file
def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.type == "text/plain":
        text = file.read().decode("utf-8")
    else:
        text = ""
    return text

# Custom CSS for styling
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stButton>button { width: 100%; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex; flex-direction: column; }
    .chat-message.user { background-color: #e6f3ff; }
    .chat-message.assistant { background-color: #f0f0f0; }
    .title-text { color: #2E86C1; font-size: 2.5rem; font-weight: bold; text-align: center; margin-bottom: 1rem; position:sticky; }
    .subtitle-text { color: #566573; text-align: center; margin-bottom: 2rem; }
    .feedback-box { background-color: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    .nav-item { padding: 0.5rem 1rem; border-radius: 0.25rem; margin: 0.25rem 0; cursor: pointer; }
    .nav-item:hover { background-color: #e9ecef; }
    .nav-item.active { background-color: #2E86C1; color: white; }
    </style>
""", unsafe_allow_html=True)

# Session state init
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'active_page' not in st.session_state:
    st.session_state.active_page = "Home"
if 'document_text' not in st.session_state:
    st.session_state.document_text = ""

# Sidebar navigation
with st.sidebar:
    st.markdown('<h2 style="color: #2E86C1;">WhiteCoatAI</h2>', unsafe_allow_html=True)
    st.markdown("---")
    nav_items = {
        "Home": "🏠",
        "Upload Documents": "📁",
        "Analysis": "📊",
        "Chat": "💬",
        "History": "📋"
    }
    for item, icon in nav_items.items():
        if st.button(f"{icon} {item}", key=f"nav_{item}"):
            st.session_state.active_page = item

# Title
st.markdown('<h1 class="title-text">👨‍⚕️ WhiteCoatAI</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Your AI-powered medical data analysis assistant</p>', unsafe_allow_html=True)

# Page content
if st.session_state.active_page == "Home":
    st.markdown("""
        ## Welcome to WhiteCoatAI
        WhiteCoatAI is your intelligent medical data analysis assistant. Our platform helps you:
        - 📁 Upload and analyze medical documents
        - 📊 Visualize your test results
        - 💬 Get instant answers to your medical questions
        - 📋 Track your medical history
        Get started by uploading your medical documents or asking questions about your health.
    """)

elif st.session_state.active_page == "Upload Documents":
    st.header("📁 Upload Medical Documents")
    uploaded_file = st.file_uploader("Upload your medical documents (PDF or TXT)", type=['pdf', 'txt'], accept_multiple_files=False)
    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")
        st.info("Extracting and analyzing...")
        raw_text = extract_text(uploaded_file)
        st.session_state.document_text = raw_text
        st.subheader("📄 Extracted Text Preview")
        st.text_area("Extracted Content", value=raw_text[:3000], height=300)
        if raw_text.strip():
            st.subheader("🧠 Medical Summary (Gemini)")
            prompt = f"Summarize this medical report for a patient in simple language:\n\n{raw_text}"
            
            with st.spinner("Generating summary..."):
                response = model.generate_content(prompt)
                summary = response.text
                st.write(summary)

                # ✅ Save to MongoDB
                report_id = save_report(
                    filename=uploaded_file.name,
                    raw_text=raw_text,
                    summary=summary,
                    parsed_results={}  # You can replace this with actual parsed test data later
                )

                # Store report ID for chat use
                st.session_state.report_id = report_id


elif st.session_state.active_page == "Analysis":
    st.header("📊 Analysis Dashboard")
    tab1, tab2, tab3 = st.tabs(["Blood Test Results", "Vital Signs", "Medication History"])
    with tab1:
        blood_data = pd.DataFrame({
            'Test': ['Hemoglobin', 'WBC', 'RBC', 'Platelets', 'Glucose'],
            'Value': [14.2, 7.5, 4.8, 250, 95],
            'Normal Range Min': [13.5, 4.5, 4.5, 150, 70],
            'Normal Range Max': [17.5, 11.0, 5.5, 450, 100]
        })
        fig = px.bar(blood_data, x='Test', y='Value', title='Blood Test Results')
        fig.add_scatter(x=blood_data['Test'], y=blood_data['Normal Range Min'], mode='lines', name='Normal Range Min', line=dict(color='red', dash='dash'))
        fig.add_scatter(x=blood_data['Test'], y=blood_data['Normal Range Max'], mode='lines', name='Normal Range Max', line=dict(color='red', dash='dash'))
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        vital_data = pd.DataFrame({
            'Date': pd.date_range(start='2024-01-01', periods=5),
            'Blood Pressure': [120, 118, 122, 119, 121],
            'Heart Rate': [72, 75, 70, 73, 71],
            'Temperature': [98.6, 98.4, 98.7, 98.5, 98.6]
        })
        fig = px.line(vital_data, x='Date', y=['Blood Pressure', 'Heart Rate', 'Temperature'], title='Vital Signs Over Time')
        st.plotly_chart(fig, use_container_width=True)
    with tab3:
        med_data = pd.DataFrame({
            'Medication': ['Aspirin', 'Metformin', 'Lisinopril'],
            'Dosage': ['81mg', '500mg', '10mg'],
            'Frequency': ['Daily', 'Twice Daily', 'Daily'],
            'Start Date': ['2024-01-01', '2024-02-01', '2024-03-01']
        })
        st.dataframe(med_data, use_container_width=True)

elif st.session_state.active_page == "Chat":
    st.header("💬 Chat with WhiteCoatAI")

    if "report_id" not in st.session_state:
        st.warning("Please upload and analyze a medical document first.")
    else:
        report = get_report(st.session_state.report_id)

        if not report:
            st.error("Could not retrieve the report from the database.")
        else:
            # Load previous chat history
            for message in report.get("chat_history", []):
                with st.container():
                    st.markdown(f"""
                        <div class="chat-message user">
                            <strong>User:</strong>
                            <p>{message['user']}</p>
                        </div>
                        <div class="chat-message assistant">
                            <strong>WhiteCoatAI:</strong>
                            <p>{message['bot']}</p>
                        </div>
                    """, unsafe_allow_html=True)

            # Chat input
            user_input = st.text_input("Type your question here...", key="chat_input")

            if st.button("Send"):
                if user_input:
                    with st.spinner("Thinking..."):
                        prompt = f"""
You are an AI medical assistant. Use the following information to answer in a patient-friendly way.

--- SUMMARY ---
{report['summary']}

--- FULL REPORT ---
{report['raw_text']}

Patient's question: {user_input}

Respond in a friendly, helpful tone.
                        """
                        response = model.generate_content(prompt)
                        bot_reply = response.text

                        add_chat(st.session_state.report_id, user_input, bot_reply)
                        st.rerun()


elif st.session_state.active_page == "History":
    st.header("📋 Medical History")
    st.markdown("""
        ## Recent Documents
        - Blood Test Results (March 15, 2024)
        - Prescription (March 10, 2024)
        - Doctor's Note (March 5, 2024)

        ## Analysis History
        - Blood Test Analysis (March 15, 2024)
        - Medication Review (March 10, 2024)
        - Health Assessment (March 5, 2024)
    """)

st.markdown("---")
st.markdown("""
    <div style='text-align: center'>
        <p>This is a demo application. Always consult with your healthcare provider for medical advice.</p>
    </div>
""", unsafe_allow_html=True)
