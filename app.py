# app.py
import streamlit as st
import time # For potential delays/simulations

# Import functions and data from crew_logic and config
try:
    from crew_logic import (
        load_memory, save_memory,
        run_mental_health_crew, run_chatbot_only,
        groq_llm # Check if LLM initialized
    )
    # Import questions/options if not using config.py
    # from crew_logic import gad7_questions, phq9_questions, options
    from config import gad7_questions, phq9_questions, options, options_display
except ImportError as e:
    st.error(f"Failed to import necessary modules. Check file structure and dependencies: {e}")
    st.stop() # Stop execution if imports fail

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Mental Health Support Chatbot", layout="wide")
st.title("Mental Health Support Chatbot")

# --- Initialize Session State ---
# Keep track of where the user is in the process
if "stage" not in st.session_state:
    st.session_state.stage = "intro"
# User specific info
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "assessment_choice" not in st.session_state:
    st.session_state.assessment_choice = None # 'Anxiety' or 'Depression'
if "assessment_type" not in st.session_state:
    st.session_state.assessment_type = None # 'GAD-7' or 'PHQ-9'
if "questions" not in st.session_state:
    st.session_state.questions = []
# Assessment progress
if "current_question" not in st.session_state:
    st.session_state.current_question = 0
if "answers" not in st.session_state:
    st.session_state.answers = {} # Store answers as {question_index: answer_text}
# Results and Chat
if "assessment_result" not in st.session_state:
    st.session_state.assessment_result = None # Stores the result dict after assessment
if "chat_history_display" not in st.session_state:
    st.session_state.chat_history_display = [] # For displaying in Streamlit UI [{role: 'user'/'assistant', content: '...'}]
if "error_message" not in st.session_state:
     st.session_state.error_message = None
if "crew_running" not in st.session_state:
     st.session_state.crew_running = False # Flag to prevent double clicks


# --- Helper Functions for UI ---
def display_chat_history():
    chat_container = st.container(height=400) # Adjust height as needed
    with chat_container:
        for message in st.session_state.chat_history_display:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

def reset_session():
    # Keep user name maybe? Or reset fully
    st.session_state.stage = "intro"
    # st.session_state.user_name = "" # Uncomment to reset name too
    st.session_state.assessment_choice = None
    st.session_state.assessment_type = None
    st.session_state.questions = []
    st.session_state.current_question = 0
    st.session_state.answers = {}
    st.session_state.assessment_result = None
    st.session_state.chat_history_display = []
    st.session_state.error_message = None
    st.session_state.crew_running = False
    st.rerun()

def set_error(message):
     st.session_state.error_message = message
     st.session_state.crew_running = False # Ensure flag is reset on error


# --- Main Application Logic ---

# Load memory once at the start
memory = load_memory()

# Display any pending error messages
if st.session_state.error_message:
    st.error(st.session_state.error_message)
    st.session_state.error_message = None # Clear after displaying

# Check if LLM failed to initialize
if not groq_llm:
     st.error("Groq LLM could not be initialized. Please check your GROQ_API_KEY environment variable and internet connection.")
     st.stop()

# --- Stage: Intro ---
if st.session_state.stage == "intro":
    st.header("Welcome!")
    name_input = st.text_input("Please enter your name:", key="user_name_input", value=st.session_state.user_name)

    if st.button("Start Session"):
        if name_input:
            st.session_state.user_name = name_input
            # Check if user has prior *completed* assessment data
            user_data = memory.get(st.session_state.user_name, {})
            if user_data.get("result") and isinstance(user_data["result"], dict) and 'error' not in user_data["result"]:
                 st.session_state.assessment_result = user_data["result"]
                 st.session_state.chat_history_display = user_data.get("chat_history", [])[-10:] # Load recent history
                 st.session_state.stage = "chat_active" # Go directly to chat if previous result exists
                 st.info(f"Welcome back, {st.session_state.user_name}! Continuing your previous session.")
                 time.sleep(1) # Brief pause
            else:
                 st.session_state.stage = "details" # New user or incomplete session, start fresh
            st.rerun()
        else:
            st.warning("Please enter your name.")

# --- Stage: Details ---
elif st.session_state.stage == "details":
    st.header(f"Hello, {st.session_state.user_name}!")
    choice = st.selectbox(
        "Are you primarily concerned with Anxiety or Depression today?",
        ["", "Anxiety", "Depression"],
        key="assessment_choice_select"
    )

    if st.button("Proceed to Assessment"):
        if choice:
            st.session_state.assessment_choice = choice
            if choice == "Anxiety":
                st.session_state.assessment_type = "GAD-7"
                st.session_state.questions = gad7_questions
            else: # Depression
                st.session_state.assessment_type = "PHQ-9"
                st.session_state.questions = phq9_questions

            st.session_state.answers = {} # Reset answers for new assessment
            st.session_state.current_question = 0
            st.session_state.stage = "assessment"
            st.rerun()
        else:
            st.warning("Please select an option.")

# --- Stage: Assessment ---
elif st.session_state.stage == "assessment":
    st.header(f"{st.session_state.assessment_type} Assessment")
    total_questions = len(st.session_state.questions)
    current_q_index = st.session_state.current_question
    question_text = st.session_state.questions[current_q_index]

    st.subheader(f"Question {current_q_index + 1} of {total_questions}")
    st.markdown(f"**{question_text}**")

    # Use radio buttons for selection
    current_answer = st.session_state.answers.get(current_q_index, None)
    answer_index = options_display.index(current_answer) if current_answer else 0 # Default selection index

    answer = st.radio(
        "Select your answer:",
        options_display,
        key=f"answer_{current_q_index}",
        index=answer_index, # Pre-select if already answered
        horizontal=True, # Make options horizontal if preferred
        label_visibility="collapsed"
    )

    # Store the selected answer text
    if answer:
        st.session_state.answers[current_q_index] = answer

    st.markdown("---") # Separator

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if current_q_index > 0:
            if st.button("⬅️ Previous"):
                st.session_state.current_question -= 1
                st.rerun()
    with col3:
        if current_q_index < total_questions - 1:
            # Check if current question has been answered before allowing next
            if current_q_index in st.session_state.answers:
                if st.button("Next ➡️"):
                    st.session_state.current_question += 1
                    st.rerun()
            else:
                st.button("Next ➡️", disabled=True)
                st.caption("Please select an answer to proceed.")
        else: # Last question
             # Check if all questions answered
             all_answered = len(st.session_state.answers) == total_questions
             if st.button("✅ Finish Assessment", disabled=not all_answered):
                if all_answered:
                     st.session_state.stage = "chat_start"
                     st.rerun()
                else:
                    # This should ideally not be reachable if button is disabled, but as fallback
                    st.warning("Please answer all questions before finishing.")
             if not all_answered:
                  st.caption("Please answer this question to finish.")


# --- Stage: Chat Start (Post-Assessment, Pre-First Chat) ---
elif st.session_state.stage == "chat_start":
    st.header("Assessment Complete")
    st.info("Thank you for completing the assessment.")
    display_chat_history() # Display chat (likely empty initially)

    # Use a form for the first chat input
    with st.form("first_chat_form", clear_on_submit=True):
        user_query = st.text_input("How are you feeling right now, or what's on your mind?", key="first_query")
        submitted = st.form_submit_button("Send", disabled=st.session_state.crew_running)

        if submitted and user_query:
            st.session_state.crew_running = True
            st.session_state.error_message = None # Clear previous errors
            # Append user message immediately for better UX
            st.session_state.chat_history_display.append({"role": "user", "content": user_query})
            st.rerun() # Show user message while processing

    # This block runs *after* the rerun triggered by appending the user message
    if st.session_state.crew_running and not submitted: # Check flag after rerun
         with st.spinner("Thinking... (Running Assessment Analysis and Chat)"):
              # Get collected answers in the correct order
              ordered_answers = [st.session_state.answers.get(i) for i in range(len(st.session_state.questions))]

              # Run the full crew
              assessment_result, chatbot_response, error = run_mental_health_crew(
                  st.session_state.user_name,
                  st.session_state.assessment_type,
                  ordered_answers,
                  user_query # Get the query submitted before the rerun
              )

              st.session_state.crew_running = False # Reset flag

              if error:
                  set_error(f"Error during initial chat setup: {error}")
                  # Remove the user message if the backend failed entirely? Optional.
                  # st.session_state.chat_history_display.pop()
              else:
                  st.session_state.assessment_result = assessment_result # Store the result
                  if chatbot_response:
                     st.session_state.chat_history_display.append({"role": "assistant", "content": chatbot_response})
                  else:
                      # Handle case where assessment might be ok but chat failed
                      set_error("Assessment analysed, but failed to get chatbot response.")
                  st.session_state.stage = "chat_active" # Move to active chat

              st.rerun()


# --- Stage: Chat Active ---
elif st.session_state.stage == "chat_active":
    st.header(f"Chat with Support Bot")
    if st.session_state.assessment_result:
         st.caption(f"Context: {st.session_state.assessment_result.get('range', 'N/A')} ({st.session_state.assessment_type})")
    else:
         st.warning("Assessment context is missing. Please restart the session.") # Should not happen ideally

    display_chat_history()

    # Use a form for subsequent chat inputs
    with st.form("chat_form", clear_on_submit=True):
        user_query = st.text_input("Your message:", key="chat_query")
        submitted = st.form_submit_button("Send", disabled=st.session_state.crew_running)

        if submitted and user_query:
            st.session_state.crew_running = True
            st.session_state.error_message = None
            # Append user message immediately
            st.session_state.chat_history_display.append({"role": "user", "content": user_query})
            st.rerun() # Show user message

    # Process after rerun
    if st.session_state.crew_running and not submitted:
        with st.spinner("Thinking..."):
            # Run ONLY the chatbot
            chatbot_response, error = run_chatbot_only(
                st.session_state.user_name,
                st.session_state.assessment_result, # Use stored result
                user_query # Get query from before rerun
            )

            st.session_state.crew_running = False # Reset flag

            if error:
                set_error(f"Error getting response: {error}")
                # st.session_state.chat_history_display.pop() # Optional: remove user message on error
            elif chatbot_response:
                st.session_state.chat_history_display.append({"role": "assistant", "content": chatbot_response})
            else:
                set_error("Failed to get chatbot response.") # Should have error msg usually

            st.rerun()

    # End session button
    if st.button("End Session"):
         st.session_state.stage = "end"
         st.rerun()


# --- Stage: End ---
elif st.session_state.stage == "end":
    st.header("Session Ended")
    st.info(f"Thank you for using the Mental Health Support Chatbot, {st.session_state.user_name}.")
    # Optionally display final assessment result
    if st.session_state.assessment_result:
         st.write("Your final assessment context for this session:")
         st.json(st.session_state.assessment_result)

    if st.button("Start New Session"):
        reset_session()

# --- Sidebar (Optional) ---
with st.sidebar:
    st.header("Session Controls")
    if st.button("Restart Session"):
        reset_session()
    st.caption(f"User: {st.session_state.user_name}")
    st.caption(f"Stage: {st.session_state.stage}")
    # Add any other debug/info if needed
    # st.write("Session State:", st.session_state)