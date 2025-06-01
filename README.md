# Vix SQL AI Assistant TypeScript Package

## Description

This TypeScript package empowers your applications to interact with SQL databases using natural language. It leverages Google's Generative AI (Gemini) to translate user questions into SQL queries, executes them against the specified database, and returns both the raw results and a natural language answer. It supports a variety of SQL databases and includes basic security validation for the generated queries.

## Features

*   **Multi-Database Support:** Connects to SQLite, PostgreSQL, MySQL, MariaDB, MSSQL, and Oracle databases.
*   **Natural Language to SQL:** Uses Google Generative AI (Gemini models) to convert questions into SQL queries.
*   **Query Execution:** Executes the generated SQL queries against the target database.
*   **Natural Language Answers:** Provides answers in (French) natural language based on the query results.
*   **Security:** Includes validation for generated SQL queries to prevent common disallowed operations.

## Installation

```bash
npm install vix-sql-ai
```

## Prerequisites

*   **Node.js:** Version 18.x or higher is recommended.
*   **Environment Variables:**
    *   `GOOGLE_API_KEY`: Your Google API key for using Google Generative AI services.
    *   **Database Connection:** You can configure the database connection in one of two ways:
        1.  **Using `DATABASE_URL`:**
            *   `DATABASE_URL`: A full database connection URI (e.g., `postgresql://user:password@host:port/database` or `sqlite:///./my_data.db`).
        2.  **Using individual DB parameters (if `DATABASE_URL` is not set):**
            *   `DB_TYPE`: The type of your database (e.g., `sqlite`, `postgresql`, `mysql`, `mariadb`, `mssql`, `oracle`).
            *   `DB_HOST`: Database host (e.g., `localhost`).
            *   `DB_PORT`: Database port (e.g., `5432` for PostgreSQL, `3306` for MySQL/MariaDB).
            *   `DB_USER`: Database username.
            *   `DB_PASSWORD`: Database password.
            *   `DB_NAME`: Database name.
            *   `DB_PATH`: Required for SQLite if not using `DATABASE_URL` (e.g., `my_database.db`).
*   **Database Drivers:**
    *   The package lists common drivers like `sqlite3`, `pg`, `mysql2`, `tedious` (for MSSQL), and `oracledb` as dependencies.
    *   **Oracle (`oracledb`) Note:** Installation of `oracledb` can be complex and might require Oracle Instant Client. Please refer to the official [`oracledb` documentation](https://oracle.github.io/node-oracledb/INSTALL.html) for detailed setup instructions if you encounter issues.

## Basic Usage (TypeScript/JavaScript)

Here's a simple example of how to use `askSqlDatabase`:

```typescript
import { askSqlDatabase, AskSqlDbParams } from '@google/sql-ai-assistant'; // Use your actual package name
import { config } from 'dotenv';

config(); // Load .env variables (ensure .env file is in the root of your project)

async function main() {
    const params: AskSqlDbParams = {
        question: "How many users are registered in the system?",

        // Option 1: Using DB_TYPE (and other DB_* env vars like DB_HOST, DB_USER, etc., or DB_PATH for SQLite)
        // Ensure these are set in your .env file if you choose this option.
        dbType: process.env.DB_TYPE as string || 'sqlite',

        // Option 2: Providing a direct connection URI (DATABASE_URL from .env will be used if dbConnectionConfig is not set)
        // dbConnectionConfig: "sqlite:///./my_local_database.db",
        // dbType: 'sqlite', // Good to provide if URI is opaque, though the system attempts to detect it.

        // Option 3: Providing a connection options object (less common for direct use)
        // dbConnectionConfig: { type: 'sqlite', database: './my_local_database.db' },

        googleApiKey: process.env.GOOGLE_API_KEY, // Can be omitted if GOOGLE_API_KEY is set in .env
        // modelName: "gemini-1.5-flash" // Optional: to override default model (gemini-pro)
        // topK: 5 // Optional: to override default top_K (10) for SQL query row limit
    };

    // Specific handling for SQLite if DB_PATH is used via .env
    if (params.dbType === 'sqlite' && process.env.DB_PATH && !params.dbConnectionConfig) {
        // askSqlDatabase will use buildDbConnectionOptions which reads DB_PATH for sqlite
        console.log(`Using SQLite with DB_PATH: ${process.env.DB_PATH}`);
    } else if (!params.dbConnectionConfig && !process.env.DATABASE_URL && !process.env.DB_TYPE) {
        console.error("Error: No database configuration found. Please set DATABASE_URL or DB_TYPE and related vars in .env, or provide dbConnectionConfig.");
        return;
    }


    try {
        const result = await askSqlDatabase(params);
        console.log("Generated SQL:", result.generatedQuery);
        console.log("Query Result (first few rows):", result.queryResult ? (Array.isArray(result.queryResult) ? result.queryResult.slice(0, 5) : result.queryResult) : "No result");
        console.log("Answer:", result.answer);

    } catch (error) {
        console.error("Error:", error);
    }
}

main();
```

## API Reference

### `askSqlDatabase(params: AskSqlDbParams): Promise<AskSqlDbResult>`

The primary function to interact with your database using natural language.

*   **`AskSqlDbParams`**:
    *   `question: string`: The natural language question to ask the database.
    *   `dbType?: string`: The type of database (e.g., 'postgresql', 'mysql'). Required if `dbConnectionConfig` is an object without a `type` or if relying on environment variables other than `DATABASE_URL`.
    *   `dbConnectionConfig?: string | object`: Can be a database connection URI string or a TypeORM `DataSourceOptions` object. If not provided, the function attempts to use `DATABASE_URL` from environment variables, or `DB_TYPE` and associated `DB_*` variables.
    *   `googleApiKey?: string`: Your Google API Key. If not provided, `process.env.GOOGLE_API_KEY` is used.
    *   `modelName?: string`: (Optional) The Gemini model name to use (e.g., "gemini-pro", "gemini-1.5-flash"). Defaults to "gemini-pro".
    *   `topK?: number`: (Optional) The maximum number of rows to query for if not specified in the question. Defaults to 10.
*   **`AskSqlDbResult`**:
    *   `answer: string`: The natural language answer generated by the LLM.
    *   `generatedQuery: string`: The SQL query that was generated and executed.
    *   `queryResult?: any`: The raw result returned from the database query execution.

### `getSchemaInfo(db: SQLDatabase, dbType?: string): Promise<string>`

Retrieves schema information for the given database.

*   Requires an instantiated `SQLDatabase` object from `@langchain/community/sql_db`. You would typically create this using a `DataSource` from `typeorm`.
*   `dbType?: string`: Optional database type, can be used to help with specific schema retrieval logic (e.g., for PostgreSQL fallbacks). `db.dialect` is usually preferred.
*   Returns a string containing the schema information, potentially truncated for very large schemas.

**Example for `getSchemaInfo`:**
```typescript
import { SQLDatabase } from '@langchain/community/sql_db';
import { DataSource } from 'typeorm';
import { getSchemaInfo } from 'your-package-name'; // Assuming this path
import { config } from 'dotenv';

config();

async function showSchema() {
    // This setup is illustrative. You'd use your actual DB connection details.
    const dbUri = process.env.DATABASE_URL || "sqlite:///./example.db";
    const dbType = dbUri.split(":")[0] || "sqlite"; // Basic type detection

    const dataSource = new DataSource({
        type: dbType as any, // 'postgres', 'mysql', 'sqlite', etc.
        url: dbUri, // For URI-based connections
        // For non-URI:
        // database: dbType === 'sqlite' ? dbUri.replace('sqlite:///./', '') : process.env.DB_NAME,
        // host: process.env.DB_HOST,
        // port: parseInt(process.env.DB_PORT || '0'),
        // username: process.env.DB_USER,
        // password: process.env.DB_PASSWORD,
    });

    try {
        // await dataSource.initialize(); // Important for some TypeORM versions/setups
        const db = await SQLDatabase.fromDataSourceParams({ appDataSource: dataSource });
        const schema = await getSchemaInfo(db);
        console.log("Database Schema:", schema);
    } catch(err) {
        console.error("Error getting schema:", err);
    } finally {
        if (dataSource.isInitialized) {
            // await dataSource.destroy();
        }
    }
}
// showSchema();
```

## Error Handling

Functions in this package may throw errors for various reasons, including:
*   Invalid or missing database connection parameters.
*   Incorrect or missing `GOOGLE_API_KEY`.
*   Network issues.
*   SQL query validation failures (e.g., disallowed keywords).
*   Problems during query execution by the database.

It's recommended to wrap calls to package functions in `try...catch` blocks to handle potential errors gracefully.

## Testing

Comprehensive testing is crucial for ensuring the reliability and correctness of this package, especially given its interaction with external services (LLMs) and databases. Our testing strategy includes:

### Unit Tests

Unit tests focus on isolating and testing individual functions and modules.
*   **`src/databaseConfig.ts`**:
    *   Test `buildDbConnectionOptions` for various database types (SQLite, PostgreSQL, MySQL, etc.) with different environment variable combinations. Verify the correctness of the generated connection options objects.
    *   Test error handling for missing required environment variables.
*   **`src/dbConnection.ts`**:
    *   Test `detectDbTypeFromUri` with a variety of valid and invalid URI examples to ensure correct type detection.
    *   Unit testing `getDatabaseConnection` directly is challenging due to its reliance on `DataSource` and `SQLDatabase.fromDataSourceParams`. Tests here might focus on parameter validation before these external calls are made.
*   **`src/security.ts`**:
    *   Test `validateSqlQuery` with various valid SQL queries (SELECT statements).
    *   Test `validateSqlQuery` with invalid queries containing disallowed keywords (DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE, REPLACE).
    *   Test MSSQL-specific command blocking (EXEC, EXECUTE, SP_).
*   **`src/mainSqlAI.ts`**:
    *   Unit test any complex helper functions that might be refactored from the main `askSqlDatabase` flow.
    *   For `askSqlDatabase`, true unit testing is complex. The strategy involves mocking its primary dependencies:
        *   Mock `getDatabaseConnection` to return a pre-configured mock `SQLDatabase` instance.
        *   Mock methods of `SQLDatabase` such as `getTableInfo()`, `run()`, and `dialect` to return predictable values.
        *   Mock `ChatGoogleGenerativeAI` (or the specific LLM client) to return predefined responses for SQL query generation and final answer generation stages.
        *   With these mocks, test the orchestration logic of `askSqlDatabase`: ensure it correctly processes input parameters, calls its internal components in the right order, handles data transformations, and formats the final output as expected.

### Integration Tests

Integration tests verify the interaction between different parts of the system, including external databases and LLMs (under controlled conditions).
*   **Database Connection Tests:**
    *   For each supported database type (SQLite, PostgreSQL, MySQL, etc.), test the `getDatabaseConnection` function by connecting to a live (local or test-specific) database instance. This requires setting up test databases and potentially seeding them with sample data.
*   **End-to-End Flow Tests:**
    *   Test the complete `askSqlDatabase` flow with a connection to a real test database and potentially a live (but rate-limited or specific model endpoint) LLM.
    *   Example:
        1.  Connect to a test SQLite database with a predefined schema and data.
        2.  Ask a specific natural language question.
        3.  Verify that the generated SQL query is syntactically correct and semantically appropriate for the question and schema (potentially using snapshot testing for the query).
        4.  Verify the raw result returned by the database against expected values.
        5.  Check if the final natural language answer is coherent and accurately reflects the query result.
    *   These tests are valuable but can be slower and more expensive to run. They should be used for core scenarios and critical paths.

### Tooling

We recommend using a modern JavaScript/TypeScript test runner such as:
*   **Jest:** A popular and comprehensive testing framework.
*   **Vitest:** A newer, fast test runner compatible with Vite projects, but usable in any Node.js project.

To set up with Jest (example):
```bash
npm install jest @types/jest ts-jest --save-dev
```
Then, configure `jest.config.js` and add test scripts to `package.json`.

### Running Tests

Once testing tools are configured, tests can typically be run using:
```bash
npm test
```
Or for continuous testing during development:
```bash
npm run test:watch # (If watch script is configured)
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any bugs, features, or improvements. (Further details to be added if this becomes a public open-source project).

## License

This package is not yet licensed. (Consider adding an MIT or Apache 2.0 license if appropriate).
