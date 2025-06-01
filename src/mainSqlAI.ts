import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { SQLDatabase } from "@langchain/community/sql_db";
import { QuerySQLDataBaseTool } from "@langchain/community/tools/sql"; // QuerySQLDataBaseTool is preferred
import { PromptTemplate } from "@langchain/core/prompts";
import { RunnableSequence, RunnablePassthrough, RunnablePick } from "@langchain/core/runnables";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { DataSource, DataSourceOptions } from "typeorm";
import { getDatabaseConnection, detectDbTypeFromUri } from "./dbConnection";
import { buildDbConnectionOptions, DB_CONFIGS } from "./databaseConfig";
import { validateSqlQuery } from "./security";

// Default LLM (can be overridden in askSqlDatabase)
const defaultLlm = new ChatGoogleGenerativeAI({
  apiKey: process.env.GOOGLE_API_KEY, // Ensure GOOGLE_API_KEY is in .env
  modelName: "gemini-pro",
});

// 1. SQL Query Generation Prompt (remains the same)
const SQL_QUERY_PROMPT_TEMPLATE = `You are a {dialect} expert. Given an input question, create a syntactically correct {dialect} query to run.
Unless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results.
You can order the results to return the most informative data as you deem best.
You can only use the tables provided below.
{table_info}

Question: {input}
SQLQuery:`;

const queryGenerationPrompt = new PromptTemplate({
  template: SQL_QUERY_PROMPT_TEMPLATE,
  inputVariables: ["dialect", "top_k", "table_info", "input"],
});

// 2. Answer Generation Prompt (remains the same)
const ANSWER_PROMPT_TEMPLATE = `You are an assistant expert in {dialect} databases.
Answer the user's question in French in a clear and structured way.
If no results are found, explain why constructively.
If the results are numerous, present them in an organized manner.
If the query has limits, mention it to the user.

Question: {question}
SQL Query ({dialect}): {query}
Result: {result}

Detailed Answer: `;

const answerPromptTemplate = new PromptTemplate({ // Renamed to avoid conflict
  template: ANSWER_PROMPT_TEMPLATE,
  inputVariables: ["question", "query", "result", "dialect"],
});

// Simplified SQL Query Generation Chain (used internally by askSqlDatabase)
function _createInternalSqlQueryChain(
    db: SQLDatabase,
    llmForQueryGen: ChatGoogleGenerativeAI,
    topK: number = 10
) {
    return RunnableSequence.from([
        RunnablePassthrough.assign({
            table_info: async () => {
                const info = await db.getTableInfo();
                if (!info || info.trim() === "") {
                    // Attempt to use getSchemaInfo as a fallback if db.getTableInfo() is empty
                    console.warn("db.getTableInfo() returned empty, trying getSchemaInfo as fallback.");
                    return getSchemaInfo(db);
                }
                return info;
            },
            dialect: () => db.dialect,
            top_k: () => topK,
        }),
        queryGenerationPrompt,
        llmForQueryGen,
        new StringOutputParser(),
    ]);
}


// The createFullChain might be deprecated in favor of askSqlDatabase or kept for advanced use.
// For now, let's assume askSqlDatabase is the primary interface.
// We can remove or comment out createFullChain if it's redundant with askSqlDatabase's logic.

/*
// Function to create the full processing chain (potentially for advanced use)
export async function createFullChain(
    db: SQLDatabase,
    llmForQueryGen: ChatGoogleGenerativeAI,
    llmForAnswer: ChatGoogleGenerativeAI,
    topK: number = 10
) {
    const writeQueryChain = _createInternalSqlQueryChain(db, llmForQueryGen, topK);
    const executeQueryTool = new QuerySQLDataBaseTool(db);

    return RunnableSequence.from([
        RunnablePassthrough.assign({ question: (input: { question: string }) => input.question }),
        RunnablePassthrough.assign({
            query: async (input: { question: string }) => writeQueryChain.invoke({ input: input.question }),
        }),
        RunnablePassthrough.assign({
            result: async (input: { query: string }) => {
                try {
                    validateSqlQuery(input.query, db.dialect);
                    return await executeQueryTool.invoke(input.query);
                } catch (e: any) {
                    console.error("Error executing SQL query:", e.message);
                    return `Error executing query: ${e.message}. Please check the generated SQL or the database connection.`;
                }
            },
            dialect: () => db.dialect,
        }),
        answerPromptTemplate,
        llmForAnswer,
        new StringOutputParser(),
    ]);
}
*/

// Main package interface
export interface AskSqlDbParams {
    question: string;
    dbType?: string;
    dbConnectionConfig?: string | DataSourceOptions; // URI string or TypeORM DataSourceOptions object
    googleApiKey?: string;
    modelName?: string; // e.g., "gemini-pro", "gemini-1.5-flash"
    topK?: number;
}

export interface AskSqlDbResult {
    answer: string;
    generatedQuery: string;
    queryResult?: any;
}

export async function askSqlDatabase(params: AskSqlDbParams): Promise<AskSqlDbResult> {
    const {
        question,
        dbType: providedDbType,
        dbConnectionConfig,
        googleApiKey,
        modelName = "gemini-pro",
        topK = 10
    } = params;

    const effectiveGoogleApiKey = googleApiKey || process.env.GOOGLE_API_KEY;
    if (!effectiveGoogleApiKey) {
        throw new Error("Google API Key not provided or found in GOOGLE_API_KEY env variable.");
    }

    const currentLlm = new ChatGoogleGenerativeAI({ apiKey: effectiveGoogleApiKey, modelName });

    let db: SQLDatabase;
    let actualDbType = providedDbType;

    if (dbConnectionConfig) {
        if (typeof dbConnectionConfig === 'string') { // URI provided
            actualDbType = actualDbType || detectDbTypeFromUri(dbConnectionConfig);
            if (!actualDbType || actualDbType === 'unknown') {
                throw new Error("Could not determine database type from URI. Please provide dbType.");
            }
            // Use SQLDatabase.fromUri for direct URI connection (Langchain way)
            // Note: This bypasses our custom getDatabaseConnection and buildDbConnectionOptions for URI case.
            // This is simpler for URI and aligns with LangChain's capabilities.
             const dataSource = new DataSource({ type: actualDbType as any, url: dbConnectionConfig });
             db = await SQLDatabase.fromDataSourceParams({ appDataSource: dataSource });
            // db = await SQLDatabase.fromUri(dbConnectionConfig); // This would be ideal if fully compatible
        } else { // Object configuration provided (DataSourceOptions)
            actualDbType = actualDbType || (dbConnectionConfig as DataSourceOptions).type as string;
            if (!actualDbType) {
                 throw new Error("dbType (or 'type' in dbConnectionConfig) must be provided for object configurations.");
            }
            // Our getDatabaseConnection expects (configObject, typeString)
            db = await getDatabaseConnection(dbConnectionConfig, actualDbType);
        }
    } else if (providedDbType) { // dbType provided, use env vars via buildDbConnectionOptions
        actualDbType = providedDbType;
        const connectionOptions = buildDbConnectionOptions(actualDbType);
        db = await getDatabaseConnection(connectionOptions, actualDbType);
    } else if (process.env.DATABASE_URL) { // Fallback to DATABASE_URL from env
        const dbUri = process.env.DATABASE_URL;
        actualDbType = detectDbTypeFromUri(dbUri);
        if (!actualDbType || actualDbType === 'unknown') {
            throw new Error("Could not determine database type from DATABASE_URL. Please provide dbType.");
        }
        // Similar to string dbConnectionConfig:
        const dataSource = new DataSource({ type: actualDbType as any, url: dbUri });
        db = await SQLDatabase.fromDataSourceParams({ appDataSource: dataSource });
        // db = await SQLDatabase.fromUri(dbUri);
    } else {
        throw new Error("Database connection configuration (dbConnectionConfig or DATABASE_URL) or dbType not provided.");
    }

    if (!actualDbType || !DB_CONFIGS[actualDbType]) {
        throw new Error(`Unsupported or unknown database type: ${actualDbType}`);
    }

    // Ensure db.dialect is set, if not, attempt to set it based on actualDbType.
    // SQLDatabase usually sets this, but good to have a fallback.
    if (!db.dialect) {
        console.warn("db.dialect not automatically set, attempting to set from actualDbType.");
        (db as any).dialect = actualDbType; // This is a workaround, ideally dialect is set by SQLDatabase
    }


    const queryGenerationChain = _createInternalSqlQueryChain(db, currentLlm, topK);
    let generatedQuery = await queryGenerationChain.invoke({ input: question });

    generatedQuery = generatedQuery.replace(/```(?:sql)?\s*/g, "").replace(/```/g, "").trim();
    if (!generatedQuery) {
        throw new Error("Generated SQL query was empty after cleaning.");
    }

    validateSqlQuery(generatedQuery, db.dialect);

    const executeQueryTool = new QuerySQLDataBaseTool(db);
    const queryResult = await executeQueryTool.invoke(generatedQuery);

    const answerGenerationChain = answerPromptTemplate.pipe(currentLlm).pipe(new StringOutputParser());
    const answer = await answerGenerationChain.invoke({
        question,
        query: generatedQuery,
        result: queryResult,
        dialect: db.dialect,
    });

    return {
        answer,
        generatedQuery,
        queryResult,
    };
}


// Example of how to use it (for testing purposes, not part of the export)
/*
async function testAskSqlDatabase() {
    // Ensure you have a .env file with GOOGLE_API_KEY and DB_PATH (for sqlite)
    // or other DB connection vars for other DB types.
    dotenv.config(); // Load .env file

    if (!process.env.DB_PATH && !process.env.DATABASE_URL) {
        console.error("Please set DB_PATH (for SQLite) or DATABASE_URL in your .env file for testing.");
        return;
    }

    let params: AskSqlDbParams;

    if (process.env.DB_PATH) { // Test with SQLite
        params = {
            question: "Combien y a-t-il d'utilisateurs avec le statut actif ?",
            // dbType: "sqlite", // Optional if dbConnectionConfig has type or using DATABASE_URL
            dbConnectionConfig: { // TypeORM DataSourceOptions for SQLite
                type: "sqlite",
                database: process.env.DB_PATH,
            }
        };
        console.log("Testing with SQLite config object...");
    } else { // Test with DATABASE_URL (e.g. postgresql)
         params = {
            question: "How many users are there?",
            // dbType is not strictly needed if DATABASE_URL's prefix is parsable by detectDbTypeFromUri
            // and SQLDatabase.fromUri or equivalent can handle it.
            // However, our current setup with DataSource for URI still benefits from type.
            // dbType: "postgresql", // Example
         };
         console.log("Testing with DATABASE_URL (ensure it's set in .env)...");
    }


    try {
        const result = await askSqlDatabase(params);
        console.log("Generated Query:", result.generatedQuery);
        console.log("Query Result:", result.queryResult);
        console.log("Final Answer:", result.answer);

        // Test getSchemaInfo
        // Need to create a DB connection first to pass to getSchemaInfo
        // This is a bit redundant if askSqlDatabase did it internally, but for isolated test:
        let dbForSchema: SQLDatabase;
        if (params.dbConnectionConfig && typeof params.dbConnectionConfig === 'object') {
            dbForSchema = await getDatabaseConnection(params.dbConnectionConfig, (params.dbConnectionConfig as any).type);
        } else if (process.env.DATABASE_URL){
            const type = detectDbTypeFromUri(process.env.DATABASE_URL);
            const ds = new DataSource({type: type as any, url: process.env.DATABASE_URL});
            dbForSchema = await SQLDatabase.fromDataSourceParams({appDataSource: ds});
        } else {
            throw new Error("Cannot establish DB for getSchemaInfo test without config.")
        }
        const schema = await getSchemaInfo(dbForSchema);
        console.log("\nSchema Information:\n", schema);


    } catch (error) {
        console.error("Error during askSqlDatabase test:", error);
    }
}

// import dotenv from 'dotenv'; // Make sure dotenv is imported if you run test
// testAskSqlDatabase();
*/


export async function getSchemaInfo(db: SQLDatabase, dbType?: string /* optional, db.dialect could be used */): Promise<string> {
    console.log("Fetching database schema information...");
    // This function implementation remains the same as previously defined.
    // It's correctly placed and exported.
    // ... (implementation from previous step) ...
    try {
        let schemaInfo = await db.getTableInfo();

        if (schemaInfo && schemaInfo.trim().length > 10) {
            return schemaInfo.length > 2000 ? schemaInfo.substring(0, 2000) + "..." : schemaInfo;
        } else {
            const dialectToUse = dbType || db.dialect;
            if (dialectToUse === "postgres" || dialectToUse === "postgresql") {
                console.log("Limited schema info from getTableInfo(), attempting PostgreSQL specific query for public tables...");
                try {
                    const tablesResult = await db.run(
                        `SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' ORDER BY table_name, ordinal_position LIMIT 50;`
                    );
                    const formattedResult = typeof tablesResult === 'string' ? tablesResult : JSON.stringify(tablesResult, null, 2);
                    if (!formattedResult || formattedResult.trim().length === 0) {
                        return "Could not retrieve detailed schema information using specific PostgreSQL query (no results or empty). Standard schema access might be restricted.";
                    }
                    return `Public tables and columns (PostgreSQL - fallback query):\n${formattedResult}`;
                } catch (e: any) {
                    console.error("Error fetching detailed PostgreSQL schema via fallback:", e.message);
                    return "Could not retrieve detailed schema information via fallback. Standard schema access might be restricted.";
                }
            }
            return "Schema information is limited or unavailable through standard methods. The database might be empty or permissions too restrictive.";
        }
    } catch (e: any) {
        console.error("Error accessing schema with db.getTableInfo():", e.message);
        return `Error accessing schema: ${e.message}. Permissions might be insufficient.`;
    }
}
