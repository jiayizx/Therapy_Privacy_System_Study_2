import streamlit as st
import firebase_admin
from firebase_admin import firestore
import time
import logging

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
        db.collection("group_two_survey_three_responses").document(document_name).set(survey_document)
        logging.info("Survey Part 2 response successfully saved to Firebase Firestore.")
    except Exception as e:
        logging.error(f"Failed to save Survey Part 2 response to Firebase Firestore: {e}")


# Set page config
st.set_page_config(page_title="Post Survey Part 2")

# Ensure Prolific ID is available
if 'prolific_id' not in st.session_state or st.session_state.prolific_id == '':
    st.warning("Please go back to the main page and enter your Prolific ID.")
    st.stop()

st.title("Post Survey Part 2")

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

prior_experience_options = [
    "I've used an AI chatbot for therapy",
    "I've used an AI chatbot, but never for therapy (this is my first time)",
    "I've been to therapy with a human therapist, but not with an AI chatbot",
    "I've neither used an AI chatbot nor been to therapy",
]

prior_experience = st.radio(
    "Select your prior experience with AI chatbot or therapy:",
    options=prior_experience_options,
    index=prior_experience_options.index(st.session_state.prior_experience) if st.session_state.prior_experience in prior_experience_options else 0,
    disabled='survey_submitted' in st.session_state and st.session_state.survey_submitted
)

st.session_state.prior_experience = prior_experience

# Submit button
if st.button("Submit") and not ('survey_submitted' in st.session_state and st.session_state.survey_submitted):
    # Validate that all selections are made
    if age_range == "Select your age range":
        st.error("Please select your age range.")
    elif gender_identity == "Select your gender identity":
        st.error("Please select your gender identity.")
    elif highest_education == "Select your highest education":
        st.error("Please select your highest level of education.")
    else:
        # Collect all responses
        responses = {
            'age_range': age_range,
            'gender_identity': gender_identity,
            'highest_education': highest_education,
            'prior_experience': prior_experience,
        }
        
        # Store the responses in Firebase
        save_survey_two_response_to_firebase(st.session_state.prolific_id, responses)

        st.success("Thank you for completing the survey!")
        st.balloons()

        # Mark responses as submitted
        st.session_state.survey_submitted = True
        st.rerun()

# Optional: Display a message if the survey is already completed
if 'survey_submitted' in st.session_state and st.session_state.survey_submitted:
    st.write("You have already completed the survey. Thank you!")
