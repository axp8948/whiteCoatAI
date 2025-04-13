from pymongo import MongoClient
from datetime import datetime
import os
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load MongoDB URI from .env
load_dotenv()
MONGO_URI = os.getenv("MONGODB_URL")

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client["WhiteCoatAI"]
reports = db["MedicalReports"]

# Save a new uploaded document
def save_report(filename, raw_text, summary, parsed_results):
    doc = {
        "filename": filename,
        "raw_text": raw_text,
        "summary": summary,
        "parsed_results": parsed_results,
        "chat_history": [],
        "uploaded_at": datetime.now()
    }
    result = reports.insert_one(doc)
    return str(result.inserted_id)

# Retrieve report by ID
def get_report(report_id):
    return reports.find_one({"_id": ObjectId(report_id)})

# Add a chat message to a report
def add_chat(report_id, user_msg, bot_msg):
    chat_entry = {"user": user_msg, "bot": bot_msg, "timestamp": datetime.now()}
    reports.update_one(
        {"_id": ObjectId(report_id)},
        {"$push": {"chat_history": chat_entry}}
    )

# Get all reports (optional for history display)
def get_all_reports():
    return list(reports.find().sort("uploaded_at", -1))

# Delete a report by ID
def delete_report(report_id):
    result = reports.delete_one({"_id": ObjectId(report_id)})
    return result.deleted_count

# Update report metadata (e.g., rename file)
def update_report_metadata(report_id, metadata):
    result = reports.update_one(
        {"_id": ObjectId(report_id)},
        {"$set": metadata}
    )
    return result.modified_count

# Get report statistics
def get_report_stats():
    total_reports = reports.count_documents({})
    
    # Get the date for the most recent document
    latest_doc = reports.find_one({}, sort=[("uploaded_at", -1)])
    most_recent = latest_doc.get("uploaded_at") if latest_doc else None
    
    # Get the date for the oldest document
    oldest_doc = reports.find_one({}, sort=[("uploaded_at", 1)])
    oldest = oldest_doc.get("uploaded_at") if oldest_doc else None
    
    return {
        "total_reports": total_reports,
        "most_recent": most_recent,
        "oldest": oldest
    }

# Search reports by filename or content
def search_reports(query):
    regex_query = {"$regex": query, "$options": "i"}  # case-insensitive search
    results = reports.find({
        "$or": [
            {"filename": regex_query},
            {"raw_text": regex_query},
            {"summary": regex_query}
        ]
    }).sort("uploaded_at", -1)
    
    return list(results)
