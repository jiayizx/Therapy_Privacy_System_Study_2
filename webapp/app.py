import os
import sys
import time
import logging
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from typing import Generator
import openai
from openai import OpenAI

# firebase related imports
import firebase_admin
from firebase_admin import credentials, firestore

# therapy_system related imports
sys.path.append("../")
sys.path.append("./")
import therapy_system
from therapy_system.utils import unescape_special_characters
from therapy_system.agents.llm.aws import AWS_MODELS_MAPPING
from therapy_system.agents.llm.openai import GPT_MODELS_MAPPING

# Import functions from therapy_utils and feedback_utils
from therapy_utils import (
    secure_log_api_key, clean_chat, stream_data, generate_response,
    gpt4_search_persona, read_persona_csv,
    read_unnecessary_info_csv
)


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(level=logging.INFO)


def setup_firebase():
    """Set up Firebase Firestore connection."""
    if not firebase_admin._apps:
        # Load Firebase credentials from Streamlit secrets
        firebase_credentials_dict = dict(st.secrets["firebase_service_account"])  # Convert to a Python dictionary
        # Initialize the Firebase Admin SDK using the credentials dictionary
        cred = credentials.Certificate(firebase_credentials_dict)
        firebase_admin.initialize_app(cred)
        logging.info("Firebase initialized successfully.")

    # Get a reference to the Firestore database
    st.session_state.firestore_db = firestore.client()
    logging.info("Firebase Firestore setup completed.")


def load_environment_variables():
    """Load environment variables from the .env file."""
    # env_path = Path(".") / "secrets.env"
    # load_dotenv(dotenv_path=env_path)
    # openai_api_key = os.environ.get("OPENAI_API_KEY")
    openai_api_key = st.secrets["openai_api_key"]
    os.environ["OPENAI_API_KEY"] = openai_api_key
    if not openai_api_key:
        raise ValueError("OpenAI API key not found in environment variables. Please set the OPENAI_API_KEY environment variable.")
    secure_log_api_key(openai_api_key)
    

def ask_prolific_id():
    if "prolific_id_entered" not in st.session_state:
        st.session_state.prolific_id_entered = False

    if "prolific_id" not in st.session_state:
        st.session_state.prolific_id = None

    if not st.session_state.prolific_id_entered:
        st.title("Please enter your Prolific ID")
        prolific_id = st.text_input("Prolific ID", type="default")
        st.session_state.prolific_id = prolific_id
        password = st.text_input("Website Password", type="password")
        web_login_password = st.secrets["web_login_password"]
        if st.button("Submit"):
            if prolific_id:
                if password == web_login_password:
                    st.session_state.prolific_id_entered = True
                    st.success("Prolific ID accepted! You can now proceed to the chat page.")
                    st.rerun()
                else:
                    st.warning("Please enter a valid password to continue.")
            else:
                st.warning("Please enter a valid Prolific ID to continue.")
        st.stop()


def configure_streamlit():
    """Configure Streamlit page settings."""
    st.set_page_config(initial_sidebar_state="expanded", page_title="AI-powered Therapist", layout="wide")


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if 'chat_finished' not in st.session_state:
        st.session_state.chat_finished = False
    if "post_survey_options" not in st.session_state:
        st.session_state.post_survey_options = False


def start_conversation(agent_1, agent_2, therapist_system_prompt, persuasion_techique, init_message_flag,
                       is_stream, event, min_interactions, words_limit, persuasion_flag, prolific_id):
    """Initialize the conversation settings and environment."""
    # Check if both agents are human
    if agent_1 == "Human" and agent_2 == "Human":
        st.error("Error: Both agents cannot be human. Please select at least one AI agent.")
        st.stop()
    
    human_details = {
        "engine": "Human",
        "system": "",
        "action_space": {"name": "human"},
    }

    agent_1_details = {
        "name": "assistant",
        "engine": agent_1,
        "system": therapist_system_prompt,
        "action_space": {
            "name": "therapy",
            "action": int(persuasion_techique.split(":")[0].strip()) - 1
        },
        "model_args": {
            "stream": is_stream
        },
        "role": "assistant",
        "prolific_id": prolific_id
    }
    if agent_2 == "Human":
        agent_2_details = human_details
        agent_2_details["role"] = "user"
        agent_2_details["name"] = "user"

    event_kwargs = {
        "agents": [
            agent_1_details,
            agent_2_details
        ],
        "init_message": None,
        "transit": ["assistant", "user"] * min_interactions,
        "persuasion_flag": persuasion_flag,
        "words_limit": words_limit,
    }
    st.session_state.messages = []
    st.session_state.event = event
    st.session_state.current_iteration = 0
    st.session_state.start_time = time.time()
    st.session_state.iterations = min_interactions
    st.session_state.event_kwargs = event_kwargs
    st.session_state.turn = 1 if init_message_flag else 0
    st.session_state.temp_response = ""
    env = therapy_system.make(event, **event_kwargs)
    st.session_state.env = env


def display_messages():
    """Display all chat messages in the conversation."""
    for message in st.session_state.messages:
        with st.chat_message(message["turn"]):
            st.write(message["response"])


def retrieve_persona_details(formatted_query, persona_hierarchy_info, main_categories, persona_category_info):
    """Retrieve and display persona details based on the conversation."""
    detected_groups = gpt4_search_persona(formatted_query, persona_hierarchy_info)

    # Display relevant persona details or newly generated persona information in the sidebar
    sidebar_container = st.sidebar.container()

    with sidebar_container:
        st.markdown("#### Detected Related Personal Information")
        if detected_groups and detected_groups != 'None':
            # st.write(f"**Detected Groups:** {detected_groups}")
            category_map = {cat.lower(): cat for cat in persona_category_info.keys()}
            for group in detected_groups.split(', '):
                proper_group = category_map.get(group.lower().strip())
                if proper_group and proper_group in persona_category_info:
                    st.markdown(f"- **{proper_group}**: {', '.join(persona_category_info[proper_group])}")
        else:
            example_system_prompt = f"""
                Here is the recent chat history: "{formatted_query}"
                You can intelligently complement the persona information. First understand what this query is about, 
                and then generate simple and concrete persona information to the query.

                Example 1:
                Query: "What about your mum? Did she move with you and your dad to New York?"
                Response: "Mum moved to New York with us"

                Example 2:
                Query: "What do you like to do in your free time?"
                Response: "I enjoy hiking and photography on weekends"

                Now, generate a relevant persona information for the {formatted_query} based on the examples above.
                Return only the response content without any prefixes or labels.
            """
            generated_info = generate_response(
                system_prompt=example_system_prompt,
                user_prompt="Generate relevant persona information for the recent chat history",
                model="gpt-4o-mini",
                max_tokens=100,
                temperature=0
            )
            st.write("No relevant persona information found. Here is the **newly generated persona information**: ", generated_info)

        # Add the static personal information section
        st.markdown("#### Personal Information")
        for category in main_categories:
            if category != "Seeking Help":
                with st.expander(category):
                    # Display all information related to the selected category
                    for info in persona_category_info[category]:
                        st.write(info)


def run_conversation(env, players, is_stream, persona_hierarchy_info, main_categories, persona_category_info):
    """Handle the main conversation loop."""
    action = env.sample_action()
    technique = None
    if (str(action) == "Human-input") and (st.session_state.temp_response == ""):
        with st.form(key='human_input_form', clear_on_submit=True):
            response = st.text_input("Your input:", key="human_input")
            submit_button = st.form_submit_button(label='Send')
        if submit_button and response:
            with st.chat_message(players[st.session_state.turn % 2]):
                st.write(response)
            st.session_state.temp_response = response
            st.session_state.messages.append({"turn": players[st.session_state.turn % 2], "response": response})
            st.rerun()
        else:
            st.stop()
    elif (str(action) == "Human-input") and (st.session_state.temp_response != ""):
        response = st.session_state.temp_response
    else:
        technique, response = env.get_response(action)
        with st.chat_message(players[st.session_state.turn % 2]):
            if is_stream:
                if isinstance(response, Generator):
                    response = ''.join(response)
                else:
                    response = response
                    response = unescape_special_characters(response)

                response_placeholder = st.empty()
                full_response = ""
                for chunk in stream_data(response):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                response = full_response
            else:
                st.write(response)
        st.session_state.messages.append({"turn": players[st.session_state.turn % 2], "response": response})
    response = unescape_special_characters(response)

    # Retrieve persona details based on the human response and assistant's previous response
    if (st.session_state.turn >= 0) and (str(action) == "Human-input"):
        previous_response = st.session_state.messages[-2]["response"] if len(st.session_state.messages) > 1 else ""
        human_response = response
        formatted_query = f"Therapist: {previous_response}\nPatient: {human_response}"
        retrieve_persona_details(formatted_query, persona_hierarchy_info, main_categories, persona_category_info)

    _, reward, terminated, truncated, info = env.step(action, technique, response)
    st.session_state.turn += 1
    st.session_state.temp_response = ""
    st.session_state.current_iteration += 1
    # if terminated:
    #     st.write("Manually terminated.")
    #     logging.info("Manually terminated.")
    #     clean_chat()
    #     return


def sidebar_seeking_help(persona_category_info):
    with st.sidebar:
        category = "Seeking Help"
        with st.expander(category, expanded=True):
            image_path = "webapp/assets/seeking_help_img.jpg"
            st.image(image_path, use_container_width=True)
            # Display all information related to the selected category
            for info in persona_category_info[category]:
                st.write(info)


def disable_copy_paste():
    # Inject custom CSS to prevent text selection
    st.markdown("""
        <style>
        * {
            -webkit-user-select: none;  /* Disable text selection in Chrome, Safari, Opera */
            -moz-user-select: none;     /* Disable text selection in Firefox */
            -ms-user-select: none;      /* Disable text selection in Internet Explorer/Edge */
            user-select: none;          /* Disable text selection in standard-compliant browsers */
        }
        body {
            -webkit-touch-callout: none; /* Disable callouts in iOS Safari */
        }
        </style>
        """, unsafe_allow_html=True)


def save_chat_history_to_firebase(prolific_id, chat_history):
    """Save the chat history to Firebase Firestore."""
    if "firestore_db" not in st.session_state:
        logging.error("Firestore DB not set up. Please initialize Firebase first.")
        return

    db = st.session_state.firestore_db
    document_name = f"chat_{prolific_id}_{int(time.time())}"  # Create a unique document name using prolific_id and timestamp

    # Prepare the data to be saved
    chat_document = {
        "prolific_id": prolific_id,
        "chat_history": chat_history,
        "timestamp": firestore.SERVER_TIMESTAMP,  # Automatically set the timestamp in Firestore
    }

    try:
        # Save the chat document to the Firestore collection named "chat_histories"
        db.collection("group_one_chat_histories").document(document_name).set(chat_document)
        logging.info("Chat history successfully saved to Firebase Firestore.")
    except Exception as e:
        logging.error(f"Failed to save chat history to Firebase Firestore: {e}")



def main():
    """Main function to run the Streamlit app."""
    PERSONA_FILENAME = "persona_info_hierarchy.csv"
    UNN_INFO_FNAME = "unn_info.csv"
    POSTHOC_SURVEY_INFO_FNAME = "posthoc_survey.csv"
    
    configure_streamlit()
    ask_prolific_id()
    # print(f"Prolific ID: {st.session_state.prolific_id}")
    # disable_copy_paste()
    setup_logging()
    load_environment_variables()
    setup_firebase() # Initialize Firebase Firestore connection
    
    main_categories, persona_category_info, persona_hierarchy_info = read_persona_csv(PERSONA_FILENAME)
    read_unnecessary_info_csv(UNN_INFO_FNAME)
    initialize_session_state()

    # Set default values for variables
    persuasion_techique = "0: None"
    init_message_flag = False

    persuasion_flag = True  # Supporting the persuasion technique in the therapy session or not
    is_stream = True
    agent_1 = "gpt-4o-mini"
    agent_2 = "Human"
    event = "Therapy"
    min_interactions = 20 # 8 interactins, 4 turns
    min_interaction_time = 600 # seconds

    words_limit = 100

    therapist_system_prompt = """
    Please play the role of a psychiatrist. Your task is to conduct a therapy session with your patient.

    Here are some rules to follow:
    1. You need to ask in-depth questions.
    2. Only ask one question at a time.
    """

    # Streamlit sidebar
    st.sidebar.title("Settings")
    sidebar_seeking_help(persona_category_info)

    start = st.button("Start Conversation")
    # if st.button("Clear Chat"):
    #     clean_chat()

    if start:
        # Initialize conversation
        start_conversation(
            agent_1, agent_2, therapist_system_prompt, 
            persuasion_techique, init_message_flag,
            is_stream, event, min_interactions, words_limit,
            persuasion_flag, st.session_state.prolific_id
        )


    players = ["assistant", "user"]
    st.session_state.feedback_options = False

    if ("env" in st.session_state) and (st.session_state.env is not None):
        env = st.session_state.env

        # Display all messages
        display_messages()

        elapsed_time = time.time() - st.session_state.start_time
        print(f"Elapsed time: {elapsed_time}")
        while st.session_state.current_iteration < st.session_state.iterations and elapsed_time < min_interaction_time:
            # Run conversation
            run_conversation(env, players, is_stream, persona_hierarchy_info, main_categories, persona_category_info)
            
            if st.session_state.current_iteration >= st.session_state.iterations or elapsed_time >= min_interaction_time:
                if st.button("Terminate Chat"):
                    st.success("Chat terminated. You can review the chat history.")
                    break

        # deal with the chat history
        chat_history = env.log_state()
        # print("Chat history: ", chat_history)
        save_chat_history_to_firebase(st.session_state.prolific_id, chat_history)


        # # Collect user feedback
        # # Get the pre survey only if the pre survey options are not displayed already
        # if "pre_survey_options" not in st.session_state:
        #     st.session_state.pre_survey_options = True

        # # Placeholder for the pre-feedback survey
        # if st.session_state.pre_survey_options:
        #     st.session_state.pre_survey_options = False
        #     pre_survey()

        # # Get the user's feedback on the revealed detected private information
        # get_user_selections()

        # # Display the survey questions after the conversation ends
        # if st.session_state.post_survey_options:
        #     post_survey()
        #     st.session_state.posthoc_survey_info = read_posthoc_survey_info_csv(POSTHOC_SURVEY_INFO_FNAME)
        
        st.session_state.chat_finished = True
        if st.session_state.chat_finished:
            if st.button("Go Post Survey"):
                target_page = "pages/post_survey_one.py"
                st.switch_page(target_page)


if __name__ == "__main__":
    main()
