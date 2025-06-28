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

# SECURITY: Store API key in environment variable or Streamlit secrets
# Option 1: Use environment variable
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Option 2: Use Streamlit secrets (recommended for production)
if not OPENROUTER_API_KEY:
    try:
        OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
    except:
        OPENROUTER_API_KEY = None

# Option 3: Fallback to user input (development only)
if not OPENROUTER_API_KEY:
    st.warning("⚠️ OpenRouter API key not found in environment variables or secrets.")
    OPENROUTER_API_KEY = st.text_input("Enter your OpenRouter API Key:", type="password", 
                                      help="Get your API key from https://openrouter.ai/keys")

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

def test_api_key(api_key):
    """Test if the API key is valid"""
    if not api_key:
        return False, "No API key provided"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://recap-ai.streamlit.app",
        "X-Title": "Recap.AI - Work Logger"
    }
    
    # Simple test payload
    payload = {
        "model": "openai/gpt-3.5-turbo",  # Use a cheaper model for testing
        "messages": [{"role": "user", "content": "Test"}],
        "max_tokens": 5
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "API key is valid"
        elif response.status_code == 401:
            return False, "Invalid API key or authentication failed"
        elif response.status_code == 402:
            return False, "Insufficient credits or payment required"
        elif response.status_code == 429:
            return False, "Rate limit exceeded"
        else:
            return False, f"API error: {response.status_code} - {response.text}"
    
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def generate_ai_summary(weekly_logs):
    if not weekly_logs:
        return "No work logs found for this week."
    
    if not AI_AVAILABLE or not OPENROUTER_API_KEY:
        return generate_basic_summary(weekly_logs)
    
    # Test API key first
    is_valid, message = test_api_key(OPENROUTER_API_KEY)
    if not is_valid:
        st.error(f"❌ API Key Issue: {message}")
        st.info("🔄 Falling back to basic summary...")
        return generate_basic_summary(weekly_logs)
    
    logs_text = ""
    for log in weekly_logs:
        logs_text += f"Date: {log['date']} at {log['time']}\nWork: {log['work']}\n\n"
    
    prompt = f"""Based on these daily work logs from this week, create a comprehensive weekly summary:

{logs_text}

Please create a professional weekly summary that includes:

1. **Key Accomplishments**: What was completed and delivered this week
2. **Problem Solving**: Specific challenges that were addressed and resolved  
3. **Value Created**: The impact and outcomes of the work done
4. **Obstacles Faced**: Any difficulties or blockers encountered
5. **Next Week's Focus**: Suggested priorities and follow-up actions

Format the response with clear headings and bullet points where appropriate. 
Keep it professional but conversational - like you're updating your manager or team.
Aim for 200-400 words total."""
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://recap-ai.streamlit.app",
            "X-Title": "Recap.AI - Work Logger"
        }
        
        # Use a more reliable model
        payload = {
            "model": "anthropic/claude-3-haiku",  # More reliable than gpt-4.1-nano
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60  # Increased timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                st.error("❌ Unexpected API response format")
                return generate_basic_summary(weekly_logs)
        else:
            st.error(f"❌ API Error {response.status_code}: {response.text}")
            return generate_basic_summary(weekly_logs)
        
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. Please try again.")
        return generate_basic_summary(weekly_logs)
    except requests.exceptions.ConnectionError:
        st.error("❌ Connection error. Please check your internet connection.")
        return generate_basic_summary(weekly_logs)
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
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
*Note: This is a basic summary. For AI-powered insights, ensure your OpenRouter API key is properly configured.*
"""
    
    return summary

# API Key Status in Sidebar
with st.sidebar:
    st.header("🔑 API Status")
    if OPENROUTER_API_KEY:
        if st.button("🧪 Test API Key"):
            with st.spinner("Testing API key..."):
                is_valid, message = test_api_key(OPENROUTER_API_KEY)
                if is_valid:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
        
        # Show masked API key
        masked_key = OPENROUTER_API_KEY[:8] + "..." + OPENROUTER_API_KEY[-4:] if len(OPENROUTER_API_KEY) > 12 else "sk-or-v1-****"
        st.info(f"🔐 Key: {masked_key}")
    else:
        st.warning("⚠️ No API key configured")
        st.info("Add your key to environment variables or Streamlit secrets")

# Rest of your tabs remain the same...
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
    
    if AI_AVAILABLE and OPENROUTER_API_KEY:
        st.success("🤖 AI-powered summaries available!")
    else:
        st.info("📝 Basic summaries available (AI features disabled)")
    
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
        
        summary_button_text = "🚀 Generate AI Summary" if (AI_AVAILABLE and OPENROUTER_API_KEY) else "📊 Generate Basic Summary"
        
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

# ... (rest of your tabs remain unchanged)

with st.sidebar:
    st.header("ℹ️ About Recap.AI")
    st.write("A comprehensive tool to log your daily work and generate summaries.")
    
    if AI_AVAILABLE and OPENROUTER_API_KEY:
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
    
    st.subheader("🛠️ Setup Instructions")
    st.write("**For AI features:**")
    st.write("1. Get API key from openrouter.ai")
    st.write("2. Add to environment: `OPENROUTER_API_KEY=your_key`")
    st.write("3. Or add to Streamlit secrets")
    st.write("4. Restart the app")
