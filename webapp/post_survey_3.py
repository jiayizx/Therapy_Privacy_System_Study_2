import streamlit as st
import firebase_admin
from firebase_admin import firestore
import time
import logging
import webbrowser

PROLIFIC_URL = "https://app.prolific.co/submissions/complete?cc=CWU9VX3E"

# Assuming Firebase setup has already been initialized

def save_survey_two_response_to_firebase(prolific_id, responses):
    """Save the survey responses for Survey Part 2 to Firebase Firestore."""
    if "firestore_db" not in st.session_state:
        logging.error("Firestore DB not set up. Please initialize Firebase first.")
        return

    db = st.session_state.firestore_db
    document_name = f"survey_two_{prolific_id}_{int(time.time())}"  # Create a unique document name using prolific_id and timestamp

    # Prepare the data to be saved
    survey_document = {
        "prolific_id": prolific_id,
        "survey_data": responses,
        "timestamp": firestore.SERVER_TIMESTAMP,  # Automatically set the timestamp in Firestore
    }

    try:
        # Save the survey document to the Firestore collection named "survey_two_responses"
        db.collection("group_one_survey_three_responses").document(document_name).set(survey_document)
        logging.info("Survey Part 3 response successfully saved to Firebase Firestore.")
    except Exception as e:
        logging.error(f"Failed to save Survey Part 2 response to Firebase Firestore: {e}")


def update_selected_options():
    """Update the selected options based on the checkbox values."""
    # st.session_state.selected_options = [st.session_state.prior_exp_options[int(option.split("_")[1])] for option, value in st.session_state.items() if value and option.startswith('cbox_')]
    st.session_state.selected_options = [
            st.session_state.prior_exp_options[int(option.split("_")[1])] 
            for option, value in st.session_state.items() 
            if isinstance(value, bool) and value and option.startswith('cbox_')
        ]

def close_and_redirect(url=PROLIFIC_URL):
    """Close the current tab after 5 seconds."""
    webbrowser.open(url)


def post_survey_three():
    """ Main function for the post survey part 2 page. """
    # st.write("### Post Survey Part 3: Demographic Information")

    if 'survey_2_completed' not in st.session_state:
        st.warning("Please complete the second part of the survey.")
        st.stop()

    # 1. Age range
    if 'age_range' not in st.session_state:
        st.session_state.age_range = "Select your age range"

    age_range = st.selectbox(
        "Please select your age range:",
        options=[
            "Select your age range",
            "18-24",
            "25-34",
            "35-44",
            "45-54",
            "55-64",
            "65 or above",
        ],
        index=["Select your age range", "18-24", "25-34", "35-44", "45-54", "55-64", "65 or above"].index(st.session_state.age_range),
        disabled='survey_submitted' in st.session_state and st.session_state.survey_submitted
    )

    st.session_state.age_range = age_range

    # 2. Gender identity
    if 'gender_identity' not in st.session_state:
        st.session_state.gender_identity = "Select your gender identity"

    gender_identity = st.selectbox(
        "Please select your gender identity:",
        options=[
            "Select your gender identity",
            "Male",
            "Female",
            "Non-binary / Third gender",
            "Prefer not to say",
        ],
        index=["Select your gender identity", "Male", "Female", "Non-binary / Third gender", "Prefer not to say"].index(st.session_state.gender_identity),
        disabled='survey_submitted' in st.session_state and st.session_state.survey_submitted
    )

    st.session_state.gender_identity = gender_identity

    # 3. Highest education (drop-down menu)
    if 'highest_education' not in st.session_state:
        st.session_state.highest_education = "Select your highest education"

    education_levels = [
        "Select your highest education",
        "Some school, no degree",
        "High school graduate, diploma or the equivalent (e.g. GED)",
        "Some college credit, no degree",
        "Bachelor's degree",
        "Master's degree",
        "Doctorate degree",
        "Prefer not to say",
    ]

    highest_education = st.selectbox(
        "What is your highest level of education?", 
        options=education_levels,
        index=education_levels.index(st.session_state.highest_education),
        disabled='survey_submitted' in st.session_state and st.session_state.survey_submitted
    )

    st.session_state.highest_education = highest_education

    # 4. Prior experience with AI chatbot or therapy
    if 'prior_experience' not in st.session_state:
        st.session_state.prior_experience = ""

    prior_experience_options = [ # "Select an option",
        "I've used an AI chatbot for therapy",
        "I've used an AI chatbot, but never for therapy (this is my first time)",
        "I've been to therapy with a human therapist, but not with an AI chatbot",
        "I've neither used an AI chatbot nor been to therapy",
    ]

    # Multiple choice selection
    st.write("Select your prior experience with AI chatbot or therapy:")
    st.session_state.prior_exp_options = prior_experience_options
    for indx, option in enumerate(prior_experience_options):
        st.checkbox(option, key=f'cbox_{indx}',on_change=update_selected_options,
                    disabled=st.session_state.get("survey_submitted", False))

    # Submit button
    if st.button("Submit", disabled=st.session_state.get("survey_submitted", False)) and not ('survey_submitted' in st.session_state and st.session_state.survey_submitted):
        # Validate that all selections are made
        if age_range == "Select your age range":
            st.error("Please select your age range.")
        elif gender_identity == "Select your gender identity":
            st.error("Please select your gender identity.")
        elif highest_education == "Select your highest education":
            st.error("Please select your highest level of education.")
        elif len(st.session_state.get("selected_options", [])) == 0:
            st.error("Please select your prior experience with AI chatbot or therapy.")
        else:
            # Collect all responses
            responses = {
                'age_range': age_range,
                'gender_identity': gender_identity,
                'highest_education': highest_education,
                'prior_experience': st.session_state.selected_options,
            }

            # Store the responses in Firebase
            save_survey_two_response_to_firebase(st.session_state.prolific_id, responses)

            st.success("Thank you for completing the survey!")
            st.balloons()

            # Mark responses as submitted
            st.session_state.survey_submitted = True
            st.session_state.survey_3_completed = True

            # Close the current tab after 5 seconds
            close_and_redirect()
            st.rerun()
