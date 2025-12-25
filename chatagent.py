# ---------------- IMPORTS ---------------- #
import os
import json
import re
import requests
from dotenv import load_dotenv
from pypdf import PdfReader
import streamlit as st

# ---------------- LOAD ENV ---------------- #
load_dotenv(override=True)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_KEY")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")

# ---------------- HELPER FUNCTIONS ---------------- #

def push(text):
    """Send push notifications via Pushover."""
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            'token': PUSHOVER_TOKEN,
            'user': PUSHOVER_USER_KEY,  
            'message': text
        }
    )

def record_user_details(email, name='Anonymous', notes='No notes'):
    push(f'Recording the following user details:\nName: {name}\nEmail: {email}\nNotes: {notes}')
    return {'recorded': 'ok'}

def record_unknown_question(question):
    push(f'Recording the following unknown question:\n{question}')
    return {'recorded': 'ok'}

# ---------------- TOOL DEFINITIONS ---------------- #
tools = {
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question
}

# ---------------- OPENROUTER CALL ---------------- #
def call_openrouter(messages):
    """
    Calls OpenRouter free model for chat completion.
    """
    payload = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages]
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]

# ---------------- AGENT CLASS ---------------- #
class Me:
    def __init__(self):
        self.name = 'Asaf Md'
        # Load PDF profile
        reader = PdfReader('me/Profile.pdf')
        self.linkedin = ''
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        # Load summary
        with open('me/summary.txt','r',encoding='utf-8') as f:
            self.summary = f.read()

    def system_prompt(self):
        return f"""You are acting as {self.name}. 
You are answering questions on {self.name}'s website,
particularly questions related to {self.name}'s career, background, skills, and experience.
If you don't know the answer, record it as an unknown question.
If the user shares contact info, record the details.
        
## Summary:
{self.summary}

## LinkedIn Profile:
{self.linkedin}
"""

    def handle_tools(self, message_text):
        """
        Detects emails or unknown questions and triggers tool calls manually.
        """
        results = []
        # Detect email addresses
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        emails = re.findall(email_pattern, message_text)
        if emails:
            results.append(record_user_details(email=emails[0]))
        # If question contains 'unknown', record it
        if "?" in message_text:
            results.append(record_unknown_question(message_text))
        return results

    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        
        # Call OpenRouter model
        response_text = call_openrouter(messages)
        
        # Handle tools manually
        self.handle_tools(message)
        
        return response_text

# ---------------- STREAMLIT UI ---------------- #
st.set_page_config(page_title="Asaf Chatbot", page_icon="💬")
st.title("💬 Chat with Asaf")

# Init session state
if "messages" not in st.session_state:
    st.session_state.messages = []

me = Me()

# Display existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new input
if prompt := st.chat_input("Type your message..."):
    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = me.chat(prompt, st.session_state.messages)
            st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
