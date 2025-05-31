import os
from app_refactored import initialize_and_process_question

ENV_FILE = ".env"
# A more realistic-looking dummy API key
DUMMY_API_KEY = "AIzaSyDUMMYPLACEHOLDERKEYSyDUMMYPLACEHOLDERKEY"

def setup_env_file(content: str):
    with open(ENV_FILE, "w") as f:
        f.write(content)
    # print(f"\n.env set to:\n{content}\n")

def run_test_question(question, description):
    print(f"--- Test: {description} ---")
    print(f"Question: {question}")

    logs_capture = []
    def callback(message):
        # print(f"[LOG] {message}")
        logs_capture.append(message)

    result = initialize_and_process_question(question, status_cb_param=callback)

    print(f"SQL Query: {result.get('sql_query')}")
    print(f"Answer: {result.get('answer')}")
    if result.get('error'):
        print(f"Error: {result.get('error')}")
    print("--- End Test ---\n")
    return result, logs_capture

# --- Test Execution ---

print("=== Group 1: SQLite Tests ===")
setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}"
DB_TYPE="sqlite"
DB_PATH="test_data.sqlite"
DATABASE_URL="sqlite:///test_data.sqlite"
""")
res1, logs1 = run_test_question("Combien d'employés y a-t-il?", "SQLite - Count employees")
res2, logs2 = run_test_question("Quels sont tous les départements uniques?", "SQLite - List departments")
res3, logs3 = run_test_question("Qui travaille dans le département Engineering avec un salaire > 72000?", "SQLite - Employees in Engineering, salary > 72000")

print("\n=== Group 2: Invalid Queries (SQLite Backend) ===")
setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}"
DB_TYPE="sqlite"
DB_PATH="test_data.sqlite"
DATABASE_URL="sqlite:///test_data.sqlite"
""")
res4, logs4 = run_test_question("What is the meaning of life in SQL?", "Nonsensical question")
res5, logs5 = run_test_question("DROP TABLE employees;", "Attempt dangerous query (DROP)")
res5b, logs5b = run_test_question("SELECT * FROM employees; DELETE FROM employees WHERE id = 1;", "Attempt multiple statements")

print("\n=== Group 3: Error Handling Tests ===")
setup_env_file(f"""
GOOGLE_API_KEY="INVALID_KEY_FOR_ERROR_TEST"
DB_TYPE="sqlite"
DB_PATH="test_data.sqlite"
DATABASE_URL="sqlite:///test_data.sqlite"
""")
res6, logs6 = run_test_question("How many employees?", "Invalid API Key Test")

setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}"
DB_TYPE="sqlite"
DB_PATH="non_existent_db.sqlite"
DATABASE_URL="sqlite:///non_existent_db.sqlite"
""")
res7, logs7 = run_test_question("How many tables are there?", "Non-existent SQLite DB")

print("\n=== Group 4: PostgreSQL Connection Test ===")
setup_env_file(f"""
GOOGLE_API_KEY="{DUMMY_API_KEY}"
DB_TYPE="postgresql"
DB_USER="testuser"
DB_PASSWORD="testpass"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="testdb"
DATABASE_URL="postgresql+psycopg2://testuser:testpass@localhost:5432/testdb"
""")
res8, logs8 = run_test_question("How many users?", "PostgreSQL connection attempt (expect failure)")

print("\n=== Group 5: Cleared .env Test ===")
setup_env_file("") # Empty .env file
res9, logs9 = run_test_question("How many users?", "Cleared .env settings")

print("All tests finished.")
