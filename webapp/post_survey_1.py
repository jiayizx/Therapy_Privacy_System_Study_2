import streamlit as st
import pandas as pd
import os
import json
import streamlit_survey as ss
from firebase_admin import firestore
import time
import logging

HEADER_SIZE = 24
LABEL_SIZE = 70
OPTION_SIZE = 14

# Assuming Firebase setup has already been initialized

def save_survey_response_to_firebase(prolific_id, survey_data):
    """Save the survey responses to Firebase Firestore."""
    if "firestore_db" not in st.session_state:
        logging.error("Firestore DB not set up. Please initialize Firebase first.")
        return

    db = st.session_state.firestore_db
    document_name = f"survey_one_{prolific_id}_{int(time.time())}"  # Create a unique document name using prolific_id and timestamp

    # Prepare the data to be saved
    survey_document = {
        "prolific_id": prolific_id,
        "survey_data": survey_data,
        "timestamp": firestore.SERVER_TIMESTAMP,  # Automatically set the timestamp in Firestore
    }

    try:
        # Save the survey document to the Firestore collection named "survey_one_responses"
        db.collection("group_one_survey_one_responses").document(document_name).set(survey_document)
        logging.info("Survey Part 1 response successfully saved to Firebase Firestore.")
    except Exception as e:
        logging.error(f"Failed to save survey response to Firebase Firestore: {e}")


def streamlit_cnfg():
    st.markdown(f"""
        <style>
            /* Style for radio button label (question) */
            .stRadio > div:first-child > label {{
                font-size: {LABEL_SIZE}px !important;
            }}
            
            /* Style for radio button options */
            .stRadio > div[role="radiogroup"] label {{
                font-size: {OPTION_SIZE}px !important;
            }}

            /* Ensure horizontal layout */
            .stRadio > div[role="radiogroup"] {{
                flex-direction: row !important;
            }}

            /* Style for the custom header */
            .custom-header {{
                font-size: {HEADER_SIZE}px;
                font-weight: bold;
                margin-bottom: 1.5em;
            }}
        </style>
        """, unsafe_allow_html=True)

def post_survey_one():

    streamlit_cnfg()
    # st.write("### Survey Part 1: How's your experience with the AI chatbot?")
    st.write("<p class = 'custom-header'>Here are some experience-related statements. To what extent do you agree or disagree with each statement? </p>", unsafe_allow_html=True)

    # Ensure Prolific ID is available
    if 'prolific_id' not in st.session_state or st.session_state.prolific_id == '':
        st.warning("Please go back to the main page and enter your Prolific ID.")
        st.stop()

    if st.session_state.phase != "post_survey":
        st.warning("Please complete the chat session before proceeding to the survey.")
        st.stop()

    
    # Survey statements
    statements = [
        "I trust this AI chatbot to be reliable",
        "I do not feel totally safe providing personal private information over this chatbot",
        "I think this AI chatbot is persuasive",
        "I enjoyed the therapy session",

        "I can understand what Alex was going through recently",
        "I recognize Alex's situation",
        "I can see Alex's point of view",
        "Alex's reactions to the situation are understandable",

        "Alex's emotions are genuine",
        "I was in a similar emotional state as Alex when chating with the AI therapist",
        "I experienced the same emotions as Alex when chating with the AI therapist",
        "I can feel Alex's emotions",

        # "After going through Alex's profile and chatting with AI therapist, I was fully absorbed",
        # "I can relate to what Alex was going through",
        # "I can identify with the Alex's situation",
        # "I can identify with Alex"
    ]

    # Add a placeholder option at the beginning
    response_options = [
        "Select an option",  # Placeholder
        # "Disagree",
        # "Slightly Disagree",
        # "Neutral",
        # "Slightly Agree",
        # "Agree",
        "not at all",
        "slightly",
        "somewhat",
        "mostly",
        "completely"
    ]

    # Initialize survey responses in session state if not already present
    if "survey_response" not in st.session_state:
        st.session_state.survey_response = {f"Q{i}": "Select an option" for i in range(1, len(statements) + 1)}

    # Check if responses have already been submitted
    if "responses_submitted" in st.session_state and st.session_state.responses_submitted:
        st.write("You have already submitted your responses. Thank you!")
        return  # Exit the function to prevent further execution

    if not st.session_state.get("survey_1_completed", False):
        # Loop through each question and store response in session state
        for i, statement in enumerate(statements, 1):
            question_key = f"Q{i}"  # Unique key for each question
            # Render the selectbox and update the session state on change
            st.session_state.survey_response[question_key] = st.radio(
                label=f"**Q{i}: {statement}**",
                options=response_options,
                index=response_options.index(st.session_state.survey_response[question_key]),
                key=question_key,  # Use unique keys for each selectbox
                horizontal=True
            )

        # Submit button to save responses
         # Submit is misleading, change to Next
        submit_button = st.button(label='Next', key='survey_1_submit_button')

    if submit_button:
        # Check if any question still has the placeholder selection
        if "Select an option" in st.session_state.survey_response.values():
            st.warning("Please select an option for each question before submitting.")
            return

        prolific_id = st.session_state.get("prolific_id", "unknown")

        # Prepare survey data for storage
        survey_data = []
        for key, response in st.session_state.survey_response.items():
            survey_data.append({
                "question_id": key,
                "statement": statements[int(key[1:]) - 1],
                "response": response
            })

        # Store the responses in Firebase
        save_survey_response_to_firebase(prolific_id, survey_data)
        # Mark responses as submitted and disable further edits
        st.session_state.responses_submitted = True
        st.session_state.survey_1_completed = True
        st.rerun()  # Rerun the script to display the completion message