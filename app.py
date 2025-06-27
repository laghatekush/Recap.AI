import streamlit as st
import json
import os
from datetime import datetime, timedelta, date

try:
    import requests
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

st.set_page_config(page_title="Recap.AI", page_icon="📝", layout="wide")
st.title("📝 Recap.AI - Daily Work Logger")
st.write("Log your daily work and generate summaries!")

OPENROUTER_API_KEY = "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"

if 'editing_entry' not in st.session_state:
    st.session_state.editing_entry = None
if 'show_delete_confirm' not in st.session_state:
    st.session_state.show_delete_confirm = None

def save_work_to_file(work_text, entry_date=None, entry_time=None):
    if os.path.exists("data.json"):
        with open("data.json", "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = {"work_logs": []}
    else:
        data = {"work_logs": []}
    
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
    
    data["work_logs"].append(new_entry)
    
    with open("data.json", "w") as file:
        json.dump(data, file, indent=2)
    
    return True

def update_work_entry(entry_id, work_text, entry_date, entry_time):
    if not os.path.exists("data.json"):
        return False
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return False
    
    for i, log in enumerate(data["work_logs"]):
        if log["id"] == entry_id:
            data["work_logs"][i]["work"] = work_text
            data["work_logs"][i]["date"] = entry_date
            data["work_logs"][i]["time"] = entry_time
            data["work_logs"][i]["updated_timestamp"] = datetime.now().isoformat()
            
            with open("data.json", "w") as file:
                json.dump(data, file, indent=2)
            return True
    
    return False

def delete_work_entry(entry_id):
    if not os.path.exists("data.json"):
        return False
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return False
    
    data["work_logs"] = [log for log in data["work_logs"] if log["id"] != entry_id]
    
    with open("data.json", "w") as file:
        json.dump(data, file, indent=2)
    
    return True

def get_this_weeks_logs():
    if not os.path.exists("data.json"):
        return []
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
            work_logs = data.get("work_logs", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []
    
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.strftime("%Y-%m-%d")
    
    this_week_logs = []
    for log in work_logs:
        if log["date"] >= monday_str:
            this_week_logs.append(log)
    
    return this_week_logs

def get_all_logs():
    if not os.path.exists("data.json"):
        return []
    
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
            return data.get("work_logs", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def get_entry_by_id(entry_id):
    all_logs = get_all_logs()
    for log in all_logs:
        if log["id"] == entry_id:
            return log
    return None

def generate_ai_summary(weekly_logs):
    if not weekly_logs:
        return "No work logs found for this week."
    
    if not AI_AVAILABLE:
        return generate_basic_summary(weekly_logs)
    
    logs_text = ""
    for log in weekly_logs:
        logs_text += f"Date: {log['date']} at {log['time']}\nWork: {log['work']}\n\n"
    
    prompt = f"""Based on these daily work logs from this week, create a comprehensive weekly summary:

{logs_text}

You are my smart assistant and experienced email writer. Below are my daily work logs from the past week. 

Please write a concise and professional email to my manager summarizing the week’s progress. Structure the email with the following sections:

1. ✅ **Accomplishments** – What I completed or delivered.
2. ⚠️ **Challenges** – Specific problems I encountered and how I solved or addressed them.
3. 📊 **Results** – The outcome and impact of the work.
4. 🔜 **Next Week** – What I plan to focus on next week.

Tone: professional, calm, and confident — like a capable contributor updating their manager. Use bullet points where needed and keep it 200–400 words max.

Personalize the intro line (e.g. "Here’s a quick summary of my work during the week of June 24–28").

Do **not** invent tasks — only use what’s given in the logs. If something appears important, emphasize its impact.

End with a friendly closing like:  
*“Let me know if you’d like to go over anything in more detail.”*

### Example Logs:
[Insert logs here, e.g., as a bullet list or parsed JSON]"""
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://recap-ai.streamlit.app",
                "X-Title": "Recap.AI - Work Logger",
            },
            data=json.dumps({
                "model": "google/gemma-2-9b-it:free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.7
            })
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return generate_basic_summary(weekly_logs)
        
    except Exception as e:
        st.error(f"AI service error: {str(e)}")
        return generate_basic_summary(weekly_logs)

def generate_basic_summary(weekly_logs):
    if not weekly_logs:
        return "No work logs found for this week."
    
    sorted_logs = sorted(weekly_logs, key=lambda x: (x['date'], x['time']))
    
    daily_counts = {}
    for log in sorted_logs:
        date_str = log['date']
        daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
    
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
*Note: This is a basic summary. For AI-powered insights, install the requests package for API access.*
"""
    
    return summary

tab1, tab2, tab3, tab4 = st.tabs(["📝 Add Work Entry", "📊 Weekly Summary", "🛠️ Manage Entries", "📋 View All Logs"])

with tab1:
    st.header("Add Your Work Entry")
    
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
                
                with st.expander("📋 Entry Preview", expanded=True):
                    st.write(f"**Date:** {entry_date.strftime('%Y-%m-%d')}")
                    st.write(f"**Time:** {entry_time.strftime('%H:%M')}")
                    st.write(f"**Work:** {work_description}")
                    
            except Exception as e:
                st.error(f"❌ Error saving: {e}")
        else:
            st.warning("⚠️ Please write something about your work before saving!")

    st.subheader("📂 Recent Work Entries")
    all_logs = get_all_logs()
    
    if all_logs:
        recent_logs = sorted(all_logs, key=lambda x: (x['date'], x['time']), reverse=True)[:5]
        for i, log in enumerate(recent_logs):
            with st.expander(f"📅 {log['date']} at {log['time']}", expanded=(i==0)):
                st.write(log['work'])
    else:
        st.info("No work entries yet. Add your first entry above!")

with tab2:
    st.header("📊 Weekly Summary Generator")
    
    if AI_AVAILABLE:
        st.success("🤖 AI-powered summaries available!")
    else:
        st.info("📝 Basic summaries available (AI features disabled - requests library not installed)")
    
    weekly_logs = get_this_weeks_logs()
    
    if weekly_logs:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.success(f"📊 Found {len(weekly_logs)} work entries from this week!")
        
        with col2:
            week_start = datetime.now() - timedelta(days=datetime.now().weekday())
            st.info(f"Week of {week_start.strftime('%B %d, %Y')}")
        
        with st.expander("📋 This Week's Work Logs", expanded=False):
            sorted_weekly = sorted(weekly_logs, key=lambda x: (x['date'], x['time']))
            for log in sorted_weekly:
                st.write(f"**{log['date']} at {log['time']}:**")
                st.write(log['work'])
                st.divider()
        
        summary_button_text = "🚀 Generate AI Summary" if AI_AVAILABLE else "📊 Generate Basic Summary"
        
        if st.button(summary_button_text, type="primary"):
            with st.spinner("Creating your weekly summary..."):
                summary = generate_ai_summary(weekly_logs)
                
            st.subheader("📊 Your Weekly Summary")
            st.markdown(summary)
            
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

with tab3:
    st.header("🛠️ Manage Your Work Entries")
    
    all_logs = get_all_logs()
    
    if all_logs:
        st.write(f"**Total entries:** {len(all_logs)}")
        
        search_term = st.text_input("🔍 Search your work logs:", placeholder="Enter keywords to search...")
        
        if search_term:
            filtered_logs = [log for log in all_logs if search_term.lower() in log['work'].lower()]
            st.write(f"Found {len(filtered_logs)} entries matching '{search_term}'")
        else:
            filtered_logs = all_logs
        
        sorted_logs = sorted(filtered_logs, key=lambda x: (x['date'], x['time']), reverse=True)
        
        for log in sorted_logs:
            with st.expander(f"📅 {log['date']} at {log['time']} (ID: {log['id']})", expanded=False):
                
                if st.session_state.editing_entry == log['id']:
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
                    st.write(log['work'])
                    
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

with tab4:
    st.header("📋 All Work Logs")
    
    all_logs = get_all_logs()
    
    if all_logs:
        st.write(f"**Total entries:** {len(all_logs)}")
        
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
        
        filtered_logs = [
            log for log in all_logs 
            if start_date.strftime("%Y-%m-%d") <= log['date'] <= end_date.strftime("%Y-%m-%d")
        ]
        
        st.write(f"**Showing {len(filtered_logs)} entries from {start_date} to {end_date}**")
        
        search_term = st.text_input("🔍 Search within filtered results:", placeholder="Enter keywords to search...")
        
        if search_term:
            filtered_logs = [log for log in filtered_logs if search_term.lower() in log['work'].lower()]
            st.write(f"Found {len(filtered_logs)} entries matching '{search_term}'")
        
        sorted_logs = sorted(filtered_logs, key=lambda x: (x['date'], x['time']), reverse=True)
        
        for log in sorted_logs:
            with st.expander(f"📅 {log['date']} at {log['time']}", expanded=False):
                st.write(log['work'])
                if 'updated_timestamp' in log:
                    st.caption(f"Last updated: {log['updated_timestamp'][:19]}")
        
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

with st.sidebar:
    st.header("ℹ️ About Recap.AI")
    st.write("A comprehensive tool to log your daily work and generate summaries.")
    
    if AI_AVAILABLE:
        st.success("🤖 AI Features: Enabled")
    else:
        st.info("📝 Using Basic Summaries")
    
    st.subheader("📈 Your Stats")
    all_logs = get_all_logs()
    weekly_logs = get_this_weeks_logs()
    
    st.metric("Total Entries", len(all_logs))
    st.metric("This Week", len(weekly_logs))
    
    if all_logs:
        first_entry = min(all_logs, key=lambda x: x['date'])
        st.metric("Logging Since", first_entry['date'])
        
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
    if AI_AVAILABLE:
        st.write("• AI-powered summaries ✅")
    else:
        st.write("• Basic summaries")
    st.write("• Search functionality")
    st.write("• Export capabilities")
    st.write("• Date range filtering")
