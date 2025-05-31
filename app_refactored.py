import os
import re
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Callable, List
import json
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, insert # Added for __main__

# LangChain imports
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

class DatabaseConfig:
    DB_CONFIGS = {
        "sqlite": {"driver": "sqlite", "port": None, "required_env": ["DB_PATH"]},
        "postgresql": {"driver": "postgresql+psycopg2", "port": 5432, "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]},
        "mysql": {"driver": "mysql+pymysql", "port": 3306, "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]},
        "mariadb": {"driver": "mariadb+pymysql", "port": 3306, "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]},
        "mssql": {"driver": "mssql+pyodbc", "port": 1433, "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME", "ODBC_DRIVER"]},
        "oracle": {"driver": "oracle+cx_oracle", "port": 1521, "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_SERVICE_NAME"]}
    }

    @classmethod
    def build_uri_from_env(cls, db_type: str, status_cb: Callable[[str], None]) -> str:
        db_type_lower = db_type.lower()
        if db_type_lower not in cls.DB_CONFIGS:
            status_cb(f"Error: DB type '{db_type_lower}' not in DB_CONFIGS.")
            raise ValueError(f"Unsupported DB type: {db_type_lower}")

        config = cls.DB_CONFIGS[db_type_lower]

        if db_type_lower == "sqlite":
            db_path = os.getenv("DB_PATH")
            if not db_path: raise ValueError("DB_PATH not set for SQLite.")
            status_cb(f"SQLite path: {db_path}")
            return f"sqlite:///{db_path}"

        missing_vars = [var for var in config["required_env"] if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing env vars for {db_type_lower}: {', '.join(missing_vars)}")

        user, password = os.getenv("DB_USER"), os.getenv("DB_PASSWORD")
        host, port = os.getenv("DB_HOST"), os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        driver_name = config["driver"]

        if db_type_lower in ["postgresql", "mysql", "mariadb"]:
            return f"{driver_name}://{user}:{password}@{host}:{port}/{db_name}"
        elif db_type_lower == "mssql":
            odbc_driver = os.getenv("ODBC_DRIVER", "").replace(" ", "+")
            if not odbc_driver: raise ValueError("ODBC_DRIVER not set for MSSQL.")
            return f"{driver_name}://{user}:{password}@{host}:{port}/{db_name}?driver={odbc_driver}"
        elif db_type_lower == "oracle":
            service_name = os.getenv("DB_SERVICE_NAME")
            if not service_name: raise ValueError("DB_SERVICE_NAME not set for Oracle.")
            return f"{driver_name}://{user}:{password}@{host}:{port}/?service_name={service_name}"

        status_cb(f"Error: Could not construct URI for {db_type_lower}.")
        raise ValueError(f"URI construction failed for {db_type_lower}")


def get_database_connection(status_cb: Callable[[str], None]) -> tuple[SQLDatabase, str]:
    load_dotenv(override=True)
    db_uri = os.getenv("DATABASE_URL")
    detected_db_type = "unknown"

    if db_uri:
        status_cb(f"Attempting connection via DATABASE_URL...")
        uri_lower = db_uri.lower()
        if "sqlite" in uri_lower: detected_db_type = "sqlite"
        elif "postgresql" in uri_lower: detected_db_type = "postgresql"
        # (other DB types) ...
        else: status_cb("Warning: Could not determine DB type from DATABASE_URL.")
    else:
        detected_db_type = os.getenv("DB_TYPE", "sqlite").lower()
        status_cb(f"Attempting connection via DB_TYPE: {detected_db_type.upper()}")
        db_uri = DatabaseConfig.build_uri_from_env(detected_db_type, status_cb)
        status_cb(f"Built URI: {db_uri.split('@')[0]}@***" if '@' in db_uri else db_uri)

    status_cb(f"Creating SQLDatabase object for {detected_db_type}...")
    try:
        engine_args = {}
        if detected_db_type != "sqlite":
            engine_args["connect_args"] = {"connect_timeout": 5}
        engine = create_engine(db_uri, **engine_args)
        db = SQLDatabase(engine=engine, view_support=True)
        status_cb("SQLDatabase object created.")
        return db, detected_db_type
    except Exception as e:
        status_cb(f"Error creating SQLDatabase: {str(e)[:150]}")
        raise ConnectionError(f"Failed to create SQLDatabase from URI: {e}")


def get_answer_prompt_template(db_type: str) -> PromptTemplate:
    template_str = """Answer the user's question based on the SQL query and its result.
Database type: {db_type_upper}
Question: {{question}}
SQL Query: {{query}}
Query Result: {{result}}
Answer (in French, be concise and clear): """
    return PromptTemplate.from_template(template_str.format(db_type_upper=db_type.upper()))

def validate_sql_query(query: str, db_type: str) -> bool:
    query_upper = query.upper()
    write_keywords = ['DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE ', 'TRUNCATE ', 'REPLACE ', 'DROP ']
    if any(keyword in query_upper for keyword in write_keywords):
        raise ValueError(f"Potentially unsafe keyword detected: {keyword.strip()}")
    if db_type == "mssql" and any(cmd in query_upper for cmd in ['EXEC ', 'EXECUTE ', 'SP_']):
        raise ValueError("Execution of stored procedures/dynamic SQL might be restricted.")
    if query.count(';') > 1 or (query.count(';') == 1 and not query.strip().endswith(';')):
        raise ValueError("Multiple SQL statements or unterminated query detected.")
    if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
         raise ValueError("Query must be a SELECT statement.")
    return True

def initialize_and_process_question(question_text: str, status_cb_param: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    logs: List[str] = []
    log = status_cb_param if status_cb_param else lambda msg: logs.append(msg)

    llm_bypass_active = os.getenv("VIX_TEST_MODE_NO_LLM") == "true"
    if llm_bypass_active:
        log("LLM Bypass Mode is ACTIVE. SQL and answers will be dummies.")

    try:
        log("Initializing Vix process...")
        load_dotenv(override=True); log("Environment variables reloaded.")

        if not llm_bypass_active:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key: raise ValueError("GOOGLE_API_KEY not found in environment.")
            log("Google API Key check: OK.")
        else:
            log("Google API Key check: SKIPPED (LLM Bypass Mode).")


        db, detected_db_type = get_database_connection(log)
        log(f"Database connection established for type: {detected_db_type.upper()}.")

        try:
            db.run("SELECT 1")
            log("DB test query (SELECT 1) successful.")
        except Exception as db_test_exc:
            log(f"DB test query failed: {str(db_test_exc)[:100]}. Attempting to proceed...")

        generated_sql = ""
        if llm_bypass_active:
            # Fix for f-string SyntaxError: move replace out
            safe_question_snippet = question_text[:50].replace("'", "''")
            generated_sql = f"SELECT 'LLM Bypass: Query for: {safe_question_snippet}' AS status, 1 AS value;"
            log(f"LLM Bypass: Using dummy SQL: {generated_sql}")
        else:
            llm_model_name = "gemini-pro"
            llm = ChatGoogleGenerativeAI(model=llm_model_name, temperature=0.0, convert_system_message_to_human=True)
            log(f"LLM initialized with model: {llm_model_name}.")
            write_query_chain = create_sql_query_chain(llm, db)
            log("SQL query generation chain created.")
            generated_sql_output = write_query_chain.invoke({"question": question_text})
            generated_sql = generated_sql_output if isinstance(generated_sql_output, str) else generated_sql_output.get("query", str(generated_sql_output))
            if not generated_sql or not isinstance(generated_sql, str):
                raise ValueError(f"Failed to generate a valid SQL query string. Output: {generated_sql_output}")
            log(f"Raw SQL query generated: {generated_sql[:200]}...")

        cleaned_sql = re.sub(r"```(?:\w+\w*)?\s*", "", generated_sql).replace("```", "").strip()
        cleaned_sql = ' '.join(cleaned_sql.split())
        log(f"Cleaned SQL query: {cleaned_sql[:200]}...")

        validate_sql_query(cleaned_sql, detected_db_type)
        log("SQL query security validation: OK.")

        execute_query_tool = QuerySQLDataBaseTool(db=db)
        log("SQL query execution tool created/referenced.")
        log(f"Executing SQL query on {detected_db_type.upper()}...")
        query_result = execute_query_tool.invoke({"query": cleaned_sql})
        log(f"Query executed. Result length: {len(str(query_result)) if query_result is not None else 'N/A'}.")

        final_natural_answer = ""
        if llm_bypass_active:
            safe_question_snippet_ans = question_text[:50].replace("'", "''") # also escape for this string
            final_natural_answer = f"LLM Bypass: Dummy answer for '{safe_question_snippet_ans}'. DB Result (first 100 chars): {str(query_result)[:100]}"
            log(f"LLM Bypass: Using dummy natural language answer.")
        else:
            if 'llm' not in locals():
                 llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.0, convert_system_message_to_human=True)
            answer_prompt = get_answer_prompt_template(detected_db_type)
            log("Answer prompt template created.")
            final_answer_chain = answer_prompt | llm | StrOutputParser()
            final_natural_answer = final_answer_chain.invoke({
                "question": question_text, "query": cleaned_sql, "result": query_result
            })
            log("Final natural language answer generated.")

        return {
            "sql_query": cleaned_sql, "result": query_result, "answer": final_natural_answer,
            "logs": logs, "error": None
        }

    except Exception as e:
        log(f"Error during Vix processing: {type(e).__name__} - {str(e)}")
        import traceback
        error_trace = traceback.format_exc(limit=2)
        log(f"Traceback (simplified): {error_trace}")
        return {
            "sql_query": None, "result": None, "answer": None,
            "logs": logs, "error": f"{type(e).__name__}: {str(e)}\n{error_trace}"
        }

if __name__ == '__main__':
    def _cli_callback(message): print(f"[CLI_TEST_LOG] {message}")

    os.environ["VIX_TEST_MODE_NO_LLM"] = "true"
    print("Running self-test for initialize_and_process_question IN LLM BYPASS MODE...")

    if not os.getenv("DB_PATH") and not os.getenv("DATABASE_URL"):
        dummy_db_path = "vix_selftest_bypass.db"
        if not os.path.exists(dummy_db_path):
            engine_cli = create_engine(f"sqlite:///{dummy_db_path}")
            meta = MetaData()
            users_table = Table('users', meta, Column('id', Integer, primary_key=True), Column('name', String(50)))
            meta.create_all(engine_cli)
            with engine_cli.connect() as conn:
                conn.execute(insert(users_table).values(name="Bypass User"))
                conn.commit()
            print(f"Created dummy SQLite DB for testing LLM Bypass: {dummy_db_path}")
        os.environ["DB_PATH"] = dummy_db_path
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DATABASE_URL"] = ""

    if not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "BYPASS_MODE_KEY_NOT_USED"

    test_question = "How many users are there in 'bypass' mode?" # Changed question slightly for clarity

    result = initialize_and_process_question(test_question, status_cb_param=_cli_callback)
    print("\n--- Self-Test Result (LLM Bypass Mode) ---")
    if result["error"]: print(f"Error: {result['error']}")
    else:
        print(f"SQL Query: {result['sql_query']}")
        print(f"Raw Result: {str(result.get('result','N/A'))[:200]}...") # Added get with default
        print(f"Natural Answer: {result['answer']}")
    print("--- End Self-Test ---")

    del os.environ["VIX_TEST_MODE_NO_LLM"]
    if os.environ.get("DB_PATH") == "vix_selftest_bypass.db" and os.path.exists("vix_selftest_bypass.db"):
        print(f"Dummy DB vix_selftest_bypass.db was used.")
