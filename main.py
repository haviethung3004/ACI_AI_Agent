import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
import requests
import urllib3
import json

# Using DeepSeek AI
from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain.prompts import PromptTemplate
from langchain import hub
from langchain.agents import Tool, AgentExecutor, initialize_agent, create_react_agent, AgentType
from langchain_experimental.tools.python.tool import PythonREPLTool
# from langchain_openai import ChatOpenAI

#Ignore all warnings
import warnings
warnings.filterwarnings("ignore")

#Disable SSL cerificate verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#Load DeekSeek API key in .env
load_dotenv(find_dotenv(), override=True)

#APIC credentials
APIC_IP = "192.168.1.250"
USERNAME = "admin"
PASSWORD = "12345678"

# Base URL for API
BASE_URL = f"https://{APIC_IP}/api"


# Start a session
session = requests.Session()

# 1. Authentication to get the session cookie
def login():
    url = f"{BASE_URL}/aaaLogin.json"
    payload = {
        "aaaUser": {
            "attributes": {
                "name": USERNAME,
                "pwd": PASSWORD
            }
        }
    }
    response = session.post(url, json=payload, verify=False)
    
    if response.status_code == 200:
        print("Login successful")
    else:
        print(f"Login failed: {response.status_code}")

#Create a template
template = '''
  You are an assistant for Cisco ACI. The user has asked: "{query}"
  Interpret the query, make an API call to APIC if needed, and return the result.
  Everything mention to APIC you should use APIC TOOL
'''

prompt_template = PromptTemplate.from_template(template)
prompt = hub.pull('hwchase17/react')

# Function to load supported URLs with their names from a JSON file
def load_urls(file_path='urls.json'):
    if not os.path.exists(file_path):
        return {"error": f"URLs file '{file_path}' not found."}
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Return the list of dictionaries directly
        print(data)
        return data
    except Exception as e:
        return {"error": f"Error loading URLs: {str(e)}"}


#Call tenant for testing
def apic(name: str, api_urls) -> str:
    """
    A tool to fetch data from APIC based on a user-friendly name.
    :param name: The list of Name loaded from the JSON file.
    :param api_urls: The list of API URLs loaded from the JSON file.
    :return: API response or an error message.
    :Remember that the APIC_IP always: 192.168.1.250
    """
    try:
        # Find the URL associated with the given name
        api_entry = next((entry for entry in api_urls if entry["Name"].lower() == name.lower()), None)
        
        if not api_entry:
            return f"Resource '{name}' not found in the API list."

        # Construct the full URL for the API call
        APIC_IP = '192.168.1.250'
        url = f"https://192.168.1.250{api_entry['URL']}"

        # Make the API call
        response = session.get(url, verify=False)

        # Process the response
        if response.status_code == 200:
            return response.json()  # Return the JSON data
        else:
            return f"API call failed: {response.status_code} - {response.text}"
    except Exception as e:
        return f"An error occurred during the API call: {e}"




apic_tool = Tool(
  name='APIC Tenant Tool',
  func=lambda name: apic(name=name, api_urls=load_urls('urls.json')),  # Pass `api_urls`
  description='A tool for fetching tenant data from the APIC system'
)

# Python REPL Tool (for executing Python code)
python_repl = PythonREPLTool()
python_repl_tool = Tool(
  name='Python REPL',
  func= python_repl.run,
  description='A tool for executing Python code'
)

tools = [apic_tool, python_repl_tool]

# Use BaseChatOpenAI model with the deepseek-chat model
llm = BaseChatOpenAI(
    model='deepseek-chat', 
    api_key=os.getenv('DEEPSEEK_API_KEY'), 
    openai_api_base='https://api.deepseek.com',
    max_tokens=1024
)

agent = create_react_agent(llm, tools, prompt)

# Create the agent executor
agent_executor = AgentExecutor(
  agent=agent,
  tools=tools,
  verbose=True,
  handle_parsing_errors=True,
  max_iterations=10
)


# ============================================================
# Streamlit UI
# ============================================================

# Streamlit UI setup
st.set_page_config(page_title="Cisco ACI Assistant", page_icon="🤖", layout="wide")
st.title("Cisco ACI Assistant 🤖")
st.markdown("This assistant helps you interact with the Cisco ACI system and fetch tenant or related data.")

# Login to APIC system
# Query input
st.markdown("### Ask a question about Cisco ACI")
query = st.text_input("Enter your query here", placeholder="Example: Fetch tenant details...")

# Process user input
if st.button("Run Query"):
    if query:
        st.info(f"Processing query: `{query}`")
        try:
            login()
            if session.cookies:
              st.success("Login successful")

            # Load the API URLs
            api_urls = load_urls('urls.json')

            # Execute agent
            response = agent_executor.invoke({
                'input': prompt_template.format(query=query)
            })
            st.success("Response from Cisco ACI Assistant:")
            st.write(response)
        except Exception as e:
            st.error(f"Error occurred: {str(e)}")
    else:
        st.warning("Please enter a query before clicking Run Query.")
