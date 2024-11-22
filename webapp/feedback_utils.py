# feedback_utils.py
import re
import streamlit as st
import time
import logging
import datetime
import json
import os
from collections import defaultdict
from typing import List
import pandas as pd
from therapy_utils import generate_response, clean_chat

MIN_WORDS = 10

def enhance_evidence(evidence:str, usr_conv_list:List[str], agt_conv_list:List[str]) -> str:
    """
    Enhance the evidence by adding chatbot quesion reference in the click to see in chat feature.
    """
    # Obtains the question asked by the chatbot for the evidence
    search_indx = None
    for indx, message in enumerate(usr_conv_list):
        if evidence in message:
            print(f"""Evidence: {evidence}, indx: {indx}""")
            search_indx = indx
            break
    if search_indx is not None:
        agent_question = agt_conv_list[search_indx]
        return f"AI therapy:{agent_question} {os.linesep} You: **{evidence}**"
    # If the evidence is not found in the user conversation, return the evidence as it is
    return f"You: **{evidence}**"


def get_survey_sample(all_detections:dict, max_display:int = 10):
    """
    This function samples the survey questions for the user to provide feedback.
    """
    user_conv_list = st.session_state.usr_conv_list
    agent_conv_list = st.session_state.agt_conv_list

    for key in all_detections:
        evidence = all_detections[key]["revealation"]
        better_evidence = enhance_evidence(evidence, user_conv_list, agent_conv_list)
        all_detections[key]["better_evidence"] = better_evidence

    if len(all_detections) <= max_display:
        return all_detections

    # Group the detections by category
    categories = defaultdict(list)
    for key, value in all_detections.items():
        categories[value["category"]].append(key)
    
    # Start with sampling
    samples, sampled_detections = 0, {}
    while samples < max_display:
        for category in sorted(categories):
            if samples >= max_display:
                return sampled_detections
                # We can sample only if the category has more than one detection
            if len(categories[category]):
                key = categories[category].pop(0)
                sampled_detections[key] = all_detections[key]
                samples += 1
    return sampled_detections


def disable_copy_paste():
    # Inject both JavaScript and CSS using a single HTML component
    st.components.v1.html("""
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
            /* Disable text selection */
            .stTextArea textarea {
                user-select: none !important;
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                -ms-user-select: none !important;
            }
        </style>
        
        <script>
    // Function to disable copy/paste events for text inputs
    function disableCopyPasteForTextInputs() {
        const textInputs = parent.document.querySelectorAll('.stTextInput input');
        textInputs.forEach(input => {
            input.addEventListener('copy', e => e.preventDefault());
            input.addEventListener('cut', e => e.preventDefault());
            input.addEventListener('paste', e => e.preventDefault());
            input.addEventListener('contextmenu', e => e.preventDefault());
            
            // Disable keyboard shortcuts
            input.addEventListener('keydown', e => {
                if ((e.ctrlKey || e.metaKey) && 
                    (e.key === 'c' || e.key === 'v' || e.key === 'x')) {
                        e.preventDefault();
                }
            });
        });
    }

    // Function to disable copy/paste events for text areas
    function disableCopyPasteForTextAreas() {
        const textareas = parent.document.querySelectorAll('.stTextArea textarea');
        textareas.forEach(textarea => {
            textarea.addEventListener('copy', e => e.preventDefault());
            textarea.addEventListener('cut', e => e.preventDefault());
            textarea.addEventListener('paste', e => e.preventDefault());
            textarea.addEventListener('contextmenu', e => e.preventDefault());
            
            // Disable keyboard shortcuts
            textarea.addEventListener('keydown', e => {
                if ((e.ctrlKey || e.metaKey) && 
                    (e.key === 'c' || e.key === 'v' || e.key === 'x')) {
                        e.preventDefault();
                }
            });
        });
    }

    // Function to apply both disabling functions
    function applyAllDisableCopyPaste() {
        disableCopyPasteForTextInputs();
        disableCopyPasteForTextAreas();
    }

    // Run immediately and also after a short delay to ensure elements are loaded
    applyAllDisableCopyPaste();
    setTimeout(applyAllDisableCopyPaste, 500);

    // Monitor for dynamic changes
    const observer = new MutationObserver(applyAllDisableCopyPaste);
    observer.observe(parent.document.body, {
        childList: true,
        subtree: true
    });
</script>
    """, height=0)

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
        .survey-heading {
            font-size: 30px !important;
        }
        .survey-text {
            font-size: 20px !important;
        }
        .survey-reveal {
            font-size: 14px !important;
        }
        </style>
        """, unsafe_allow_html=True)


def get_survey_info():
    """
    Use GPT-4 to determine the survey questions for post conversation
    Return all the detected revealed unnecessary information.
    """

    # Define the response format exclusively as we cannot have {} in the user prompt
    json_response_format = {
        "phrase": "[The phrase being checked]",
        "present": "Yes/No",
        "evidence": "[Exact quote from the dialogue that infers the phrase or semantically equivalent]"
    }

    # User Prompt to set the format of the output and provide only when there is a match.
    user_prompt = f"""Analyze the given dialogue carefully and compare it against each phrase in the specified list of phrases (including some rewording of the phrases, or can be easily inferred). For each phrase:

        1. Determine if the phrase or its semantic equivalent is present in the dialogue. Consider:
        - Exact matches
        - Paraphrases or rewordings
        - Implied meanings that can be reasonably inferred from the context

        2. Provide a nested JSON response where key is the index of each phrase in the list of phrases and value is the phrase attributes, i.e. for each phrase provide a Json response with the following structure:
        {json_response_format}

        3. For the "present" field:
        - Use "Yes" if the phrase or its equivalent is found
        - Use "No" if it's not present or cannot be reasonably inferred

        4. For the "evidence" field:
        - If present, provide the most relevant quote from the dialogue
        - If not present, skip the field

        Ensure your analysis is thorough and considers both explicit and implicit information in the dialogue.
        
        ### Phrases to check against:
        {st.session_state.posthoc_survey_info['user_mentioned'].tolist()}

        ### Dialogue:
        {st.session_state.user_conversation}
        """

    system_prompt = """
    You are a smart semantic analyzer that evaluates dialogue content against specific phrases. 
    Your core capabilities include:
        1. MATCHING LEVELS
        - Direct matches (exact or rephrased)
        - Semantic equivalents (synonyms, contextual matches)
        - Logical inferences (combined evidence)
        - Professional terminology alignment
        - Name/location variations

        2. PRESENT CRITERIA
        Answer "Yes" when information is:
        - Explicitly stated
        - Clearly paraphrased
        - Logically inferrable
        Answer "No" when:
        - Information contradicts dialogue
        - Cannot be reasonably inferred
        - Too speculative

        3. EVIDENCE STANDARDS
        - Use exact quotes from text
        - Multiple quotes separated by ' | '
        - Include context for clarity
        - All supporting evidence for inferences

        You must be precise, thorough, and avoid speculation beyond reasonable inference.
    """

    gpt_response = generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model="gpt-4o-mini",
        max_tokens=2000,
        temperature=0
    )

    logging.info("Detection GPT-4 responses : %s", gpt_response)

    # Process to get rid of code and other unwanted characters
    gpt_response = gpt_response.replace('```json', '').replace('```', '').strip()

    # Evaluate the json and store it in a dictionary
    llm_responses = json.loads(gpt_response)

    survey_questions = {}
    for key in llm_responses:
        if llm_responses[key]["present"].lower() == "yes":
            kn = int(key)
            survey_questions[key] = {
                "revealation": llm_responses[key]["evidence"],
                "category": st.session_state.posthoc_survey_info.loc[kn, "category"],
                "priority": st.session_state.posthoc_survey_info.loc[kn, "category priority"].astype(int).astype(str),
                "user_mentioned": st.session_state.posthoc_survey_info.loc[kn, "user_mentioned"],
                "survey_display": st.session_state.posthoc_survey_info.loc[kn, "survey_display"],
            }
    st.session_state.complete_detections = survey_questions
    return survey_questions


def setup_survey_config():
    """This function sets up the session state display options for the survey."""

    # Disable configurations
    if "disable_user_selections" not in st.session_state:
        st.session_state.disable_user_selections = False

    if "disable_necessary_reasons" not in st.session_state:
        st.session_state.disable_necessary_reasons = True

    if "disable_unnecessary_reasons" not in st.session_state:
        st.session_state.disable_unnecessary_reasons = True

    if "disabled_submit" not in st.session_state:
        st.session_state.disable_submit = True

    # User display configurations
    if "user_selections_fixed" not in st.session_state:
        st.session_state.user_selections_fixed = False

    if "user_nec_reasons_entered" not in st.session_state:
        st.session_state.user_nec_reasons_entered = False

    if "user_unnec_reasons_entered" not in st.session_state:
        st.session_state.user_unnec_reasons_entered = False

    # Store the user selections and non-selections
    if "user_selections" not in st.session_state:
        st.session_state.user_selections = set() # Stores the keys in string format
        st.session_state.user_non_selections = set() # Stores the keys in string format


def set_user_conversation():
    """Sets the user conversation from the chat history."""
    st.session_state.usr_conv_list = [message["response"] for message in st.session_state.messages
                     if message["turn"] == "user"]
    st.session_state.agt_conv_list = [message["response"] for message in st.session_state.messages
                     if message["turn"] == "assistant"]
    st.session_state.user_conversation = "\n".join(st.session_state.usr_conv_list)
    logging.info("User conversation: %s", st.session_state.user_conversation)
    logging.info("Agent conversation: %s", st.session_state.agt_conv_list)
    logging.info("User conversation list: %s", st.session_state.usr_conv_list)

def get_user_selections():
    """
    This function asks the user to provide feedback on the revealed detected private information
    and stores the user's feedback, reasoning, and the revealed private information.
    """
    if "user_conversation" not in st.session_state:
        set_user_conversation()

    # If complete detections are not obtained in the daemon mode, enforce the user to wait
    if "complete_detections" not in st.session_state:
        logging.info("Forcing to get detections from user conversation")
        with st.spinner("Analyzing conversation..."):
            complete_detections = get_survey_info()
        logging.info("Obtained gpt detections from user conversation")
        logging.info("Complete Detections : %s", complete_detections)
        st.session_state.complete_detections = complete_detections

    # Get the survey info from user conversation if not already obtained
    if "survey_info" not in st.session_state:
        logging.info("Sampling survey info from the complete detections.")
        st.session_state.survey_info = get_survey_sample(st.session_state.complete_detections)
        logging.info("Sampled Survey info: %s", st.session_state.survey_info)

    survey_info = st.session_state.survey_info

    # Configuring the setup
    setup_survey_config()
    disable_copy_paste() # Debug

    if not st.session_state.user_selections_fixed:
        # Display the survey information to the user for getting the user selections
        if survey_info == {}:
            # Skip the survey as there are no detections
            navigate_to_next_page()
            # st.write("Successfully analyzed conversation.")
            # st.session_state.disable_submit = False
            # return None

        else:
            logging.info("Surveying user, waiting for user to complete selections.")

            # Survey information
            st.subheader("Select the following information that you think it's necessary to share for the therapy")

            for key, value in survey_info.items():
                # Commenting out the display in columns as click to see in the chat is not optimal
                # col1, col3 = st.columns([5, 1])
                # with col1:
                #     st.checkbox(f"{value['survey_display']}", key=f"checkbox_{key}", value=False,
                #                 disabled=st.session_state.disable_user_selections)
                # with col3:
                #     with st.expander("Click to see in chat"):
                #         st.write(f":grey[{value['revealation']}]")

                st.checkbox(f"{value['survey_display']}", key=f"checkbox_{key}", value=False)
            # Display button to fix the user selections to proceed to the next step and prevent change
            st.button("Next", on_click=fix_user_selections)

    # User selections are fixed, proceed to the next step
    if (st.session_state.user_selections_fixed
        and not st.session_state.user_nec_reasons_entered):
        get_necessary_reasoning()

    if (st.session_state.user_selections_fixed
        and st.session_state.user_nec_reasons_entered
        and not st.session_state.user_unnec_reasons_entered):
        get_unnecessary_reasoning()

    if (st.session_state.user_selections_fixed
        and st.session_state.user_nec_reasons_entered
        and st.session_state.user_unnec_reasons_entered):
        # Not required to display the submit button as the user can directly proceed to the next page
        # display_submit_button()
        navigate_to_next_page()
    # st.rerun()


def fix_user_selections():
    """
    This function fixes the user selections made in the survey.
    """
    st.session_state.disable_user_selections = True # Disable the user selections

    # Store the user's selected options into st.session_state memory
    # Depending up on the checkbox selection, obtain the keypart and store in memory.
    for key, value in st.session_state.items():
        if key.startswith("checkbox_"):
            key_part = key.split("_")[1]
            if value:
                st.session_state.user_selections.add(key_part)
            else:
                st.session_state.user_non_selections.add(key_part)

    logging.info("Captured User selection into selected and unselected as %s, %s",
                 st.session_state.user_selections,
                 st.session_state.user_non_selections)
    st.session_state.user_selections_fixed = True # Do not display the selections again


def get_necessary_reasoning():
    """
    This function asks the user to provide reasoning for the selected options in the survey.
    Display of this function is already taken taken care in the get_user_selections function.
    """
    if st.session_state.user_selections and not st.session_state.user_nec_reasons_entered:
        st.subheader("Why you think following information is :blue[necessary] to share for the therapy session?")

        for key in st.session_state.user_selections:
            col1, col2 = st.columns([4, 4])
            col1.write(st.session_state.survey_info[key]["survey_display"])
            # Commented out for now as the See in chat is not optimal for the user
            with col1.expander("See in chat"):
                st.write(f":grey[{st.session_state.survey_info[key]['better_evidence']}]")
            
            _ = col2.text_area("_", key=f"reasoning_{key}_necessary", label_visibility="collapsed",
                                height=120)

        validate_reasoning(prefix="reasoning", suffix="necessary", var_name="disable_necessary_reasons")
        st.button("Next", on_click=set_user_nec_reasoning,
                  disabled=st.session_state.disable_necessary_reasons,
                  help=f"Provide reasoning for :red[all with at-least {MIN_WORDS} words] to proceed to next step.",
                  key="next_button")
    else:
        # set_reasoning("reasoning", "necessary", True, "user_nec_reasons_entered")
        set_user_nec_reasoning()


def set_reasoning(prefix: str = "reasoning", suffix: str = "necessary",
                  selection: bool = True,
                  var_name: str = "user_nec_reasons_entered"):
    """
    This function sets the var_name to True by capturing the reasoning 
    for specified combination of prefix and suffix.
    """
    # Captured the reasoning for the selected options
    for key, value in st.session_state.items():
        if key.startswith(f"{prefix}_") and key.endswith(f"_{suffix}"):
            key_part = key.split("_")[1]
            st.session_state.survey_info[key_part]["reasoning"] = value
            st.session_state.survey_info[key_part]["selected"] = selection
    st.session_state[var_name] = True


def set_user_nec_reasoning():
    """
    This function sets the user_nec_reasons_entered to True after the user 
    provides reasoning for the selected options.
    """
    # Captured the reasoning for the selected options
    for key, value in st.session_state.items():
        if key.startswith("reasoning_") and key.endswith("_necessary"):
            key_part = key.split("_")[1]
            st.session_state.survey_info[key_part]["reasoning"] = value
            st.session_state.survey_info[key_part]["selected"] = True
    st.session_state.user_nec_reasons_entered = True


def set_user_unnec_reasoning():
    """
    This function sets the user_nec_reasons_entered to True after the user provides 
    reasoning for the un-selected options.
    """
    # Captured the reasoning for the selected options
    for key, value in st.session_state.items():
        if key.startswith("reasoning_") and key.endswith("_unnecessary"):
            key_part = key.split("_")[1]
            st.session_state.survey_info[key_part]["reasoning"] = value
            st.session_state.survey_info[key_part]["selected"] = True
    st.session_state.user_unnec_reasons_entered = True


def get_unnecessary_reasoning():
    """
    This function asks the user to provide reasoning for the selected options in the survey.
    """
    # Display the reasoning text area for the user to provide reasoning for the selected options
    if st.session_state.user_non_selections and not st.session_state.user_unnec_reasons_entered:

        if "disable_unnecessary_reasons" not in st.session_state:
            st.session_state.disable_unnecessary_reasons = True

        if st.session_state.disable_unnecessary_reasons:
            st.header("Why you think following information is :blue[unnecessary] to share for the therapy session, but you still share that with the chatbot?")
            # Display the options to the user for the selected options
            for key in st.session_state.user_non_selections:
                col1, col2 = st.columns([4, 4])

                # Display the information in the first column
                col1.write(st.session_state.survey_info[key]["survey_display"])
                # Commented out for now as the See in chat is not optimal for the user
                with col1.expander("See in chat"):
                    st.write(f":grey[{st.session_state.survey_info[key]['better_evidence']}]")

                # Display the reasoning text area in the second column
                with col2:
                    _ = col2.text_area("_", key=f"reasoning_{key}_unnecessary", label_visibility="collapsed")

        validate_reasoning(prefix="reasoning", suffix="unnecessary", var_name="disable_unnecessary_reasons")
        st.button("Next", on_click=set_user_unnec_reasoning,
                  disabled=st.session_state.disable_unnecessary_reasons,
                  help=f"Provide reasoning for :red[all with at-least {MIN_WORDS} words] to proceed to next step.")
    else:
        # set_reasoning("reasoning", "unnecessary", False, "user_unnec_reasons_entered")
        set_user_unnec_reasoning()


def display_submit_button():
    """Enables the submit button after the user provides reasoning for the selected and non-selected options."""
    # st.switch_page("Post Survey 3")
    st.session_state.user_unnec_reasons_entered = True
    st.session_state.user_nec_reasons_entered = True
    st.session_state.disable_submit = False

    # st.write("Succesfully completed Post Survey 2")
    if st.button("Next", on_click=navigate_to_next_page,
                     disabled=st.session_state.disable_submit):
        st.session_state.survey_2_completed = True


def navigate_to_next_page():
    """
    This function navigates the user to the next page after the survey is completed.
    """
    # Store the feedback in firecase and set the survey_2_completed to True
    store_feedback()
    st.session_state.survey_2_completed = True
    # Set the other flags to True
    st.session_state.user_selections_fixed = True
    st.session_state.user_unnec_reasons_entered = True
    st.session_state.user_nec_reasons_entered = True
    st.rerun()


def validate_reasoning(prefix: str = "reasoning", suffix: str = "necessary",
                       var_name: str = "disable_submit", min_words: int = MIN_WORDS):
    """
    This function validates all the reasoning provided by the user for the desired options and 
    sets the var_name to True or False.
    """
    regex = re.compile(r"[\s]{2,}")
    for key, value in st.session_state.items():
        if key.startswith(f"{prefix}_") and key.endswith(f"_{suffix}"):
            value = regex.sub(" ", value).strip()
            if not value or len(value.split(" ")) < min_words:
                st.session_state[var_name] = True
                return None
    st.session_state[var_name] = False
    return None


def store_feedback():
    """
    Store the user's feedback in a structured way locally and in Firebase Firestore.
    Enables the post-survey options after the feedback is submitted.
    """

    feedback = defaultdict(dict)

    # Add the user conversation and chat history to the storage
    feedback["user_conversation"] = st.session_state.get('user_conversation', [])
    feedback['messages'] = st.session_state.get('messages', [])
    feedback['complete_detections'] = st.session_state.get('complete_detections', {})
    feedback['user_selections'] = st.session_state.get('user_selections', [])
    feedback['survey_info'] = st.session_state.get('survey_info', {})
    
    # Prolific ID
    prolific_id = st.session_state.get('prolific_id', 'unknown')
    feedback["prolific_id"] = prolific_id

    # Log the user feedback
    logging.info("=" * 50)
    logging.info("User feedback: %s", feedback)
    logging.info("=" * 50)

    # Dump user feedback to a text file with timestamp reference
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # feedback_file = os.path.join(".logs", f"feedback_{timestamp}.json")
    # os.makedirs(".logs", exist_ok=True)
    # with open(feedback_file, "w", encoding='utf-8') as f:
    #     json.dump(feedback, f, indent=4)

    if "firestore_db" in st.session_state:
        # Store the feedback in Firebase Firestore if configured
        try:
            db = st.session_state.firestore_db
            # Reference to the collection
            collection_ref = db.collection('group_one_survey_two_responses')

            # Create a unique document name using Prolific ID and timestamp
            document_name = f"{prolific_id}_{timestamp}"

            # Add the feedback document
            collection_ref.document(document_name).set(feedback)

            st.success("Feedback submitted successfully.")
        except Exception as e:
            st.error(f"An error occurred while submitting feedback: {e}")

    # Clear the chat history and reset the session state if needed
    # clean_chat()
    st.session_state.survey_2_completed = True


def log_info(message, mode:str="info"):
    """
    This function logs the information message to the console.
    """
    if mode == "error":
        logging.error(message)
    else:
        logging.info(message)


def read_posthoc_survey_info_csv(filename):
    """
    This function reads the posthoc survey information from the CSV file
    Retuns the tuple of (indices, categories, categories_priorities, user_mentioned, survey_display)
    """
    data = pd.read_csv(filename, encoding='utf-8')
    # data.sort_values(by=["category priority", "category"], inplace=True) # Not required.
    return data
