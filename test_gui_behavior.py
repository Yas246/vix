import os
import sys
from app_refactored import initialize_and_process_question

ENV_FILE = ".env"
DUMMY_API_KEY = "AIzaSyDUMMYPLACEHOLDERKEYFORTESTING" # Consistent dummy key

def setup_env_file(content: str):
    with open(ENV_FILE, "w") as f:
        f.write(content)
    # print(f"DEBUG: .env set to:\n{content}") # For debugging test script

def set_bypass_mode(active: bool):
    if active:
        os.environ["VIX_TEST_MODE_NO_LLM"] = "true"
        print("\n-- LLM BYPASS MODE ACTIVATED for next test --")
    else:
        if "VIX_TEST_MODE_NO_LLM" in os.environ:
            del os.environ["VIX_TEST_MODE_NO_LLM"]
        print("\n-- LLM BYPASS MODE DEACTIVATED for next test --")

def run_simulated_question(question, description):
    print(f"--- Test: {description} ---")
    print(f"Question: {question}")

    logs_capture = []
    def callback(message):
        # print(f"[LOG] {message}") # Can be noisy, enable for detailed debugging
        logs_capture.append(message)

    result = initialize_and_process_question(question, status_cb_param=callback)

    print(f"SQL Query: {result.get('sql_query')}")
    print(f"Answer: {result.get('answer')}")
    error = result.get('error')
    if error:
        print(f"Error: {error.splitlines()[0]}") # Print first line of error for brevity
    # For full error: print(f"Error: {error}")

    # Print first few and last few logs for brevity
    if len(logs_capture) > 6:
        print("Logs (summary):")
        for log_entry in logs_capture[:3]: print(f"  {log_entry}")
        print("  ...")
        for log_entry in logs_capture[-3:]: print(f"  {log_entry}")
    else:
        print("Logs:")
        for log_entry in logs_capture: print(f"  {log_entry}")

    print("--- End Test ---\n")
    return result

# --- Test Execution ---

print("=== Test Phase: Settings Management (Simulated) ===")
print("Action: Configure for SQLite with test_data.sqlite, save API key.")
setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}"
DB_TYPE="sqlite"
DB_PATH="test_data.sqlite"
DATABASE_URL="sqlite:///test_data.sqlite"
""")
# In a real GUI, we'd open settings, see these loaded, maybe save again.
# Here, we assume app_refactored.py will pick this up.

print("\nAction: Configure for PostgreSQL (dummy data), save.")
setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}"
DB_TYPE="postgresql"
DB_USER="testuser"
DB_PASSWORD="testpass"
DB_HOST="pg_dummy_host"
DB_PORT="5432"
DB_NAME="dummydb"
DATABASE_URL="postgresql+psycopg2://testuser:testpass@pg_dummy_host:5432/dummydb"
""")
# This only prepares .env. A test call would confirm if it's read.


print("\n=== Test Phase: Q&A with LLM Bypass Mode ===")
set_bypass_mode(True)
setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}" # Still set, but bypass should ignore it for LLM calls
DB_TYPE="sqlite"
DB_PATH="test_data.sqlite"
DATABASE_URL="sqlite:///test_data.sqlite"
""")
run_simulated_question("List all employees", "Q&A SQLite - LLM Bypass")
run_simulated_question("What is the HR department's budget?", "Q&A SQLite - Another question - LLM Bypass")

print("\n=== Test Phase: Database Interaction (LLM Bypass Mode) ===")
set_bypass_mode(True) # Ensure bypass is active
print("Action: Configure for invalid SQLite path.")
setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}"
DB_TYPE="sqlite"
DB_PATH="/invalid_path_that_cant_be_written/error.db"
DATABASE_URL="sqlite:////invalid_path_that_cant_be_written/error.db"
""")
run_simulated_question("Any question", "DB Error with Invalid Path - LLM Bypass")

print("\n=== Test Phase: API Key Error Handling (LLM Bypass Mode OFF) ===")
set_bypass_mode(False)
print("Action: Configure invalid API key.")
setup_env_file(f"""
GOOGLE_API_KEY="THIS_IS_AN_INVALID_KEY"
DB_TYPE="sqlite"
DB_PATH="test_data.sqlite"
DATABASE_URL="sqlite:///test_data.sqlite"
""")
run_simulated_question("How many employees are there?", "API Key Error - LLM Bypass OFF")

print("\n=== Test Phase: No API Key (LLM Bypass Mode OFF) ===")
set_bypass_mode(False)
print("Action: Configure with no API key.")
setup_env_file(f"""
DB_TYPE="sqlite"
DB_PATH="test_data.sqlite"
DATABASE_URL="sqlite:///test_data.sqlite"
""") # GOOGLE_API_KEY is missing
run_simulated_question("How many employees are there?", "No API Key - LLM Bypass OFF")


print("\nAll simulated tests finished.")
print("Reminder: GUI specific behaviors like bypass label visibility and theme toggling require manual visual testing.")
