# app.py - Standalone Recap.AI with Optional AI Features

import streamlit as st
import json
import os
from datetime import datetime, timedelta, date

# Try to import Google Generative AI, make it completely optional
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Set up the page
st.set_page_config(page_title="Recap.AI", page_icon="📝", layout="wide")
st.title("📝 Recap.AI - Daily Work Logger")
st.write("Log your daily work and generate summaries!")

# Your API key (only used if genai is available)
GEMINI_API_KEY = "AIzaSyDcT1zigN6J2osDvFNqNZbB_oJ_fEdTbXA"

# Initialize session state for editing
if 'editing_entry' not in st.session_state:
    st.session_state.editing_entry = None
if 'show_delete_confirm' not in st.session_state:
    st.session_state.show_delete_confirm = None

# Function to save work to JSON file
def save_work_to_file(work_text, entry_date=None, entry_time=None):
    """This function saves work to our data.json file"""
    
    # Step 1: Read existing data from file
    if os.path.exists("data.json"):
        with open("data.json", "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = {"work_logs": []}
    else:
        data = {"work_logs": []}
    
    # Step 2: Create new work entry
    if entry_date is None:
        entry_date = datetime.now().strftime("%Y-%m-%d")
    if entry_time is None:
        entry_time = datetime.now().strftime("%H:%M")
    
    new_entry = {
        "id": len(data["work_logs"]) + 1,
        "date": entry_date,
        "time": entry_time,
        "work": work_text,
        "timestamp": datetime.now().isoformat()
    }
    
    # Step 3: Add new entry to our data
    data["work_logs"].append(new_entry)
    
    # Step 4: Save back to file
    with open("data.json", "w") as file:
        json.dump(data, file, indent=2)
    
    return True

# Function to update existing entry
def update_work_entry(entry_id, work_text, entry_date, entry_time):
    """Update an existing work entry"""
    if not os.path.exists("data.json"):
        return False
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return False
    
    # Find and update the entry
    for i, log in enumerate(data["work_logs"]):
        if log["id"] == entry_id:
            data["work_logs"][i]["work"] = work_text
            data["work_logs"][i]["date"] = entry_date
            data["work_logs"][i]["time"] = entry_time
            data["work_logs"][i]["updated_timestamp"] = datetime.now().isoformat()
            
            # Save back to file
            with open("data.json", "w") as file:
                json.dump(data, file, indent=2)
            return True
    
    return False

# Function to delete entry
def delete_work_entry(entry_id):
    """Delete a work entry"""
    if not os.path.exists("data.json"):
        return False
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return False
    
    # Find and remove the entry
    data["work_logs"] = [log for log in data["work_logs"] if log["id"] != entry_id]
    
    # Save back to file
    with open("data.json", "w") as file:
        json.dump(data, file, indent=2)
    
    return True

# Function to get this week's work logs
def get_this_weeks_logs():
    """Get all work logs from this week"""
    if not os.path.exists("data.json"):
        return []
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
            work_logs = data.get("work_logs", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []
    
    # Get Monday of this week
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.strftime("%Y-%m-%d")
    
    # Filter logs from this week
    this_week_logs = []
    for log in work_logs:
        if log["date"] >= monday_str:
            this_week_logs.append(log)
    
    return this_week_logs

# Function to get all work logs
def get_all_logs():
    """Get all work logs"""
    if not os.path.exists("data.json"):
        return []
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
            return data.get("work_logs", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []

# Function to get entry by ID
def get_entry_by_id(entry_id):
    """Get a specific entry by its ID"""
    all_logs = get_all_logs()
    for log in all_logs:
        if log["id"] == entry_id:
            return log
    return None

# Function to generate AI summary using Gemini (if available)
def generate_ai_summary(weekly_logs):
    """Use Google Gemini to create a weekly summary or create a basic summary"""
    
    if not weekly_logs:
        return "No work logs found for this week."
    
    # If AI is not available, create a basic summary
    if not GENAI_AVAILABLE:
        return generate_basic_summary(weekly_logs)
    
    # Prepare the work logs text
    logs_text = ""
    for log in weekly_logs:
        logs_text += f"Date: {log['date']} at {log['time']}\nWork: {log['work']}\n\n"
    
    # Create the prompt for AI
    prompt = f"""
    Based on these daily work logs from this week, create a comprehensive weekly summary:

    {logs_text}

    Please create a professional weekly summary that includes:

    1. **Key Accomplishments**: What was completed and delivered this week
    2. **Problem Solving**: Specific challenges that were addressed and resolved  
    3. **Value Created**: The impact and outcomes of the work done
    4. **Obstacles Faced**: Any difficulties or blockers encountered
    5. **Next Week's Focus**: Suggested priorities and follow-up actions

    Format the response with clear headings and bullet points where appropriate. 
    Keep it professional but conversational - like you're updating your manager or team.
    Aim for 200-400 words total.
    """
    
    try:
        # Configure Gemini with the API key
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Create the model
        model = genai.GenerativeModel('gemini-pro')
        
        # Generate response
        response = model.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        st.error(f"AI service error: {str(e)}")
        return generate_basic_summary(weekly_logs)

# Function to generate basic summary without AI
def generate_basic_summary(weekly_logs):
    """Generate a basic summary without AI"""
    
    if not weekly_logs:
        return "No work logs found for this week."
    
    # Sort logs by date
    sorted_logs = sorted(weekly_logs, key=lambda x: (x['date'], x['time']))
    
    # Count entries per day
    daily_counts = {}
    for log in sorted_logs:
        date_str = log['date']
        daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
    
    # Create basic summary
    summary = f"""# Weekly Summary - {len(weekly_logs)} Work Entries

## 📊 Overview
- **Total Entries:** {len(weekly_logs)}
- **Days Active:** {len(daily_counts)}
- **Average Entries per Day:** {len(weekly_logs) / len(daily_counts):.1f}

## 📅 Daily Breakdown
"""
    
    for date_str, count in daily_counts.items():
        day_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %B %d")
        summary += f"- **{day_name}:** {count} {'entry' if count == 1 else 'entries'}\n"
    
    summary += "\n## 📝 Work Entries This Week\n"
    
    for log in sorted_logs:
        day_name = datetime.strptime(log['date'], "%Y-%m-%d").strftime("%A")
        summary += f"\n**{day_name} ({log['date']}) at {log['time']}:**\n"
        summary += f"{log['work']}\n"
    
    summary += f"""

## 💡 Summary Statistics
- First entry: {sorted_logs[0]['date']} at {sorted_logs[0]['time']}
- Last entry: {sorted_logs[-1]['date']} at {sorted_logs[-1]['time']}
- Most productive day: {max(daily_counts.items(), key=lambda x: x[1])[0]} ({max(daily_counts.values())} entries)

---
*Note: This is a basic summary. For AI-powered insights, install the google-generativeai package.*
"""
    
    return summary

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📝 Add Work Entry", "📊 Weekly Summary", "🛠️ Manage Entries", "📋 View All Logs"])

# TAB 1: Add Work Entry
with tab1:
    st.header("Add Your Work Entry")
    
    # Date and time selection
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        entry_date = st.date_input(
            "📅 Select Date",
            value=date.today(),
            max_value=date.today(),
            help="Choose the date for this work entry"
        )
    
    with col2:
        entry_time = st.time_input(
            "🕐 Select Time",
            value=datetime.now().time(),
            help="Choose the time for this work entry"
        )
    
    with col3:
        if entry_date < date.today():
            st.info("📅 Adding entry for past date")
        elif entry_date == date.today():
            st.success("📅 Adding entry for today")
    
    # Work description
    col1, col2 = st.columns([3, 1])
    
    with col1:
        work_description = st.text_area(
            "What did you work on?", 
            placeholder="Describe your work, accomplishments, challenges, meetings, etc...",
            height=120,
            help="Be specific about what you accomplished, any problems you solved, or challenges you faced."
        )
    
    with col2:
        st.write("**Tips for good entries:**")
        st.write("• Be specific about outcomes")
        st.write("• Mention key decisions made")
        st.write("• Note any blockers")
        st.write("• Include metrics if relevant")

    if st.button("💾 Save Work Entry", type="primary"):
        if work_description.strip():
            try:
                save_work_to_file(
                    work_description.strip(), 
                    entry_date.strftime("%Y-%m-%d"), 
                    entry_time.strftime("%H:%M")
                )
                st.success("✅ Your work entry has been saved successfully!")
                st.balloons()
                
                # Show preview of saved entry
                with st.expander("📋 Entry Preview", expanded=True):
                    st.write(f"**Date:** {entry_date.strftime('%Y-%m-%d')}")
                    st.write(f"**Time:** {entry_time.strftime('%H:%M')}")
                    st.write(f"**Work:** {work_description}")
                    
            except Exception as e:
                st.error(f"❌ Error saving: {e}")
        else:
            st.warning("⚠️ Please write something about your work before saving!")

    # Show recent work entries
    st.subheader("📂 Recent Work Entries")
    all_logs = get_all_logs()
    
    if all_logs:
        # Show last 5 entries
        recent_logs = sorted(all_logs, key=lambda x: (x['date'], x['time']), reverse=True)[:5]
        for i, log in enumerate(recent_logs):
            with st.expander(f"📅 {log['date']} at {log['time']}", expanded=(i==0)):
                st.write(log['work'])
    else:
        st.info("No work entries yet. Add your first entry above!")

# TAB 2: Weekly Summary
with tab2:
    st.header("📊 Weekly Summary Generator")
    
    # Show AI status
    if GENAI_AVAILABLE:
        st.success("🤖 AI-powered summaries available!")
    else:
        st.info("📝 Basic summaries available (AI features disabled - google-generativeai not installed)")
    
    # Get this week's logs
    weekly_logs = get_this_weeks_logs()
    
    if weekly_logs:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.success(f"📊 Found {len(weekly_logs)} work entries from this week!")
        
        with col2:
            week_start = datetime.now() - timedelta(days=datetime.now().weekday())
            st.info(f"Week of {week_start.strftime('%B %d, %Y')}")
        
        # Show what will be summarized
        with st.expander("📋 This Week's Work Logs", expanded=False):
            sorted_weekly = sorted(weekly_logs, key=lambda x: (x['date'], x['time']))
            for log in sorted_weekly:
                st.write(f"**{log['date']} at {log['time']}:**")
                st.write(log['work'])
                st.divider()
        
        # Generate summary button
        summary_button_text = "🚀 Generate AI Summary" if GENAI_AVAILABLE else "📊 Generate Basic Summary"
        
        if st.button(summary_button_text, type="primary"):
            with st.spinner("Creating your weekly summary..."):
                summary = generate_ai_summary(weekly_logs)
                
            st.subheader("📊 Your Weekly Summary")
            st.markdown(summary)
            
            # Download button for summary
            summary_with_header = f"""# Weekly Summary - Week of {week_start.strftime('%B %d, %Y')}

Generated on: {datetime.now().strftime('%Y-%m-%d at %H:%M')}

{summary}

---
Generated by Recap.AI
"""
            
            st.download_button(
                label="📥 Download Summary",
                data=summary_with_header,
                file_name=f"weekly_summary_{week_start.strftime('%Y_%m_%d')}.md",
                mime="text/markdown"
            )
    
    else:
        st.info("📝 No work entries found for this week yet.")
        st.write("💡 **Tip:** Add some work entries in the 'Add Work Entry' tab, then come back here to generate your summary.")

# TAB 3: Manage Entries
with tab3:
    st.header("🛠️ Manage Your Work Entries")
    
    all_logs = get_all_logs()
    
    if all_logs:
        st.write(f"**Total entries:** {len(all_logs)}")
        
        # Search functionality
        search_term = st.text_input("🔍 Search your work logs:", placeholder="Enter keywords to search...")
        
        # Filter logs based on search
        if search_term:
            filtered_logs = [log for log in all_logs if search_term.lower() in log['work'].lower()]
            st.write(f"Found {len(filtered_logs)} entries matching '{search_term}'")
        else:
            filtered_logs = all_logs
        
        # Sort logs by date and time (most recent first)
        sorted_logs = sorted(filtered_logs, key=lambda x: (x['date'], x['time']), reverse=True)
        
        # Display logs with edit/delete options
        for log in sorted_logs:
            with st.expander(f"📅 {log['date']} at {log['time']} (ID: {log['id']})", expanded=False):
                
                # Check if this entry is being edited
                if st.session_state.editing_entry == log['id']:
                    # Edit mode
                    st.write("✏️ **Editing Entry**")
                    
                    edit_col1, edit_col2 = st.columns([1, 1])
                    with edit_col1:
                        edit_date = st.date_input(
                            "Date", 
                            value=datetime.strptime(log['date'], "%Y-%m-%d").date(),
                            key=f"edit_date_{log['id']}"
                        )
                    with edit_col2:
                        edit_time = st.time_input(
                            "Time", 
                            value=datetime.strptime(log['time'], "%H:%M").time(),
                            key=f"edit_time_{log['id']}"
                        )
                    
                    edit_work = st.text_area(
                        "Work Description", 
                        value=log['work'],
                        height=100,
                        key=f"edit_work_{log['id']}"
                    )
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("💾 Save Changes", key=f"save_{log['id']}", type="primary"):
                            if update_work_entry(
                                log['id'], 
                                edit_work, 
                                edit_date.strftime("%Y-%m-%d"), 
                                edit_time.strftime("%H:%M")
                            ):
                                st.success("✅ Entry updated successfully!")
                                st.session_state.editing_entry = None
                                st.rerun()
                            else:
                                st.error("❌ Failed to update entry")
                    
                    with col2:
                        if st.button("❌ Cancel", key=f"cancel_{log['id']}"):
                            st.session_state.editing_entry = None
                            st.rerun()
                
                else:
                    # View mode
                    st.write(log['work'])
                    
                    # Show if entry was updated
                    if 'updated_timestamp' in log:
                        st.caption(f"Last updated: {log['updated_timestamp'][:19]}")
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("✏️ Edit", key=f"edit_{log['id']}"):
                            st.session_state.editing_entry = log['id']
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_{log['id']}"):
                            st.session_state.show_delete_confirm = log['id']
                            st.rerun()
                    
                    # Delete confirmation
                    if st.session_state.show_delete_confirm == log['id']:
                        st.warning("⚠️ Are you sure you want to delete this entry?")
                        del_col1, del_col2, del_col3 = st.columns([1, 1, 2])
                        
                        with del_col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_delete_{log['id']}", type="primary"):
                                if delete_work_entry(log['id']):
                                    st.success("✅ Entry deleted successfully!")
                                    st.session_state.show_delete_confirm = None
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete entry")
                        
                        with del_col2:
                            if st.button("❌ Cancel", key=f"cancel_delete_{log['id']}"):
                                st.session_state.show_delete_confirm = None
                                st.rerun()
    
    else:
        st.info("📝 No work entries found. Start logging your work in the 'Add Work Entry' tab!")

# TAB 4: View All Logs
with tab4:
    st.header("📋 All Work Logs")
    
    all_logs = get_all_logs()
    
    if all_logs:
        st.write(f"**Total entries:** {len(all_logs)}")
        
        # Date range filter
        col1, col2 = st.columns([1, 1])
        with col1:
            start_date = st.date_input(
                "From Date",
                value=date.today() - timedelta(days=30),
                help="Filter entries from this date onwards"
            )
        with col2:
            end_date = st.date_input(
                "To Date",
                value=date.today(),
                help="Filter entries up to this date"
            )
        
        # Filter logs by date range
        filtered_logs = [
            log for log in all_logs 
            if start_date.strftime("%Y-%m-%d") <= log['date'] <= end_date.strftime("%Y-%m-%d")
        ]
        
        st.write(f"**Showing {len(filtered_logs)} entries from {start_date} to {end_date}**")
        
        # Search within filtered results
        search_term = st.text_input("🔍 Search within filtered results:", placeholder="Enter keywords to search...")
        
        if search_term:
            filtered_logs = [log for log in filtered_logs if search_term.lower() in log['work'].lower()]
            st.write(f"Found {len(filtered_logs)} entries matching '{search_term}'")
        
        # Sort and display logs
        sorted_logs = sorted(filtered_logs, key=lambda x: (x['date'], x['time']), reverse=True)
        
        for log in sorted_logs:
            with st.expander(f"📅 {log['date']} at {log['time']}", expanded=False):
                st.write(log['work'])
                if 'updated_timestamp' in log:
                    st.caption(f"Last updated: {log['updated_timestamp'][:19]}")
        
        # Export filtered data
        if filtered_logs:
            export_data = json.dumps({"work_logs": filtered_logs}, indent=2)
            st.download_button(
                label="📤 Export Filtered Data (JSON)",
                data=export_data,
                file_name=f"recap_ai_filtered_{start_date}_{end_date}.json",
                mime="application/json"
            )
    
    else:
        st.info("📝 No work entries found. Start logging your work in the 'Add Work Entry' tab!")

# Sidebar with app info
with st.sidebar:
    st.header("ℹ️ About Recap.AI")
    st.write("A comprehensive tool to log your daily work and generate summaries.")
    
    # Show package status
    if GENAI_AVAILABLE:
        st.success("🤖 AI Features: Enabled")
    else:
        st.warning("📝 AI Features: Disabled")
        with st.expander("Enable AI Features"):
            st.code("pip install google-generativeai")
            st.write("Restart the app after installation.")
    
    st.subheader("📈 Your Stats")
    all_logs = get_all_logs()
    weekly_logs = get_this_weeks_logs()
    
    st.metric("Total Entries", len(all_logs))
    st.metric("This Week", len(weekly_logs))
    
    if all_logs:
        first_entry = min(all_logs, key=lambda x: x['date'])
        st.metric("Logging Since", first_entry['date'])
        
        # Show entries by day of week
        days_count = {}
        for log in all_logs:
            day_name = datetime.strptime(log['date'], "%Y-%m-%d").strftime("%A")
            days_count[day_name] = days_count.get(day_name, 0) + 1
        
        st.subheader("📊 Entries by Day")
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            if day in days_count:
                st.write(f"**{day}:** {days_count[day]}")
    
    st.subheader("🛠️ Features")
    st.write("• Daily work logging")
    st.write("• Date selection")
    st.write("• Edit & delete entries")
    if GENAI_AVAILABLE:
        st.write("• AI-powered summaries ✅")
    else:
        st.write("• Basic summaries")
    st.write("• Search functionality")
    st.write("• Export capabilities")
    st.write("• Date range filtering")