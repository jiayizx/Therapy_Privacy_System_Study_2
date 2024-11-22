import streamlit as st
from webapp.post_survey_1 import post_survey_one
from webapp.post_survey_2 import post_survey_two, prep_survey_two
from webapp.post_survey_3 import close_and_redirect, post_survey_three

def style_code():
    """ CSS style for the survey page. """
    st.components.v1.html(
        """
        <style>
        st-button-prolific {
            max-width: 800px;
            margin: auto;
            padding: 20px;
            display: block;
            background-color: #4CAF50;
            border: none;
            color: white;
        }
        </style>
        """, height=0
    )


def main():
    """ Main function for the survey page. """
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
        st.write("You have already completed the survey.")
        style_code()
        if st.button("Back to the Prolific and complete the task!", key="prolific"):
            close_and_redirect()

if __name__ == "__main__":
    main()
