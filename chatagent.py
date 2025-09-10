from openai import OpenAI
from dotenv import load_dotenv
import json
import requests
import os
from pypdf import PdfReader
import streamlit as st

load_dotenv(override=True)


def push(text):
    requests.post("https://api.pushover.net/1/messages.json", data={'token': os.getenv("PUSHOVER_TOKEN"),
                                                                   'user': os.getenv("PUSHOVER_USER_KEY"),  
                                                                   'message': text})
    

def record_user_details(email, name='Anonymous', notes='No notes'):
    push(f'Recording the following user details:\nName: {name}\nEmail: {email}\nNotes: {notes}')
    return {'recorded': 'ok'}

def record_unknown_question(question):
    push(f'Recording the following unknown question:\n{question}')
    return {'recorded': 'ok'}


record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


class Me:

    def __init__(self):
        self.name = 'Asaf Md'
        self.openai = OpenAI()
        reader = PdfReader('me/Profile.pdf')
        self.linkedin = ''
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open('me/summary.txt','r',encoding='utf-8') as f:
            self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    

    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
If you don't know the answer, use record_unknown_question. If the user shares contact, use record_user_details."
        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        return system_prompt
    
    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content


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
