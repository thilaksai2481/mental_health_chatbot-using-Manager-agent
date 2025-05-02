# crew_logic.py
import os
import json
import traceback
import ast # For safely evaluating string representations of dicts
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Assuming config.py is in the same directory or configured in PYTHONPATH
try:
    from config import MEMORY_FILE, gad7_questions, phq9_questions, options
except ImportError:
    print("Warning: config.py not found. Using default values (ensure these are defined).")
    # Define fallbacks if config.py is not used
    MEMORY_FILE = "user_memory_crewai_streamlit.json"
    gad7_questions = ["Q1?", "Q2?", "..."] # Add actual questions if not using config
    phq9_questions = ["Q1?", "Q2?", "..."] # Add actual questions if not using config
    options = {"Not at all": 0, "Several days": 1, "More than half the days": 2, "Nearly every day": 3}


# --- Configuration & LLM ---
load_dotenv()
GROQ_API_KEY = os.getenv['GROQ_API_KEY']
if not GROQ_API_KEY:
    # Handle missing key more gracefully for Streamlit deployment
    print("ERROR: GROQ_API_KEY environment variable not set.")
    # Potentially raise an error or use a fallback mechanism if desired
    # For now, we'll let it fail later if Groq() is called without a key.
    # raise ValueError("GROQ_API_KEY environment variable not set.")

# Initialize Groq client (handle potential key error)
try:
    groq_llm = ChatGroq(api_key=GROQ_API_KEY, model_name="groq/gemma2-9b-it")
except Exception as e:
    print(f"Error initializing Groq LLM: {e}")
    groq_llm = None # Set to None if initialization fails


# --- Persistence Functions ---
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                # Handle empty file case
                content = f.read()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {MEMORY_FILE}. Starting fresh.")
            return {}
        except Exception as e:
            print(f"Error loading memory: {e}")
            return {}
    return {}

def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=4)
    except Exception as e:
        print(f"Error saving memory: {e}")


# --- Custom Tool: Mental Health Assessment ---
class MentalHealthAssessmentTool(BaseTool):
    name: str = "Mental Health Assessment Tool"
    description: str = (
        "Evaluates GAD-7 (Anxiety) or PHQ-9 (Depression) assessment scores based on user answers. "
        "Input MUST BE a dictionary with 'assessment_type' ('GAD-7' or 'PHQ-9') "
        "and 'answers' (a list of strings like 'Several days', 'Not at all', etc., corresponding "
        "to the questions in order)."
    )
    options: dict = options

    def _run(self, **kwargs) -> dict:
        # Robust input extraction and validation
        input_dict = kwargs
        if not isinstance(input_dict, dict):
             try:
                 # Handle case where input might be a string representation
                 input_dict = ast.literal_eval(input_dict)
                 if not isinstance(input_dict, dict):
                      return {"error": "Input must be a dictionary or a string representation of one."}
             except Exception as e:
                 return {"error": f"Failed to parse input: {e}. Input must be a dictionary."}

        assessment_type = input_dict.get('assessment_type')
        answers = input_dict.get('answers')

        if not assessment_type or not isinstance(assessment_type, str) or assessment_type not in ["GAD-7", "PHQ-9"]:
             return {"error": f"Invalid or missing 'assessment_type'. Must be 'GAD-7' or 'PHQ-9'. Received: {assessment_type}"}
        if not answers or not isinstance(answers, list):
             return {"error": f"Invalid or missing 'answers'. Must be a list of strings. Received: {answers}"}

        expected_length = len(gad7_questions) if assessment_type == "GAD-7" else len(phq9_questions)
        if len(answers) != expected_length:
             return {"error": f"Incorrect number of answers for {assessment_type}. Expected {expected_length}, got {len(answers)}."}

        validated_answers = []
        for answer in answers:
            if answer not in self.options:
                 return {"error": f"Invalid answer value '{answer}'. Allowed values are: {list(self.options.keys())}"}
            validated_answers.append(answer)

        try:
            total_score = sum(self.options[answer] for answer in validated_answers)
            range_result = "Unknown"
            impact = "Evaluation criteria not met."

            # --- Evaluation logic (Simplified for brevity - use full logic from previous examples) ---
            if assessment_type == "GAD-7":
                if 0 <= total_score <= 4: range_result, impact = "Minimal Anxiety", "Minimal anxiety..."
                elif 5 <= total_score <= 9: range_result, impact = "Mild Anxiety", "Mild anxiety..."
                elif 10 <= total_score <= 14: range_result, impact = "Moderate Anxiety", "Moderate anxiety..."
                else: range_result, impact = "Severe Anxiety", "Severe anxiety..."
            elif assessment_type == "PHQ-9":
                 if 0 <= total_score <= 4: range_result, impact = "Minimal Depression", "Minimal depression..."
                 elif 5 <= total_score <= 9: range_result, impact = "Mild Depression", "Mild depression..."
                 elif 10 <= total_score <= 14: range_result, impact = "Moderate Depression", "Moderate depression..."
                 elif 15 <= total_score <= 19: range_result, impact = "Moderately Severe Depression", "Moderately severe depression..."
                 else: range_result, impact = "Severe Depression", "Severe depression..."

            return {"type": assessment_type, "range": range_result, "score": total_score, "impact": impact}
        except Exception as e:
            print(f"Error during score calculation: {e}\n{traceback.format_exc()}")
            return {"error": f"Error during score calculation: {str(e)}"}

assessment_tool = MentalHealthAssessmentTool()

# --- Agent Definitions (Ensure LLM is available) ---
assessor = Agent(
    role="Mental Health Assessor",
    goal="Accurately evaluate the user's GAD-7 or PHQ-9 assessment using the 'Mental Health Assessment Tool' based on the provided answers. Return ONLY the structured JSON result dictionary from the tool.",
    backstory=(
        "An expert in applying the 'Mental Health Assessment Tool'. You strictly follow instructions, take the assessment type and list of answers, execute the tool, and pass back the exact result dictionary without modification or additional commentary."
    ),
    llm=groq_llm,
    tools=[assessment_tool],
    verbose=True, # Set to False for cleaner Streamlit logs if needed
    allow_delegation=False
) if groq_llm else None # Only define if LLM initialized

chatbot = Agent(
    role="Empathetic Mental Health Chatbot",
    goal=(
        "Provide a supportive and empathetic conversational response to the user. **Crucially, base the response on their latest assessment results (provided as context - including type, range, score, and impact) and their current query/message.** Acknowledge previous results if relevant context is provided. Keep responses concise, helpful, non-medical, and focused on the assessed condition."
    ),
    backstory=(
        "A CBT-informed chatbot specializing in empathetic communication. You receive context including the user's name, latest assessment result (e.g., {'type': 'GAD-7', 'range': 'Moderate Anxiety', 'score': 12, 'impact': '...'}), potentially previous results, recent chat history, and their current message. Craft a single, natural-sounding, supportive response. **You MUST acknowledge the provided assessment severity.** Avoid clinical jargon and medical advice. Refer to professionals if severity is high or user expresses severe distress, but do so gently."
    ),
    llm=groq_llm,
    verbose=True,
    allow_delegation=False
) if groq_llm else None

manager = Agent(
    role="Mental Health Support Workflow Manager",
    goal=(
        "Efficiently manage the user interaction for mental health assessment and support, ensuring a smooth transition between steps. "
        "1. Receive initial user data (name, assessment type, answers, query). "
        "2. Delegate the 'assessment_task' to the 'Mental Health Assessor' agent. "
        "3. Await the structured assessment result (a dictionary). "
        "4. **Verify the assessment result is a valid dictionary.** "
        "5. Using the valid assessment result dictionary as context, delegate the 'chatbot_task' to the 'Empathetic Mental Health Chatbot' agent, providing all necessary context (assessment result dict, user query, name, history). "
        "6. Receive the final chat response string from the Chatbot. "
        "7. Compile and return **only** the final chatbot response string."
    ),
    backstory=(
        "You are the central coordinator. You ensure the Assessor provides a valid dictionary result before passing it to the Chatbot. You follow the sequence: Assess -> Chat. You handle potential errors from the assessor gracefully. Your final output MUST be the user-facing chatbot message string."
    ),
    llm=groq_llm,
    verbose=True,
    allow_delegation=True
) if groq_llm else None


# --- Crew Execution Functions ---

def run_mental_health_crew(user_name, assessment_type, user_answers, user_query):
    """
    Runs the full CrewAI workflow (Assess -> Chat) using the Manager.

    Returns:
        tuple: (assessment_result_dict, chatbot_response_string, error_message)
               assessment_result_dict is None if assessment fails.
               chatbot_response_string is None if chat fails or assessment fails.
               error_message contains details if any step fails.
    """
    if not groq_llm or not assessor or not chatbot or not manager:
        return None, None, "LLM or Agents failed to initialize. Check API Key and configuration."

    memory = load_memory()
    user_data = memory.get(user_name, {"chat_history": [], "result": None})
    previous_result_str = "None"
    if user_data.get("result"):
         prev_res = user_data["result"]
         previous_result_str = f"{prev_res.get('type', 'N/A')} - {prev_res.get('range', 'N/A')} (Score: {prev_res.get('score', 'N/A')})"

    # --- Task Definitions ---
    assessment_task = Task(
        description=(
            f"Evaluate the results for a '{assessment_type}' assessment for user '{user_name}'. "
            f"User answers: {user_answers}. "
            f"Use the 'Mental Health Assessment Tool'. Input to the tool MUST be a dictionary: "
            f"{{'assessment_type': '{assessment_type}', 'answers': {user_answers}}}. "
            f"Return the complete dictionary output from the tool."
        ),
        expected_output=(
            "A dictionary containing the assessment 'type', 'range', 'score', and 'impact', OR an error dictionary {'error': '...'}"
        ),
        agent=assessor,
        human_input=False
    )

    # Define chatbot task structure, context will be dynamically added by manager simulation
    chatbot_task_template = Task(
        description=(
            f"User '{user_name}' has completed a '{assessment_type}' assessment. "
            f"**The assessment result dictionary is provided as context.** " # Placeholder
            f"The user's current query/message is: '{user_query}'.\n"
            f"Context about the user's previous assessment result: {previous_result_str}.\n"
            f"Context from recent chat history (last 5): {user_data.get('chat_history', [])[-5:]} \n\n"
            f"**Your Action:** Based on the NEW assessment results (from context) and the user's query ('{user_query}'), "
            f"generate a single, empathetic response. **Acknowledge the assessment severity from the context dictionary.** "
            f"Focus on the assessed condition ({assessment_type.split('-')[0]}). Be concise and supportive. DO NOT give medical advice."
        ),
        expected_output=(
            "A single string containing the empathetic chat message for the user."
        ),
        agent=chatbot,
        human_input=False
        # Context will be added dynamically based on assessment_task output
    )

    # --- Crew Definition ---
    mental_health_crew = Crew(
        agents=[assessor, chatbot],
        tasks=[assessment_task, chatbot_task_template], # Pass template task
        manager_agent=manager,
        process=Process.hierarchical,
        verbose=1 # Lower verbosity for cleaner Streamlit logs maybe
    )

    # --- Execute the Crew ---
    print("\n--- Kicking Off Hierarchical Crew (Full Run) ---")
    assessment_result_dict = None
    chatbot_response = None
    error_msg = None

    try:
        # Kickoff - Manager orchestrates assessor then chatbot
        crew_result = mental_health_crew.kickoff()

        # --- Process Results ---
        # 1. Get Assessment Result
        assessment_task_output = assessment_task.output.raw_output if assessment_task.output else None
        print(f"Raw Assessment Output: {assessment_task_output}")
        if assessment_task_output:
            try:
                if isinstance(assessment_task_output, str):
                    assessment_result_dict = ast.literal_eval(assessment_task_output)
                elif isinstance(assessment_task_output, dict):
                    assessment_result_dict = assessment_task_output

                if not isinstance(assessment_result_dict, dict):
                     raise ValueError("Parsed assessment output is not a dictionary.")

                if 'error' in assessment_result_dict:
                    error_msg = f"Assessment Error: {assessment_result_dict['error']}"
                    print(error_msg)
                    assessment_result_dict = None # Nullify result on error
                else:
                     print(f"Parsed Assessment Result: {assessment_result_dict}")

            except Exception as parse_error:
                error_msg = f"Error parsing assessment result: {parse_error}. Raw: {assessment_task_output}"
                print(error_msg)
                assessment_result_dict = None

        # 2. Get Chatbot Result (should be the final crew_result if assessment was okay)
        if assessment_result_dict: # Only expect chatbot response if assessment succeeded
             if isinstance(crew_result, str):
                 chatbot_response = crew_result
             else: # Fallback if output is unexpected
                 chatbot_response = str(crew_result)
             print(f"Final Chatbot Response: {chatbot_response}")
        else:
            # If assessment failed, crew_result might be None or reflect the assessor's output/error
            chatbot_response = None # Ensure no chatbot response if assessment failed
            if not error_msg: # If no specific assessment error captured, add a generic one
                 error_msg = "Assessment step failed, cannot proceed to chat."


        # --- Update Memory ---
        if assessment_result_dict: # Save successful assessment
             user_data['result'] = assessment_result_dict
        # Only save chat history if both assessment and chat were successful
        if assessment_result_dict and chatbot_response:
            user_data.setdefault('chat_history', []).append({"role": "user", "content": user_query})
            user_data['chat_history'].append({"role": "assistant", "content": chatbot_response})

        memory[user_name] = user_data
        save_memory(memory)

        return assessment_result_dict, chatbot_response, error_msg

    except Exception as e:
        error_msg = f"Crew execution failed: {e}\n{traceback.format_exc()}"
        print(error_msg)
        # Attempt to save any partial state? Maybe not reliable.
        # save_memory(memory)
        return assessment_result_dict, chatbot_response, error_msg


def run_chatbot_only(user_name, current_assessment_result, user_query):
    """
    Runs only the Chatbot agent for follow-up messages.

    Args:
        user_name (str): User's name.
        current_assessment_result (dict): The dictionary result from the last assessment.
        user_query (str): The user's new message.

    Returns:
        tuple: (chatbot_response_string, error_message)
    """
    if not groq_llm or not chatbot:
        return None, "Chatbot Agent not initialized."
    if not current_assessment_result or 'error' in current_assessment_result:
         return None, "Cannot run chatbot without a valid prior assessment result."

    memory = load_memory()
    user_data = memory.get(user_name, {"chat_history": [], "result": current_assessment_result}) # Use passed result
    previous_result_str = f"{current_assessment_result.get('type', 'N/A')} - {current_assessment_result.get('range', 'N/A')}" # Using current as previous context here

    # Create a specific task for the chatbot
    chatbot_direct_task = Task(
        description=(
            f"User '{user_name}' needs a response. "
            f"Their relevant assessment result is: {current_assessment_result}. " # Provide the dict directly
            f"Their current query/message is: '{user_query}'.\n"
            f"Context from recent chat history (last 5): {user_data.get('chat_history', [])[-5:]} \n\n"
            f"**Your Action:** Based on the assessment context ({current_assessment_result.get('range', 'N/A')}) and the query ('{user_query}'), "
            f"generate a single, empathetic response. Acknowledge the assessment severity. Be concise and supportive. DO NOT give medical advice."
        ),
        expected_output="A single string containing the empathetic chat message.",
        agent=chatbot,
        human_input=False
    )

    print(f"\n--- Running Chatbot Agent Only for: {user_name} ---")
    chatbot_response = None
    error_msg = None

    try:
        # Execute the single task directly (no crew needed for one agent)
        # Note: task.execute() might need context passed differently or agent.execute_task() is preferred
        # Using agent.execute_task() is generally safer for direct execution
        chatbot_response = chatbot.execute_task(chatbot_direct_task)

        if isinstance(chatbot_response, str):
             print(f"Chatbot Direct Response: {chatbot_response}")
        else:
             error_msg = f"Chatbot returned unexpected type: {type(chatbot_response)}. Content: {chatbot_response}"
             print(error_msg)
             chatbot_response = None # Ensure it's None on error

        # --- Update Memory ---
        if chatbot_response:
            user_data.setdefault('chat_history', []).append({"role": "user", "content": user_query})
            user_data['chat_history'].append({"role": "assistant", "content": chatbot_response})
            memory[user_name] = user_data # Update memory with new chat
            save_memory(memory)
        else:
            # Save memory even if chat failed? Maybe not useful.
            pass

        return chatbot_response, error_msg

    except Exception as e:
        error_msg = f"Chatbot execution failed: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return None, error_msg