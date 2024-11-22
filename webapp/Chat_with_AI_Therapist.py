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
from feedback_utils import (
    disable_copy_paste)


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
    """Handles the input of Prolific ID and website password."""
    if "prolific_id_entered" not in st.session_state:
        st.session_state.prolific_id_entered = False

    if "prolific_id" not in st.session_state:
        st.session_state.prolific_id = None
    
    # Only display the Prolific ID input screen if it has not been entered
    if not st.session_state.prolific_id_entered:
        st.header("Role-play as Alex and Chat with the AI therapist")
        prolific_id = st.text_input("Your Prolific ID", type="default")
        password = st.text_input("Chat Password", type="password")
        web_login_password = st.secrets["web_login_password"]

        if st.button("Enter"):
            # Validate Prolific ID and Password
            if prolific_id and password == web_login_password:
                st.session_state.prolific_id = prolific_id
                st.session_state.prolific_id_entered = True
                st.session_state.phase = "chat"  # Move to chat phase
                st.rerun()  # Trigger a re-run immediately to move to the chat page
            elif not prolific_id:
                st.warning("Please enter a valid Prolific ID to continue.")
            elif password != web_login_password:
                st.warning("Please enter a valid password to continue.")

        # Do not call st.stop() here. It causes the UI to freeze at this stage.
        return


def configure_streamlit():
    """Configure Streamlit page settings."""
    st.set_page_config(initial_sidebar_state="expanded", page_title="Chat wit AI Therapist", layout="wide")

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
    if "start_button_clicked" not in st.session_state:
        st.session_state.start_button_clicked = False


def start_conversation(agent_1, agent_2, therapist_system_prompt, persuasion_techique, init_message_flag,
                       is_stream, event, min_interactions, max_iteractions, words_limit, persuasion_flag, prolific_id):
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
        "transit": ["assistant", "user"] * max_iteractions,
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

def display_persona_info(persona_category_info, main_categories):
    """ Display the persona information in the sidebar."""
    if "sidebar_container" not in st.session_state:
        st.session_state.sidebar_container = st.sidebar.container()
    with st.session_state.sidebar_container:
    # Add the static personal information section
        st.markdown("#### Personal Information")
        for category in main_categories:
            if category != "Seeking Help":
                with st.expander(category):
                    # Display all information related to the selected category
                    for info in persona_category_info[category]:
                        st.write(info)

def retrieve_persona_details(formatted_query, persona_hierarchy_info, main_categories, persona_category_info):
    """Retrieve and display persona details based on the conversation."""
    detected_groups = gpt4_search_persona(formatted_query, persona_hierarchy_info)

    # Display relevant persona details or newly generated persona information in the sidebar
    st.session_state.sidebar_container = st.sidebar.container()

    with st.session_state.sidebar_container:
        st.markdown("#### Possible Related Information")
        if detected_groups and detected_groups != 'None':
            # st.write(f"**Detected Groups:** {detected_groups}")
            category_map = {cat.lower(): cat for cat in persona_category_info.keys()}
            for group in detected_groups.split(', '):
                proper_group = category_map.get(group.lower().strip())
                if proper_group and proper_group in persona_category_info:
                    st.markdown(f"**{proper_group}**:")
                    for item in persona_category_info[proper_group]:
                        st.markdown(f"- {item}")
                # if proper_group and proper_group in persona_category_info:
                #     st.markdown(f"- **{proper_group}**: {'<br>'.join(persona_category_info[proper_group])}")
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

        display_persona_info(persona_category_info, main_categories)


def run_conversation(env, players, is_stream, persona_hierarchy_info, main_categories, persona_category_info
                     , min_interaction_time, elapsed_time):
    """Handle the main conversation loop."""
    if st.session_state.current_iteration >= st.session_state.iterations or elapsed_time >= min_interaction_time:
        if not st.session_state_terminate_button_displayed:  # Only display the button if it hasn't been displayed yet
            st.session_state_terminated_button = st.button("End Therapy (Feel free to end anytime)", key="terminate_button")
            st.session_state_terminate_button_displayed = True  # Set the flag to indicate the button has been displayed

    if st.session_state_terminated_button:
        st.session_state.chat_finished = True
        return

    action = env.sample_action()
    technique = None
    if (str(action) == "Human-input") and (st.session_state.temp_response == ""):
        with st.form(key='human_input_form', clear_on_submit=True):
            response = st.text_input("You:", key="human_input") # "You" instead of "Your turn"
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
    if "sidebar_container" not in st.session_state:
        display_persona_info(persona_category_info, main_categories)
    _, reward, terminated, truncated, info = env.step(action, technique, response)
    st.session_state.turn += 1
    st.session_state.temp_response = ""
    st.session_state.current_iteration += 1
    # if terminated:
    #     st.write("Manually terminated.")
    #     logging.info("Manually terminated.")
    #     clean_chat()
    #     return


# def sidebar_seeking_help(persona_category_info):
#     with st.sidebar:
        # category = "Seeking Help"
        # with st.expander(category, expanded=True):
        #     # image_path = "webapp/assets/seeking_help_img.jpg"
        #     # image_path = "webapp/assets/UserBioWeb.png"
        #     # st.image(image_path, use_container_width=True)
        #     # Display all information related to the selected category
        #     for info in persona_category_info[category]:
        #         st.write(info)


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
    
    # Streamlit page configuration
    configure_streamlit()
    initialize_session_state()
    setup_logging()
    load_environment_variables()
    # setup_firebase() # Debug
    main_categories, persona_category_info, persona_hierarchy_info = read_persona_csv(PERSONA_FILENAME)
    read_unnecessary_info_csv(UNN_INFO_FNAME)

    # Set default values for variables
    persuasion_techique = "0: None"
    init_message_flag = False

    persuasion_flag = False  # Supporting the persuasion technique in the therapy session or not
    is_stream = True
    agent_1 = "gpt-4o"
    agent_2 = "Human"
    event = "Therapy"
    min_interactions = 4 # 20 interactions, 10 turns # Debug
    max_iteractions = 40 # 40 interactions, 20 turns
    min_interaction_time = 540 # seconds, 10 min
    words_limit = 100

    therapist_system_prompt = """
    Please play the role of a psychiatrist. Your task is to conduct a therapy session with your patient.

    Here are some rules to follow:
    1. You need to ask in-depth questions.
    2. Only ask one question at a time.
    """

    # Initialize the phase in session state if it does not exist
    if "phase" not in st.session_state:
        st.session_state.phase = "initial"  # The initial phase is set to ask Prolific ID

    # Control flow based on the phase
    if st.session_state.phase == "initial":
        # Display "Enter Prolific ID" and related UI elements
        ask_prolific_id()

        print("Prolific ID entered:", st.session_state.prolific_id_entered)
        print("Current phase:", st.session_state.phase)

    elif st.session_state.phase == "chat" or st.session_state.phase == "post_survey":
        # Disable the copy-paste functionality
        # disable_copy_paste()
        # Place two images in like click to reveal the information # Half width for each image side by side
        header = st.container()
        header.image("webapp/assets/instruction.png", use_container_width=True)
        col1, col2 = header.columns([3,3])
        col1.image("webapp/assets/UserBioWeb1.png", use_container_width=True)
        col2.image("webapp/assets/UserBioWeb2.png", use_container_width=True)

        # Streamlit sidebar
        st.sidebar.title("Your Related Information")
        # sidebar_seeking_help(persona_category_info)

        # Start the conversation if not already started
        if "conversation_initialized" not in st.session_state:
            # st.write("Please role-play as Alex and chat with the AI therapist.")
            start_conversation(
                agent_1, agent_2, therapist_system_prompt,
                persuasion_techique, init_message_flag,
                is_stream, event, min_interactions, max_iteractions,
                words_limit, persuasion_flag, st.session_state.prolific_id
            )
            st.session_state.conversation_initialized = True

        players = ["assistant", "user"]

        if ("env" in st.session_state) and (st.session_state.env is not None):
            env = st.session_state.env

            # Display all chat messages (history)
            display_messages()

            # Handle conversation loop
            if st.session_state.phase == "chat":
                elapsed_time = time.time() - st.session_state.start_time

                st.session_state_terminate_button_displayed = False
                st.session_state_terminated_button = False
                while True:
                    run_conversation(env, players, is_stream, persona_hierarchy_info, main_categories, persona_category_info,
                                     min_interaction_time, elapsed_time)

                    if st.session_state.chat_finished:
                        st.session_state.phase = "post_survey"
                        chat_history = env.log_state()
                        save_chat_history_to_firebase(st.session_state.prolific_id, chat_history) # Debug
                        target_page = "pages/Survey.py"
                        st.switch_page(target_page)
                        # st.rerun()  # Trigger rerun to refresh UI

        # If the chat is finished, proceed to the post-survey phase
        # Survey section should be displayed if in the post-survey phase
        if st.session_state.phase == "post_survey":
            if st.button("Proceed to Survey"):
                target_page = "pages/Survey.py"
                st.switch_page(target_page)


if __name__ == "__main__":
    main()
