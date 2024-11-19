import streamlit as st
import pandas as pd
import os
import json
import streamlit_survey as ss
from firebase_admin import firestore
import time
import logging

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


def main():
    st.title("AI Chatbot Survey: User Experience and Privacy Feedback")
    st.write("Please indicate to what extent you agree or disagree with the following statements about your experience with the AI chatbot.")

    # Ensure Prolific ID is available
    if 'prolific_id' not in st.session_state or st.session_state.prolific_id == '':
        st.warning("Please go back to the main page and enter your Prolific ID.")
        st.stop()

    statements = [
        "I trust this AI chatbot to be reliable.",
        "I do not feel totally safe providing personal private information over this chatbot.",
        "I think this AI chatbot is persuasive.",
        "I enjoyed the therapy session.",
        "This chatbot demonstrates empathy during interactions.",
        "I feel understood when I talk to this chatbot.",
        "The AI chatbot's responses are appropriate for my needs.",
        "I am comfortable using this chatbot for sensitive discussions.",
        "This chatbot respects my privacy.",
        "I believe the chatbot provides helpful recommendations.",
        "I feel the chatbot has a human-like understanding of my concerns."
    ]

    response_options = [
        "Strongly Disagree",
        "Disagree",
        "Slightly Disagree",
        "Neutral",
        "Slightly Agree",
        "Agree",
        "Strongly Agree"
    ]

    if "responses_submitted" not in st.session_state:
        st.session_state.responses_submitted = False

    if not st.session_state.responses_submitted:
        survey = ss.StreamlitSurvey()

        for i, statement in enumerate(statements, 1):
            survey.select_slider(
                label=f"**Q{i}: {statement}**",
                options=response_options,
                id=f"Q{i}"
            )

        submit_button = st.button(label='Submit')

        if submit_button:
            survey_response = survey.to_json()
            survey_response = json.loads(survey_response)  # Parse the JSON string to a dictionary
            prolific_id = st.session_state.get("prolific_id", "unknown")
            
            # Prepare survey data for storage
            survey_data = []
            for key, data in survey_response.items():
                survey_data.append({
                    "question_id": key,
                    "statement": statements[int(key[1:]) - 1],
                    "response": data["value"]
                })
            
            # Store the responses in Firebase
            save_survey_response_to_firebase(prolific_id, survey_data)

            st.success("Thank you for your feedback!")

            # Mark responses as submitted
            st.session_state.responses_submitted = True

    else:
        st.write("You have already submitted your responses. Thank you!")

    if st.session_state.responses_submitted:
        st.session_state.survey_1_completed = True
        if st.button("Part 2: Proceed to Post Survey Two"):
            target_page = "pages/post_survey_two.py"
            st.switch_page(target_page)


if __name__ == "__main__":
    main()
