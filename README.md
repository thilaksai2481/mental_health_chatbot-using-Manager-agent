# CrewAI Mental Health Support Chatbot (Streamlit UI)

## Overview

This project demonstrates a mental health support chatbot built using Python, Streamlit for the user interface, and CrewAI as the agent framework. The application guides users through a standardized mental health assessment (GAD-7 for Anxiety or PHQ-9 for Depression) and then provides an empathetic chatbot interaction based on the assessment results.

The backend leverages CrewAI's hierarchical process, featuring:
*   An **Assessor Agent** using a custom tool to score the assessment.
*   An **Empathetic Chatbot Agent** to interact with the user based on their results.
*   A **Manager Agent** to orchestrate the workflow between the Assessor and Chatbot agents.
*   Integration with the **Groq API** for fast LLM responses.

**Disclaimer:** This application is for demonstration and informational purposes only. It is **NOT** a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition. Never disregard professional medical advice or delay in seeking it because of something you have read or interacted with on this application.

## Features

*   **Interactive UI:** Built with Streamlit for easy interaction.
*   **User Identification:** Greets users by name.
*   **Assessment Choice:** Users can select between Anxiety (GAD-7) or Depression (PHQ-9) assessments.
*   **Guided Assessment:** Step-by-step questions with clear options.
*   **CrewAI Powered Backend:**
    *   Utilizes multiple agents (Assessor, Chatbot, Manager) for distinct tasks.
    *   Employs a hierarchical process managed by the Manager Agent.
    *   Custom `MentalHealthAssessmentTool` for reliable scoring.
*   **Contextual Chat:** The chatbot's responses are tailored based on the user's assessment score and severity level.
*   **Session Persistence:** Basic user data (name, latest assessment result, chat history) is stored locally in a JSON file (`user_memory_crewai_streamlit.json`).
*   **Fast LLM:** Uses Groq for quick language model responses.

## Technology Stack

*   **Python 3.8+**
*   **Streamlit:** Web application framework for the UI.
*   **CrewAI & CrewAI Tools:** Framework for building and orchestrating AI agents.
*   **Groq SDK (`groq-sdk`):** Python client for the Groq API.
*   **python-dotenv:** For managing environment variables (API keys).

## Prerequisites

*   Python 3.8 or higher installed.
*   `pip` (Python package installer).
*   Git (Optional, for cloning).
*   A **Groq API Key**. You can get one from [GroqCloud](https://console.groq.com/keys).

## Setup

1.  **Clone the Repository (Optional):**
    ```bash
    # If you have the code in a repository
    git clone <your-repository-url>
    cd <repository-directory>
    ```
    If you received the code directly, navigate to the project directory containing `app.py`, `crew_logic.py`, etc.

2.  **Install Dependencies:**
    ```bash
    pip install streamlit crewai crewai-tools groq-sdk python-dotenv
    ```
    *(Consider creating a `requirements.txt` file for easier dependency management in larger projects)*

3.  **Configure API Key:**
    *   Create a file named `.env` in the root directory of the project (the same directory as `app.py`).
    *   Add your Groq API key to the `.env` file like this:
        ```dotenv
        GROQ_API_KEY=your_actual_groq_api_key
        ```
    *   **Important:** Do **NOT** commit the `.env` file to version control (e.g., Git). Add `.env` to your `.gitignore` file if using Git.

## Running the Application

1.  Open your terminal or command prompt.
2.  Navigate to the project's root directory.
3.  Run the Streamlit application using the following command:
    ```bash
    streamlit run app.py
    ```
4.  Streamlit will provide a URL (usually `http://localhost:8501`) which you can open in your web browser.

## File Structure

.
├── app.py # Main Streamlit application file (UI, state management)
├── crew_logic.py # CrewAI setup (Agents, Tasks, Tool, Crew execution functions)
├── config.py # (Optional) Stores constants like questions, options, memory file path
├── .env # Stores the GROQ_API_KEY (Create this manually, DO NOT COMMIT)
├── user_memory_crewai_streamlit.json # Stores user session data (created automatically on run)
└── README.md # This file


*(Note: If you didn't use `config.py`, the constants will be within `crew_logic.py` or `app.py`)*

## Workflow Overview

1.  **Intro:** The user provides their name.
2.  **Details:** The user selects whether they are concerned with Anxiety or Depression.
3.  **Assessment:** The user answers the corresponding GAD-7 or PHQ-9 questions step-by-step.
4.  **Chat Start:** After finishing the assessment, the user provides their initial chat message.
    *   The application triggers the **full CrewAI workflow**:
        *   The `Manager Agent` delegates the assessment task to the `Assessor Agent`.
        *   The `Assessor Agent` uses the `MentalHealthAssessmentTool` to get the score and result dictionary.
        *   The `Manager Agent` receives the result and delegates the chat task to the `Chatbot Agent`, providing the assessment result and user query as context.
        *   The `Chatbot Agent` generates the initial response.
        *   The result and the first chat exchange are saved.
5.  **Chat Active:** The user can continue chatting.
    *   For subsequent messages, the application triggers **only the `Chatbot Agent`** (`run_chatbot_only` function), providing the stored assessment result and chat history for context. This is more efficient than running the full crew again.
6.  **End:** The user can end the session manually.

## Important Notes

*   **Medical Disclaimer:** Reiterating, this tool does **NOT** provide medical advice. It's a technical demonstration. Consult healthcare professionals for actual health concerns.
*   **API Key Security:** Keep your `.env` file secure and never share your API keys publicly.
*   **Groq Usage:** Using the Groq API may incur costs depending on your usage and Groq's pricing model. Monitor your usage.
*   **Error Handling:** Basic error handling is implemented. Check the terminal where you ran `streamlit run app.py` for more detailed logs if issues occur.
*   **Data Persistence:** The `user_memory_*.json` file provides simple local persistence. This method is not suitable for production environments with multiple users, security requirements, or large amounts of data. A database would be necessary for a real-world application.
