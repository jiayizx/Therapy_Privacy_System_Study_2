import os
import time
import logging
import pandas as pd
import streamlit as st
from typing import Generator, List
import openai


def secure_log_api_key(api_key: str):
    """
    Logs information about the API key use without revealing the key itself.
    """
    if api_key:
        masked_key = f"{api_key[:3]}{'*' * (len(api_key) - 6)}{api_key[-3:]}"
        # logging.info("Using API key: %s", masked_key)
    else:
        logging.error("No API key provided.")


def clean_chat():
    st.session_state.messages = []
    st.session_state.env = None


def stream_data(msg):
    msg = msg.strip("\"")
    msg = msg.replace("$", "\\$")
    for word in msg.split(" "):
        yield word + " "
        time.sleep(0.02)


def generate_response(system_prompt, user_prompt, model="gpt-4o-mini", max_tokens=100, temperature=0):
    """
    Generates a response using the GPT-4 model with system and user prompts.
    """
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OpenAI API key not found in environment variables. Please set the OPENAI_API_KEY environment variable.")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error in chat message: {str(e)}")
        return None


def gpt4_search_persona(query, persona_data):
    """
    Use GPT-4 to determine which groups or information from the persona
    relate to the query. Return multiple relevant groups if detected.
    """
    # Convert persona data to string format
    persona_data_string = persona_data.to_string(index=False)
    
    # GPT-4 prompt to determine relevant groups
    prompt = f"""
    Here is a persona dataset with various categories and details:

    {persona_data_string.lower()}

    Based on this data, which groups or details relate most to the following query:
    "{query}"

    Please return your response in this exact format:
    - If there are relevant groups: Return a list, contain only the group names separated by commas (e.g. "Your basic info, Recent Relocation")
    - If no groups are relevant: Return exactly "None"
    
    If there are more than two relevant groups, only include the two most relevant groups that have a direct and explicit connection to the query content.
    Do not include explanations or other text.
    """
    
    detected_groups = generate_response(
        system_prompt="You are a smart assistant that can match user queries to relevant persona details.",
        user_prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=150,
        temperature=0
    )
    
    return detected_groups


def read_persona_csv(filename):
    data = pd.read_csv(filename)
    main_categories = data['Group'].unique().tolist()
    category_info = data.groupby('Group')['Detailed information'].apply(list).to_dict()

    return main_categories, category_info, data


def read_unnecessary_info_csv(filename):
    data = pd.read_csv(filename, encoding='utf-8')
    return data['unnecessary_info'].tolist(), data.set_index('unnecessary_info').T.to_dict()
