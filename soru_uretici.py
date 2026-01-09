import streamlit as st
import google.generativeai as genai
import json
import os
import time

# --- SETTINGS ---
JSON_FILENAME = "remit_questions.json"

# Page Configuration
st.set_page_config(page_title="REMIT Question Generator (Gemini)", layout="centered")

st.title("⚡ REMIT Question Generator (Google Gemini)")
st.markdown("Generate Intraday/Day-ahead scenarios using Google's latest models.")

# --- API KEY INPUT ---
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

if not api_key:
    st.warning("Please enter your Google API Key in the sidebar.")
    st.info("If you don't have a key, get one for free at [Google AI Studio](https://aistudio.google.com/app/apikey).")
    st.stop()

# Configure Google Gemini
genai.configure(api_key=api_key)

# --- MODEL SELECTION & PRICING ---
st.sidebar.divider()
st.sidebar.subheader("Model Selection")

# List of models sorted by price/speed (Cheapest first)
# Structure: (Technical Name, Display Name, Details)
models_data = [
    # --- GROUP 1: FREE TIER AVAILABLE ---
    # Flash-Lite (Most Economic/Fast)
    ("gemini-2.5-flash-lite", "Gemini 2.5 Flash-Lite", "⚡ Very Fast | ✅ Free Tier Available"),
    ("gemini-2.0-flash-lite", "Gemini 2.0 Flash-Lite", "⚡ Fast | ✅ Free Tier Available"),
    
    # Flash (Balanced)
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview", "🚀 Newest Flash | ✅ Free Tier Available"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash", "🚀 New Standard | ✅ Free Tier Available"),
    ("gemini-2.0-flash", "Gemini 2.0 Flash", "🚀 Balanced | ✅ Free Tier Available"),
    ("gemini-1.5-flash", "Gemini 1.5 Flash", "🛡️ Stable/Old | ✅ Free Tier Available"),

    # Pro (Intelligent)
    ("gemini-2.5-pro", "Gemini 2.5 Pro", "🧠 Very Smart | ✅ Free Tier Available"),
    ("gemini-1.5-pro", "Gemini 1.5 Pro", "🧠 Stable Smart | ✅ Free Tier Available"),

    # --- GROUP 2: PAID TIER ONLY ---
    ("gemini-3-pro-preview", "Gemini 3 Pro Preview", "💎 Most Powerful | 💲 PAID ($2.00/1M Token)")
]

# Format function for selectbox
def format_model_option(model_tuple):
    return f"{model_tuple[1]}  —  {model_tuple[2]}"

# User selection
selected_model_tuple = st.sidebar.selectbox(
    "Select Model", 
    options=models_data,
    format_func=format_model_option,
    index=3 # Default: 'Gemini 2.5 Flash' (index 3)
)

selected_model_key = selected_model_tuple[0]

# Pricing Information
st.sidebar.info(f"""
**Selected Model:** {selected_model_tuple[1]}
**Status:** {selected_model_tuple[2]}

*Note: Models marked 'Free Tier Available' are free within daily limits. 'PAID' models do not offer a free tier.*
""")

# --- FUNCTIONS ---

def load_existing_questions():
    """Loads existing JSON file or returns an empty list."""
    if not os.path.exists(JSON_FILENAME):
        return []
    try:
        with open(JSON_FILENAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_question_to_file(question_data):
    """Appends the question to the JSON file with an incremented ID."""
    existing_data = load_existing_questions()
    
    # Determine ID (Last ID + 1)
    if existing_data:
        new_id = existing_data[-1].get("id", 0) + 1
    else:
        new_id = 1
        
    # Add ID to data
    question_data["id"] = new_id
    
    # Append and save
    existing_data.append(question_data)
    
    with open(JSON_FILENAME, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4, ensure_ascii=False)
    
    return new_id

def generate_ai_question(model_name_input):
    """Requests a JSON formatted question from Google Gemini. Retries on 429 errors."""
    
    try:
        model = genai.GenerativeModel(model_name_input)
    except Exception as e:
        st.error(f"Model initialization error: {e}")
        return None
    
    prompt = """
    You are an expert Compliance Officer in Energy Trading.
    Generate a multiple-choice question focusing on 'REMIT', 'Market Abuse', 'Insider Trading' or 'Market Manipulation'.
    
    Specific Context: Intraday and Day-Ahead Power/Gas Markets.
    Difficulty: Senior/Hard (Tricky scenarios).
    
    Output strictly in this JSON format (no markdown code blocks):
    {
        "topic": "Topic Name (e.g. Wash Trading)",
        "question": "The scenario text...",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "Option X",
        "explanation": "Detailed explanation citing REMIT principles."
    }
    """
    
    # Retry Mechanism
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Request response from Gemini
            response = model.generate_content(prompt)
            text_response = response.text
            
            # Clean up potential markdown blocks
            clean_json = text_response.replace("```json", "").replace("```", "").strip()
            
            return json.loads(clean_json)
        
        except Exception as e:
            error_str = str(e)
            # If error is 429 (Quota)
            if "429" in error_str:
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1) # Wait 5s, 10s, 15s
                    st.warning(f"⚠️ Quota limit reached (429). Waiting {wait_time} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue # Retry loop
                else:
                    st.error("❌ Quota error persists. Please wait a minute or select a different model (e.g., Flash-Lite).")
                    return None
            else:
                # Other errors (e.g., 404, 500)
                st.error(f"API Error ({model_name_input}): {e}")
                st.info("Tip: If you get a '404 not found' error, try selecting an older, more stable model like 'Gemini 1.5 Flash'.")
                return None

# --- UI INTERFACE ---

# Session State (Keep question across re-runs)
if 'current_question' not in st.session_state:
    st.session_state['current_question'] = None

# Buttons layout
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🎲 GENERATE NEW QUESTION", use_container_width=True):
        with st.spinner(f"AI ({selected_model_tuple[1]}) is designing a scenario..."):
            q_data = generate_ai_question(selected_model_key)
            if q_data:
                st.session_state['current_question'] = q_data

# Display question if exists
if st.session_state['current_question']:
    q = st.session_state['current_question']
    
    st.divider()
    st.subheader(f"Topic: {q.get('topic')}")
    
    # Question Card
    st.info(f"**Scenario:**\n\n{q.get('question')}")
    
    # Options
    st.write("**Options:**")
    for opt in q.get('options', []):
        st.code(opt, language="text")
        
    # Show Answer
    with st.expander("👀 View Correct Answer & Explanation"):
        st.success(f"**Correct Answer:** {q.get('correct_answer')}")
        st.warning(f"**Explanation:** {q.get('explanation')}")

    # Save Button (Only visible if question exists)
    with col2:
        if st.button("💾 SAVE TO DATABASE", use_container_width=True, type="primary"):
            saved_id = save_question_to_file(q)
            st.toast(f"✅ Question saved successfully! ID: {saved_id}", icon="🎉")

# --- REVIEW SAVED QUESTIONS ---
st.divider()
with st.expander("📂 Review Saved Questions"):
    saved_data = load_existing_questions()
    if saved_data:
        st.write(f"Total {len(saved_data)} questions.")
        st.json(saved_data)
        
        # Convert JSON to string
        json_str = json.dumps(saved_data, indent=4, ensure_ascii=False)
        
        # Download Button
        st.download_button(
            label="📥 Download All Questions as JSON",
            data=json_str,
            file_name="remit_questions.json",
            mime="application/json"
        )
    else:
        st.write("No questions saved yet.")
