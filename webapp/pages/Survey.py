import streamlit as st
from webapp.post_survey_1 import post_survey_one
from webapp.post_survey_2 import post_survey_two, prep_survey_two
from webapp.post_survey_3 import post_survey_three

def main():
    st.title("Survey")

    # Ensure Prolific ID is available
    if 'prolific_id' not in st.session_state or st.session_state.prolific_id == '':
        st.warning("Please go back to the 'Chat with AI Therapist' page and enter your Prolific ID.")
        st.stop()

    if st.session_state.phase != "post_survey":
        st.warning("Please complete the chat session before proceeding to the survey.")
        st.stop()

    # Preload the survey for the second part of the survey
    if not st.session_state.get("prep_done", False):
        prep_survey_two()

    # Check if the first survey is completed
    if 'survey_1_completed' not in st.session_state:
        post_survey_one()
    elif 'survey_2_completed' not in st.session_state:
        post_survey_two()
    elif 'survey_3_completed' not in st.session_state:
        post_survey_three()
    else:
        st.write("You have already completed the survey. Thank you!")

if __name__ == "__main__":
    main()
