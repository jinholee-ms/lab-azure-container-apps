from dotenv import load_dotenv
import os
from queue import Queue, Empty
import time
import threading

import streamlit as st

from agents import agents_collection, AzureInventoryAgent


load_dotenv(".env", override=True)


@st.dialog("Environment Setup")
def env_setup_dialog():
    env_azure_openai_endpoint = st.text_input("Azure OpenAI Endpoint", key="azure_openai_endpoint", value=os.getenv("AZURE_OPENAI_ENDPOINT"))
    env_azure_openai_api_key = st.text_input("Azure OpenAI API Key", type="password", key="azure_openai_api_key", value=os.getenv("AZURE_OPENAI_API_KEY"))
    env_openai_api_version = st.text_input("OpenAI API Version", key="openai_api_version", value=os.getenv("OPENAI_API_VERSION"))
    env_azure_openai_deployment = st.text_input("Azure OpenAI Deployment", key="azure_openai_deployment", value=os.getenv("AZURE_OPENAI_DEPLOYMENT"))
    env_azure_openai_model = st.text_input("Azure OpenAI Model", key="azure_openai_model", value=os.getenv("AZURE_OPENAI_MODEL"))
    if st.button("Save", width="stretch"):
        os.environ["AZURE_OPENAI_ENDPOINT"] = env_azure_openai_endpoint
        os.environ["AZURE_OPENAI_API_KEY"] = env_azure_openai_api_key
        os.environ["OPENAI_API_VERSION"] = env_openai_api_version
        os.environ["AZURE_OPENAI_DEPLOYMENT"] = env_azure_openai_deployment
        os.environ["AZURE_OPENAI_MODEL"] = env_azure_openai_model
        st.rerun()


with st.sidebar:
    st.image("resources/microsoft-logo.svg", caption="Created by Microsoft")
    
    agent_selectbox = st.selectbox(
        "Select agents",
        agents_collection.keys(),
    )
    set_environment_btn = st.button("Set Environment", width="stretch")
    reset_chat_history_btn = st.button("Reset chat history", width="stretch")


st.title("🚀 AI Agent Playground")


st.divider(width="stretch")


# Restore chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


# actionable scripts
if agent_selectbox or not agent_selectbox:
    print("Selected agents:", agent_selectbox)
    if agent_selectbox:
        focused_agent_type = agents_collection[agent_selectbox]
if set_environment_btn:
    env_setup_dialog()
if reset_chat_history_btn:
    st.session_state["messages"] = []


# azure 의 모든 resource group 들 안에 있는 모든 resources 를 보여줘
if prompt := st.chat_input():
    with st.chat_message("user"):
        st.empty().write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        content = st.empty()
        response = None
        with st.spinner("Thinking...", show_time=True):
            ui_event_queue = Queue()
            focused_agent = focused_agent_type(ui_event_queue)
            agent_thread = threading.Thread(
                target=focused_agent.entrypoint,
                args=(str(prompt),),
                daemon=True, 
            )
            
            agent_thread.start()
            while agent_thread.is_alive() or not ui_event_queue.empty():
                try:
                    ev = ui_event_queue.get(timeout=0.25)
                except Empty:
                    continue

                if ev["type"] == "response":
                    print("Received response event:", ev)
                    response = ev["data"]
            agent_thread.join()
        
        print("Final response:", response, "type:", type(response))
        if output := response.get("error"):
            st.error(f"⚠️ LLM 응답 실패: {output}")
        elif output := response.get("output"):
            content.write(output)
            st.session_state.messages.append({"role": "assistant", "content": output})
