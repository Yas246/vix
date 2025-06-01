import { SQLDatabase } from "@langchain/community/sql_db";
import { DataSource, DataSourceOptions } from "typeorm";
import { buildDbConnectionOptions } from "./databaseConfig"; // Assuming this is in the same directory or path is adjusted

export async function getDatabaseConnection(
  dbType: string,
  dbDetails?: any // Can be a connection URI or parameters object
): Promise<SQLDatabase> {
  let connectionOptions: DataSourceOptions;

  if (typeof dbDetails === 'string') {
    // If dbDetails is a URI string
    const detectedType = detectDbTypeFromUri(dbDetails);
    if (detectedType === 'unknown' || (dbType && dbType !== detectedType)) {
      console.warn(`Mismatch or unknown DB type from URI. Provided type: ${dbType}, Detected type: ${detectedType}. Using provided type: ${dbType || detectedType}`);
    }
    const typeToUse = (dbType || detectedType) as any; // Cast to any to satisfy DataSourceOptions['type']
    if (typeToUse === 'unknown') {
        throw new Error("Database type could not be determined from URI and was not explicitly provided.");
    }
    // Basic URI handling for SQLite
    if (typeToUse === 'sqlite') {
        connectionOptions = { type: 'sqlite', database: dbDetails.split('///')[1] };
    } else {
        // For other types, TypeORM typically expects a URL property for URI connections
        connectionOptions = { type: typeToUse, url: dbDetails };
    }
  } else if (dbDetails && typeof dbDetails === 'object') {
    // If dbDetails is an object of parameters
    // Ensure 'type' is included, as DataSourceOptions requires it.
    if (!dbDetails.type && !dbType) {
        throw new Error("Database 'type' must be provided in dbDetails or as a dbType argument.");
    }
    connectionOptions = { ...dbDetails, type: (dbDetails.type || dbType) as any };
  } else {
    // If no dbDetails, build from environment variables using buildDbConnectionOptions
    if (!dbType) {
        throw new Error("dbType must be provided if dbDetails is not specified.");
    }
    const builtOptions = buildDbConnectionOptions(dbType);
    connectionOptions = builtOptions as DataSourceOptions; // buildDbConnectionOptions should return DataSourceOptions compatible object
  }

  if (!connectionOptions.type) {
    throw new Error("Database type is missing in connection options.");
  }

  console.log("Attempting to connect with options:", connectionOptions);


  const appDataSource = new DataSource(connectionOptions);

  try {
    // Initialize the data source to ensure it's connectable
    // This step might not be strictly necessary if SQLDatabase.fromDataSourceParams handles initialization
    // await appDataSource.initialize(); // Temporarily commenting out to see if fromDataSourceParams is enough
    // console.log("Data source initialized successfully.");

    const db = await SQLDatabase.fromDataSourceParams({
      appDataSource,
      // customDescription: "Optional custom description for the database.", // Example
      // includesTables: ['user', 'product'], // Example: to include only specific tables
      // excludesTables: ['internal_logs'], // Example: to exclude specific tables
    });
    console.log("SQLDatabase instance created successfully.");
    return db;
  } catch (error) {
    console.error("Failed to create database connection:", error);
    // if (appDataSource.isInitialized) {
    //   await appDataSource.destroy();
    // }
    throw error;
  }
}

export function detectDbTypeFromUri(uri: string): string {
  if (!uri) return "unknown";
  const lowerUri = uri.toLowerCase();
  if (lowerUri.startsWith("sqlite")) return "sqlite";
  if (lowerUri.startsWith("postgres")) return "postgres";
  if (lowerUri.startsWith("mysql")) return "mysql"; // Covers mariadb for TypeORM typically
  if (lowerUri.startsWith("mariadb")) return "mysql"; // MariaDB uses 'mysql' type in TypeORM
  if (lowerUri.startsWith("mssql")) return "mssql";
  if (lowerUri.startsWith("oracle")) return "oracle";
  return "unknown";
}
