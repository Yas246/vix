// examples/example.ts
import { askSqlDatabase, AskSqlDbParams, getSchemaInfo } from '../src'; // Adjust path if running from compiled dist
import { config } from 'dotenv';
import { SQLDatabase } from '@langchain/community/sql_db'; // For getSchemaInfo example
import { DataSource } from "typeorm"; // For getSchemaInfo example

config(); // Load .env variables from project root

async function main() {
    let params: AskSqlDbParams = {
        question: "How many active users are there?", // A simple question
        // dbType will be determined by environment or defaults
        // dbConnectionConfig will be determined by environment or defaults
        modelName: "gemini-pro", // specify a model
    };

    // Determine DB configuration from environment variables
    const dbTypeFromEnv = process.env.DB_TYPE as string | undefined;
    const databaseUrlFromEnv = process.env.DATABASE_URL as string | undefined;
    const dbPathFromEnv = process.env.DB_PATH as string | undefined;

    if (databaseUrlFromEnv) {
        params.dbConnectionConfig = databaseUrlFromEnv;
        // dbType can often be inferred, but explicit is good if known
        if (dbTypeFromEnv) params.dbType = dbTypeFromEnv;
        console.log(`Using DATABASE_URL: ${databaseUrlFromEnv}`);
    } else if (dbTypeFromEnv) {
        params.dbType = dbTypeFromEnv;
        if (dbTypeFromEnv === 'sqlite' && dbPathFromEnv) {
            // buildDbConnectionOptions in askSqlDatabase will pick up DB_PATH for sqlite
            console.log(`Using DB_TYPE: ${dbTypeFromEnv} with DB_PATH: ${dbPathFromEnv}`);
        } else {
            console.log(`Using DB_TYPE: ${dbTypeFromEnv} (ensure DB_HOST, etc. are set in .env)`);
        }
    } else {
        // Fallback to a temporary SQLite DB for easy example running if no other config is found
        console.warn("No DB configuration found in .env (DATABASE_URL or DB_TYPE). Falling back to temporary 'example.db' for SQLite demo.");
        params.dbType = 'sqlite';
        params.dbConnectionConfig = "sqlite:///./example.db";
    }

    if (!params.googleApiKey && !process.env.GOOGLE_API_KEY) {
        console.error("Error: GOOGLE_API_KEY is not set in .env and not provided in params.");
        return;
    }


    console.log(`\nRunning example with effective DB_TYPE: ${params.dbType || 'auto-detected'}`);
    if(typeof params.dbConnectionConfig === 'string') console.log(`Effective Connection URI (if any): ${params.dbConnectionConfig}`);

    try {
        const result = await askSqlDatabase(params);
        console.log("\n--- askSqlDatabase Result ---");
        console.log("Generated SQL:", result.generatedQuery);
        // console.log("Raw Query Result:", JSON.stringify(result.queryResult, null, 2)); // Can be verbose
        console.log("Answer:", result.answer);

        // Example for getSchemaInfo:
        // This requires setting up a SQLDatabase instance manually.
        console.log("\n--- getSchemaInfo Example ---");
        let dbForSchema: SQLDatabase | undefined = undefined;

        // Determine connection options for creating DataSource for getSchemaInfo
        let schemaDbType = params.dbType;
        let schemaDbConfig = params.dbConnectionConfig;

        if (typeof schemaDbConfig === 'string') { // URI
            schemaDbType = schemaDbType || detectDbTypeFromUriLocal(schemaDbConfig); // Use local helper or import
             if (!schemaDbType || schemaDbType === 'unknown') {
                console.warn("Cannot determine dbType for schema from URI, skipping getSchemaInfo.");
            } else {
                 const dataSource = new DataSource({ type: schemaDbType as any, url: schemaDbConfig });
                 dbForSchema = await SQLDatabase.fromDataSourceParams({ appDataSource: dataSource });
            }
        } else if (typeof schemaDbConfig === 'object') { // DataSourceOptions
             schemaDbType = schemaDbType || (schemaDbConfig as any).type;
             if (!schemaDbType) {
                console.warn("Cannot determine dbType for schema from config object, skipping getSchemaInfo.");
             } else {
                const dataSource = new DataSource(schemaDbConfig as any);
                dbForSchema = await SQLDatabase.fromDataSourceParams({ appDataSource: dataSource });
             }
        } else if (schemaDbType) { // dbType from env, needs other env vars
            // This case requires building full config, simplified for example
            if (schemaDbType === 'sqlite' && (process.env.DB_PATH || params.dbConnectionConfig === "sqlite:///./example.db")) {
                 const dataSource = new DataSource({ type: 'sqlite', database: process.env.DB_PATH || 'example.db' });
                 dbForSchema = await SQLDatabase.fromDataSourceParams({ appDataSource: dataSource });
            } else {
                console.log("Skipping getSchemaInfo: For non-URI/non-object config, full env setup (DB_HOST etc.) is needed to manually create DataSource.");
            }
        } else {
             console.log("Skipping getSchemaInfo as DB connection details for manual setup are unclear.");
        }


        if (dbForSchema) {
            const schema = await getSchemaInfo(dbForSchema, schemaDbType);
            console.log("Schema Information:", schema);
            if (dbForSchema.appDataSource?.isInitialized) {
                // await dbForSchema.appDataSource.destroy(); // Clean up connection
            }
        }

    } catch (error: any) {
        console.error("\nError in example:", error.message);
        if (error.stack) console.error(error.stack);
    }
}

// Helper to avoid importing from src/dbConnection for this example file if not desired
function detectDbTypeFromUriLocal(uri: string): string {
  if (!uri) return "unknown";
  const lowerUri = uri.toLowerCase();
  if (lowerUri.startsWith("sqlite")) return "sqlite";
  if (lowerUri.startsWith("postgres")) return "postgres";
  if (lowerUri.startsWith("mysql")) return "mysql";
  if (lowerUri.startsWith("mariadb")) return "mysql"; // MariaDB uses 'mysql' type in TypeORM
  if (lowerUri.startsWith("mssql")) return "mssql";
  if (lowerUri.startsWith("oracle")) return "oracle";
  return "unknown";
}

main();
