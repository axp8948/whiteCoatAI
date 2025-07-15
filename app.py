import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import base64
import os
from dotenv import load_dotenv
import google.generativeai as genai
from db import save_report, get_all_reports
from db import get_report, add_chat, get_report_stats

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

# Extract text from uploaded file using Gemini
def extract_text(file):
    if file.type == "application/pdf":
        # Read the PDF file and encode it as base64
        pdf_bytes = file.getvalue()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create a prompt for Gemini to extract text from the PDF
        prompt = "Extract all text content from this PDF document. Format it clearly and preserve the structure."
        
        # Create parts with the PDF attachment
        parts = [
            {"text": prompt},
            {
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": base64_pdf
                }
            }
        ]
        
        # Send to Gemini for text extraction
        try:
            response = model.generate_content(parts)
            return response.text
        except Exception as e:
            st.error(f"Error extracting text with Gemini: {str(e)}")
            return ""
    elif file.type == "text/plain":
        text = file.read().decode("utf-8")
        return text
    else:
        return ""

# Custom CSS for styling
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stButton>button { width: 100%; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex; flex-direction: column; }
    .chat-message.user { background-color: #000000; }
    .chat-message.assistant { background-color: #000000; }
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
        with st.spinner("Extracting and analyzing with Gemini..."):
            raw_text = extract_text(uploaded_file)
        st.session_state.document_text = raw_text
        st.subheader("📄 Extracted Text Preview")
        # Replace text_area with markdown display
        with st.expander("View extracted content", expanded=True):
            st.markdown(raw_text[:3000])
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
    
    if "document_text" not in st.session_state or not st.session_state.document_text.strip():
        st.warning("Please upload and analyze a medical document first to generate graphs.")
    else:
        with st.spinner("Analyzing document and generating visualizations..."):
            # Prompt Gemini to extract structured data for visualization
            prompt = f"""
            Based on the following medical document, generate data for 5 numerical visualizations:
            1. Blood Test Results with normal ranges (bar chart)
            2. Vital Signs over time (line chart if time-series data available)
            3. Cholesterol Levels (HDL, LDL, Total) as a bar chart
            4. Key Health Metrics Comparison (numerical indicators like BMI, blood pressure, glucose levels)
            5. Lab Results Trends (if multiple dates available, show trends for key metrics)

            For each visualization, provide the data in a structured JSON format that can be easily parsed.
            Only include visualizations where relevant numerical data is actually present in the document.
            Make sure all values are numeric when possible, or explicitly marked as string values when necessary.
            
            Format your response exactly like this example:
            ```json
            {{
                "visualization1": {{
                    "title": "Blood Test Results",
                    "type": "bar", 
                    "data": [
                        {{"Test": "Hemoglobin", "Value": 14.2, "Normal Range Min": 13.5, "Normal Range Max": 17.5}},
                        {{"Test": "WBC", "Value": 7.5, "Normal Range Min": 4.5, "Normal Range Max": 11.0}}
                    ]
                }},
                "visualization2": {{
                    "title": "Vital Signs Over Time",
                    "type": "line",
                    "data": [
                        {{"Date": "2024-01-01", "Blood Pressure": 120, "Heart Rate": 72, "Temperature": 98.6}},
                        {{"Date": "2024-01-15", "Blood Pressure": 118, "Heart Rate": 75, "Temperature": 98.4}}
                    ]
                }},
                "visualization3": {{
                    "title": "Cholesterol Levels",
                    "type": "bar",
                    "data": [
                        {{"Type": "HDL", "Value": 62, "Target": 60}},
                        {{"Type": "LDL", "Value": 128, "Target": 100}},
                        {{"Type": "Total", "Value": 210, "Target": 200}}
                    ]
                }},
                "visualization4": {{
                    "title": "Key Health Metrics",
                    "type": "radar",
                    "data": [
                        {{"Metric": "BMI", "Value": 24.2, "Ideal Range": 22.5}},
                        {{"Metric": "Systolic BP", "Value": 122, "Ideal Range": 120}},
                        {{"Metric": "Diastolic BP", "Value": 78, "Ideal Range": 80}},
                        {{"Metric": "Glucose", "Value": 92, "Ideal Range": 90}}
                    ]
                }},
                "visualization5": {{
                    "title": "Lab Results Trends",
                    "type": "line",
                    "data": [
                        {{"Date": "2023-10-01", "Hemoglobin": 14.0, "Glucose": 95, "Creatinine": 0.9}},
                        {{"Date": "2024-01-15", "Hemoglobin": 14.2, "Glucose": 92, "Creatinine": 0.85}}
                    ]
                }}
            }}
            ```
            
            Return ONLY the JSON, with no additional explanation. If a particular visualization cannot be created due to lack of data, exclude it from the JSON completely.
            
            Medical document:
            {st.session_state.document_text}
            """
            
            try:
                response = model.generate_content(prompt)
                result_text = response.text
                
                # Extract the JSON part
                import json
                import re
                
                # Find JSON between triple backticks if present
                json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Otherwise just try to parse the whole response
                    json_str = result_text
                
                try:
                    visualizations = json.loads(json_str)
                    
                    # Create tabs for each visualization
                    tabs = []
                    tab_names = []
                    
                    for viz_key, viz_data in visualizations.items():
                        if "title" in viz_data and "data" in viz_data:
                            tabs.append(viz_data)
                            tab_names.append(viz_data["title"])
                    
                    if tabs:
                        st_tabs = st.tabs(tab_names)
                        
                        for i, (tab, viz) in enumerate(zip(st_tabs, tabs)):
                            with tab:
                                if viz["type"] == "bar" and viz["data"]:
                                    df = pd.DataFrame(viz["data"])
                                    
                                    # Handle data conversion for values that might be strings like '<148'
                                    # This fixes the Arrow serialization issue
                                    numeric_columns = []
                                    for col in df.columns:
                                        if col == 'Value' or 'value' in col.lower() or col.endswith('Min') or col.endswith('Max') or col.endswith('Target'):
                                            # Try to convert to numeric, coerce non-convertible values to NaN
                                            df[col] = pd.to_numeric(df[col], errors='coerce')
                                            numeric_columns.append(col)
                                    
                                    # Identify the likely x-axis column (non-numeric column or first column)
                                    x_column = None
                                    for col in df.columns:
                                        if col not in numeric_columns:
                                            x_column = col
                                            break
                                    
                                    # If no non-numeric column found, use the first column
                                    if x_column is None and len(df.columns) > 0:
                                        x_column = df.columns[0]
                                    
                                    # Find the main value column
                                    y_column = 'Value' if 'Value' in df.columns else next((col for col in df.columns if 'value' in col.lower()), None)
                                    if y_column is None and numeric_columns:
                                        y_column = numeric_columns[0]
                                    
                                    if x_column and y_column:
                                        # Create visualization with dynamically determined columns
                                        fig = px.bar(df, x=x_column, y=y_column, title=viz["title"])
                                        
                                        # Add reference lines if appropriate columns exist
                                        ref_min = next((col for col in df.columns if 'min' in col.lower() or 'low' in col.lower()), None)
                                        ref_max = next((col for col in df.columns if 'max' in col.lower() or 'high' in col.lower()), None)
                                        
                                        if ref_min:
                                            fig.add_scatter(x=df[x_column], y=df[ref_min], mode='lines', 
                                                           name='Lower Reference', line=dict(color='red', dash='dash'))
                                        
                                        if ref_max:
                                            fig.add_scatter(x=df[x_column], y=df[ref_max], mode='lines', 
                                                           name='Upper Reference', line=dict(color='red', dash='dash'))
                                        
                                        # Handle the single reference line case (like Target)
                                        ref_target = next((col for col in df.columns if 'target' in col.lower() or 'reference' in col.lower()), None)
                                        if ref_target and not (ref_min or ref_max):
                                            fig.add_scatter(x=df[x_column], y=df[ref_target], mode='lines', 
                                                           name='Target/Reference', line=dict(color='green', dash='dash'))
                                        
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.error(f"Could not determine appropriate columns for visualization. Available columns: {', '.join(df.columns)}")
                                    
                                    # Also display the raw data in a table format for clarity
                                    st.write("Raw Data:")
                                    st.write(df)
                                
                                elif viz["type"] == "line" and viz["data"]:
                                    df = pd.DataFrame(viz["data"])
                                    
                                    # Try to find date/time column
                                    date_col = None
                                    for col in df.columns:
                                        if 'date' in col.lower() or 'time' in col.lower():
                                            date_col = col
                                            # Convert to datetime if it's a string
                                            if df[col].dtype == 'object':
                                                df[col] = pd.to_datetime(df[col], errors='coerce')
                                            break
                                    
                                    # If no date column found but DataFrame has a column named 'Date'
                                    if date_col is None and 'Date' in df.columns:
                                        date_col = 'Date'
                                        if df['Date'].dtype == 'object':
                                            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                                    
                                    # Convert numeric columns, handle string values gracefully
                                    numeric_cols = []
                                    for col in df.columns:
                                        if col != date_col:  # Skip the date column
                                            df[col] = pd.to_numeric(df[col], errors='coerce')
                                            numeric_cols.append(col)
                                    
                                    if date_col and numeric_cols:
                                        fig = px.line(df, x=date_col, y=numeric_cols, title=viz["title"])
                                        st.plotly_chart(fig, use_container_width=True)
                                    elif len(df.columns) >= 2:  # Try to use first column as x and others as y if no date column
                                        x_col = df.columns[0]
                                        y_cols = df.columns[1:]
                                        fig = px.line(df, x=x_col, y=y_cols, title=viz["title"])
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.error(f"Could not create line chart. Missing appropriate columns. Available columns: {', '.join(df.columns)}")
                                    
                                    # Display raw data
                                    st.write("Raw Data:")
                                    st.write(df)
                                
                                elif viz["type"] == "table" and viz["data"]:
                                    df = pd.DataFrame(viz["data"])
                                    st.subheader(viz["title"])
                                    # Use st.write instead of st.dataframe to avoid Arrow serialization issues
                                    st.write(df)
                                
                                else:
                                    st.write("Unsupported visualization type or empty data")
                    else:
                        st.info("No visualizations could be generated from the document. The document may not contain structured medical data.")
                
                except json.JSONDecodeError as e:
                    st.error(f"Failed to parse Gemini's response as JSON: {str(e)}")
                    st.text_area("Raw response from Gemini:", value=result_text, height=300)
            
            except Exception as e:
                st.error(f"Error generating visualizations: {str(e)}")
                st.info("Try uploading a different document with more structured medical data.")


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

            # ✅ Use form for stable input+submit behavior
            with st.form("chat_form", clear_on_submit=True):
                user_input = st.text_input("Type your question here...", key="chat_input")
                submitted = st.form_submit_button("Send")

                if submitted and user_input.strip():
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

                    # ✅ Input will auto-clear because of clear_on_submit=True
                    st.rerun()


elif st.session_state.active_page == "History":
    st.header("📋 Medical History")
    
    # Add search functionality
    search_query = st.text_input("🔍 Search reports by filename or content", "")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if search_query:
            reports_list = search_reports(search_query)
            st.subheader(f"Search Results: {len(reports_list)} found")
        else:
            reports_list = get_all_reports()
            st.subheader(f"All Reports: {len(reports_list)} total")
    
    with col2:
        # Display statistics
        stats = get_report_stats()
        st.metric("Total Documents", stats["total_reports"])
    
    # No reports case
    if not reports_list:
        st.info("No medical documents found. Upload some documents to get started.")
    else:
        # Create tabs for different views
        list_tab, grid_tab, stats_tab = st.tabs(["List View", "Grid View", "Statistics"])
        
        with list_tab:
            # Display as a table with actions
            for i, report in enumerate(reports_list):
                with st.expander(f"📄 {report['filename']} - {report['uploaded_at'].strftime('%Y-%m-%d %H:%M')}"):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.caption(f"Uploaded: {report['uploaded_at'].strftime('%Y-%m-%d %H:%M')}")
                        st.markdown("**Summary:**")
                        st.markdown(report['summary'][:300] + "..." if len(report['summary']) > 300 else report['summary'])
                    
                    with col2:
                        # Action buttons
                        if st.button("📊 Analysis", key=f"analyze_{i}"):
                            # Load this report into session state and redirect to analysis
                            st.session_state.document_text = report['raw_text']
                            st.session_state.report_id = str(report['_id'])
                            st.session_state.active_page = "Analysis"
                            st.rerun()
                        
                        if st.button("💬 Chat", key=f"chat_{i}"):
                            # Load this report into session state and redirect to chat
                            st.session_state.document_text = report['raw_text']
                            st.session_state.report_id = str(report['_id'])
                            st.session_state.active_page = "Chat"
                            st.rerun()
                    
                    with col3:
                        # Download options
                        download_option = st.selectbox("Download as", 
                                                      options=["Select", "Text", "Summary", "Full Report"],
                                                      key=f"download_{i}")
                        
                        if download_option == "Text":
                            st.download_button(
                                label="Download",
                                data=report['raw_text'],
                                file_name=f"{report['filename'].split('.')[0]}_text.txt",
                                mime="text/plain",
                                key=f"dl_text_{i}"
                            )
                        elif download_option == "Summary":
                            st.download_button(
                                label="Download",
                                data=report['summary'],
                                file_name=f"{report['filename'].split('.')[0]}_summary.txt",
                                mime="text/plain",
                                key=f"dl_summary_{i}"
                            )
                        elif download_option == "Full Report":
                            import json
                            report_copy = dict(report)
                            # Convert ObjectId to string for JSON serialization
                            report_copy['_id'] = str(report_copy['_id'])
                            # Convert datetime to string
                            report_copy['uploaded_at'] = report_copy['uploaded_at'].isoformat()
                            # Convert chat history timestamps
                            for chat in report_copy.get('chat_history', []):
                                if 'timestamp' in chat:
                                    chat['timestamp'] = chat['timestamp'].isoformat()
                            
                            report_json = json.dumps(report_copy, indent=2)
                            st.download_button(
                                label="Download",
                                data=report_json,
                                file_name=f"{report['filename'].split('.')[0]}_full_report.json",
                                mime="application/json",
                                key=f"dl_full_{i}"
                            )
                    
                    # Delete option with confirmation
                    if st.checkbox("Show delete option", key=f"show_delete_{i}"):
                        delete_col1, delete_col2 = st.columns([3, 1])
                        with delete_col1:
                            st.warning("⚠️ This action cannot be undone!")
                        with delete_col2:
                            if st.button("🗑️ Delete Report", key=f"delete_{i}"):
                                delete_report(str(report['_id']))
                                st.success("Report deleted successfully!")
                                st.rerun()
        
        with grid_tab:
            # Display as a grid of cards
            num_cols = 3
            rows = [reports_list[i:i+num_cols] for i in range(0, len(reports_list), num_cols)]
            
            for row in rows:
                cols = st.columns(num_cols)
                for i, report in enumerate(row):
                    with cols[i]:
                        st.markdown(f"**{report['filename']}**")
                        st.caption(f"{report['uploaded_at'].strftime('%Y-%m-%d %H:%M')}")
                        
                        # Count number of chats
                        chat_count = len(report.get('chat_history', []))
                        
                        metrics_col1, metrics_col2 = st.columns(2)
                        with metrics_col1:
                            st.metric("Chats", chat_count)
                        with metrics_col2:
                            # Get document length
                            doc_length = len(report['raw_text'])
                            st.metric("Length", f"{doc_length//1000}K")
                        
                        if st.button("Open", key=f"grid_open_{report['_id']}"):
                            st.session_state.document_text = report['raw_text']
                            st.session_state.report_id = str(report['_id'])
                            st.session_state.active_page = "Analysis"
                            st.rerun()
        
        with stats_tab:
            st.subheader("Document Statistics")
            
            # Calculate document types
            file_extensions = {}
            for report in reports_list:
                ext = report['filename'].split('.')[-1].lower() if '.' in report['filename'] else 'unknown'
                file_extensions[ext] = file_extensions.get(ext, 0) + 1
            
            # Visualization of document types
            if file_extensions:
                import plotly.express as px
                fig = px.pie(
                    names=list(file_extensions.keys()),
                    values=list(file_extensions.values()),
                    title="Document Types"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Uploads over time
            if reports_list:
                dates = [report['uploaded_at'] for report in reports_list]
                date_df = pd.DataFrame({
                    'date': dates
                })
                date_df['date'] = pd.to_datetime(date_df['date'])
                date_df['month'] = date_df['date'].dt.strftime('%Y-%m')
                monthly_counts = date_df.groupby('month').size().reset_index(name='count')
                
                fig = px.bar(
                    monthly_counts,
                    x='month',
                    y='count',
                    title="Uploads by Month"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Most active documents (by chat interactions)
            chat_counts = []
            for report in reports_list:
                chat_counts.append({
                    'filename': report['filename'],
                    'chats': len(report.get('chat_history', [])),
                    'uploaded': report['uploaded_at']
                })
            
            if chat_counts:
                chat_df = pd.DataFrame(chat_counts)
                chat_df = chat_df.sort_values('chats', ascending=False).head(10)
                
                fig = px.bar(
                    chat_df,
                    x='filename',
                    y='chats',
                    title="Most Discussed Documents"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Option to clear all history with confirmation
    with st.expander("⚠️ Danger Zone"):
        st.warning("These actions cannot be undone!")
        if st.button("Clear All History"):
            confirm = st.checkbox("I understand this will permanently delete all reports")
            if confirm:
                import pymongo
                # Drop the collection
                client.drop_database("WhiteCoatAI")
                # Recreate the collection
                db = client["WhiteCoatAI"]
                reports = db["MedicalReports"]
                st.success("All history cleared successfully!")
                st.session_state.document_text = ""
                if "report_id" in st.session_state:
                    del st.session_state.report_id
                st.rerun()

st.markdown("---")
st.markdown("""
    <div style='text-align: center'>
        <p>This is a demo application. Always consult with your healthcare provider for medical advice.</p>
    </div>
""", unsafe_allow_html=True)
