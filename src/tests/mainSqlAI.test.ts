// src/tests/mainSqlAI.test.ts
import { askSqlDatabase, AskSqlDbParams } from '../mainSqlAI'; // Adjust path
import { getDatabaseConnection } from '../dbConnection';
import { buildDbConnectionOptions } from '../databaseConfig';
import { ChatGoogleGenerativeAI } from '@langchain/google-genai';
import { SQLDatabase } from '@langchain/community/sql_db';
import { QuerySQLDataBaseTool } from '@langchain/community/tools/sql'; // Correct tool
import { validateSqlQuery } from '../security';

// Mock dependencies
jest.mock('../dbConnection');
jest.mock('../databaseConfig');
jest.mock('@langchain/google-genai');
jest.mock('@langchain/community/sql_db');
jest.mock('@langchain/community/tools/sql');
jest.mock('../security');

const mockGetDatabaseConnection = getDatabaseConnection as jest.Mock;
const mockBuildDbConnectionOptions = buildDbConnectionOptions as jest.Mock;
const mockChatGoogleGenerativeAI = ChatGoogleGenerativeAI as jest.Mock;
const mockSQLDatabase = SQLDatabase as jest.MockedClass<typeof SQLDatabase>;
const mockQuerySQLDataBaseTool = QuerySQLDataBaseTool as jest.MockedClass<typeof QuerySQLDataBaseTool>;
const mockValidateSqlQuery = validateSqlQuery as jest.Mock;

describe('askSqlDatabase', () => {
    let params: AskSqlDbParams;
    const OLD_ENV = process.env;

    beforeEach(() => {
        jest.clearAllMocks();
        process.env = { ...OLD_ENV, GOOGLE_API_KEY: 'test-api-key' }; // Ensure API key is set for mocks

        params = {
            question: "How many users are there?",
            dbType: "sqlite",
            dbConnectionConfig: { type: "sqlite", database: "test.db" }
        };

        // Setup default mock implementations
        mockBuildDbConnectionOptions.mockReturnValue({ type: "sqlite", database: "test.db" });

        const mockDbInstance = {
            dialect: "sqlite",
            getTableInfo: jest.fn().mockResolvedValue("CREATE TABLE users (id INTEGER, name TEXT)"),
            run: jest.fn().mockResolvedValue("[{\"COUNT(*)\":10}]"), // Mock for db.run if getSchemaInfo fallback is hit
        } as unknown as SQLDatabase;
        mockGetDatabaseConnection.mockResolvedValue(mockDbInstance);
        mockSQLDatabase.fromDataSourceParams.mockResolvedValue(mockDbInstance);


        (mockChatGoogleGenerativeAI.prototype as any).invoke = jest.fn()
            .mockResolvedValueOnce("SELECT COUNT(*) FROM users;") // First call for SQL generation
            .mockResolvedValueOnce("There are 10 users.");     // Second call for answer generation

        (mockQuerySQLDataBaseTool.prototype as any).invoke = jest.fn().mockResolvedValue("[{\"COUNT(*)\":10}]");

        mockValidateSqlQuery.mockReturnValue(true); // Assume query is valid by default
    });

    afterAll(() => {
        process.env = OLD_ENV;
    });

    it('should successfully process a question and return an answer', async () => {
        const result = await askSqlDatabase(params);

        expect(mockGetDatabaseConnection).toHaveBeenCalledWith({ type: "sqlite", database: "test.db" }, "sqlite");
        expect(mockChatGoogleGenerativeAI.prototype.invoke).toHaveBeenCalledTimes(2);
        expect(mockChatGoogleGenerativeAI.prototype.invoke).toHaveBeenNthCalledWith(1, expect.objectContaining({
            input: params.question,
            // table_info: "CREATE TABLE users (id INTEGER, name TEXT)", // This is part of the prompt construction now
            // dialect: "sqlite"
        }));
        expect(mockValidateSqlQuery).toHaveBeenCalledWith("SELECT COUNT(*) FROM users;", "sqlite");
        expect(mockQuerySQLDataBaseTool.prototype.invoke).toHaveBeenCalledWith("SELECT COUNT(*) FROM users;");
         expect(mockChatGoogleGenerativeAI.prototype.invoke).toHaveBeenNthCalledWith(2, expect.objectContaining({
            question: params.question,
            query: "SELECT COUNT(*) FROM users;",
            result: "[{\"COUNT(*)\":10}]",
            dialect: "sqlite"
        }));
        expect(result.answer).toBe("There are 10 users.");
        expect(result.generatedQuery).toBe("SELECT COUNT(*) FROM users;");
        expect(result.queryResult).toEqual("[{\"COUNT(*)\":10}]");
    });

    it('should use GOOGLE_API_KEY from params if provided', async () => {
        params.googleApiKey = 'param-api-key';
        await askSqlDatabase(params);
        expect(mockChatGoogleGenerativeAI).toHaveBeenCalledWith(expect.objectContaining({
            apiKey: 'param-api-key'
        }));
    });

    it('should throw error if GOOGLE_API_KEY is not found', async () => {
        delete process.env.GOOGLE_API_KEY;
        await expect(askSqlDatabase(params)).rejects.toThrow("Google API Key not provided or found in GOOGLE_API_KEY env variable.");
    });

    it('should handle dbConnectionConfig as URI string', async () => {
        params.dbConnectionConfig = "sqlite:///test.db";
        params.dbType = "sqlite"; // type needs to be explicit or detectable by mock

        // Mock SQLDatabase.fromUri if that path was taken, or adjust getDatabaseConnection mock
        // For this test, assuming SQLDatabase.fromDataSourceParams is used by getDatabaseConnection as per current impl.
        // The mock for SQLDatabase.fromDataSourceParams should handle the DataSource created from URI.

        await askSqlDatabase(params);
        // Check if getDatabaseConnection was called appropriately (indirectly testing URI handling)
        // The actual test here depends on how getDatabaseConnection handles a URI.
        // If it creates a DataSource and passes to SQLDatabase.fromDataSourceParams:
        expect(mockSQLDatabase.fromDataSourceParams).toHaveBeenCalled();
    });

    it('should use buildDbConnectionOptions if only dbType is provided', async () => {
        params.dbConnectionConfig = undefined;
        params.dbType = "postgresql"; // Change type to ensure buildDbConnectionOptions is used for this type

        const pgMockDbInstance = {
            dialect: "postgres",
            getTableInfo: jest.fn().mockResolvedValue("CREATE TABLE products (id SERIAL, name TEXT)"),
             run: jest.fn().mockResolvedValue("[]"),
        } as unknown as SQLDatabase;
        mockGetDatabaseConnection.mockResolvedValue(pgMockDbInstance); // new mock for this specific call path
        mockBuildDbConnectionOptions.mockReturnValueOnce({ type: "postgres", host: "localhost" });

        await askSqlDatabase(params);
        expect(mockBuildDbConnectionOptions).toHaveBeenCalledWith("postgresql");
        expect(mockGetDatabaseConnection).toHaveBeenCalledWith({ type: "postgres", host: "localhost" }, "postgresql");
    });

    it('should throw error if query validation fails', async () => {
        mockValidateSqlQuery.mockImplementation(() => {
            throw new Error("Disallowed keyword detected");
        });
        await expect(askSqlDatabase(params)).rejects.toThrow("Disallowed keyword detected");
    });

    it('should clean the generated SQL query', async () => {
        // Override LLM mock for this test to return a query with backticks and "sql"
        (mockChatGoogleGenerativeAI.prototype as any).invoke = jest.fn()
            .mockResolvedValueOnce("```sql\nSELECT * FROM test_table;\n```") // SQL generation
            .mockResolvedValueOnce("Done."); // Answer generation

        await askSqlDatabase(params);
        expect(mockValidateSqlQuery).toHaveBeenCalledWith("SELECT * FROM test_table;", "sqlite");
        expect(mockQuerySQLDataBaseTool.prototype.invoke).toHaveBeenCalledWith("SELECT * FROM test_table;");
    });

    // Add more tests:
    // - Different database types and their specific behaviors if any (e.g. Oracle connection string)
    // - What happens if getTableInfo returns empty or very limited info (testing the fallback in _createInternalSqlQueryChain)
    // - Error handling for database execution failures from queryTool.invoke
});
