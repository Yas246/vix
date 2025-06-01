// Core functionality
export { askSqlDatabase, getSchemaInfo } from './mainSqlAI';
export type { AskSqlDbParams, AskSqlDbResult } from './mainSqlAI';

// Optional: Export key utilities for advanced users or for extending functionality.
// Deciding which to export depends on the intended library usage.
// For a minimal and clean API, the above might be sufficient.
// If users need more control, uncomment selected exports below:

// Database connection utilities
// export { getDatabaseConnection, detectDbTypeFromUri } from './dbConnection';
// export { buildDbConnectionOptions, listSupportedDatabases, DB_CONFIGS } from './databaseConfig';
// export type { DbDriverConfig } from './databaseConfig';

// Security utilities
// export { validateSqlQuery } from './security';

// Re-exporting key LangChain or other external types if they are part of the public function signatures
// or if users are expected to work with them directly.
// export { SQLDatabase } from '@langchain/community/sql_db';
// export { ChatGoogleGenerativeAI } from '@langchain/google-genai';
// export type { DataSourceOptions } from 'typeorm'; // If dbConnectionConfig as object is a key part of API

// For now, keeping the API surface minimal as per the subtask's refined goal.
// The primary use case is covered by askSqlDatabase.
// getSchemaInfo is a useful standalone utility.
