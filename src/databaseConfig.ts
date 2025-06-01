import dotenv from 'dotenv';

dotenv.config();

export interface DbDriverConfig {
  driverName: string;
  defaultPort?: number;
  exampleUri: string;
  description: string;
  requiredEnv: string[];
}

export const DB_CONFIGS: Record<string, DbDriverConfig> = {
  sqlite: {
    driverName: 'sqlite3',
    exampleUri: 'sqlite:///path/to/your/database.db',
    description: 'SQLite local file-based database',
    requiredEnv: ['DB_PATH'],
  },
  postgresql: {
    driverName: 'pg',
    defaultPort: 5432,
    exampleUri: 'postgresql://user:password@host:port/database',
    description: 'PostgreSQL object-relational database system',
    requiredEnv: ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_NAME', 'DB_PORT'],
  },
  mysql: {
    driverName: 'mysql2',
    defaultPort: 3306,
    exampleUri: 'mysql://user:password@host:port/database',
    description: 'MySQL open-source relational database',
    requiredEnv: ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_NAME', 'DB_PORT'],
  },
  mariadb: {
    driverName: 'mysql2', // Typically uses the same driver as MySQL
    defaultPort: 3306,
    exampleUri: 'mariadb://user:password@host:port/database',
    description: 'MariaDB community-developed fork of MySQL',
    requiredEnv: ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_NAME', 'DB_PORT'],
  },
  mssql: {
    driverName: 'tedious',
    defaultPort: 1433,
    exampleUri: 'mssql://user:password@host:port/database',
    description: 'Microsoft SQL Server database',
    requiredEnv: ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_NAME', 'DB_PORT'],
  },
  oracle: {
    driverName: 'oracledb',
    defaultPort: 1521,
    exampleUri: 'oracle://user:password@host:port/service_name',
    description: 'Oracle Database system',
    requiredEnv: ['DB_USER', 'DB_PASSWORD', 'DB_CONNECTION_STRING', 'DB_NAME'], // DB_CONNECTION_STRING for Oracle
  },
};

export function listSupportedDatabases(): void {
  console.log("Supported Databases and their configurations:");
  for (const dbType in DB_CONFIGS) {
    const config = DB_CONFIGS[dbType];
    console.log(`\nType: ${dbType}`);
    console.log(`  Driver: ${config.driverName}`);
    console.log(`  Description: ${config.description}`);
    console.log(`  Example URI: ${config.exampleUri}`);
    console.log(`  Required Environment Variables: ${config.requiredEnv.join(', ')}`);
  }
}

export function buildDbConnectionOptions(dbType: string): any {
  const config = DB_CONFIGS[dbType];
  if (!config) {
    throw new Error(`Unsupported database type: ${dbType}`);
  }

  const missingEnvVars = config.requiredEnv.filter(envVar => !process.env[envVar]);
  if (missingEnvVars.length > 0) {
    throw new Error(`Missing required environment variables for ${dbType}: ${missingEnvVars.join(', ')}`);
  }

  if (dbType === 'sqlite') {
    return {
      type: 'sqlite',
      database: process.env.DB_PATH!,
    };
  }

  const commonOptions = {
    host: process.env.DB_HOST!,
    port: parseInt(process.env.DB_PORT || '', 10) || config.defaultPort,
    user: process.env.DB_USER!,
    password: process.env.DB_PASSWORD!,
    database: process.env.DB_NAME!,
  };

  switch (dbType) {
    case 'postgresql':
      return { type: 'postgres', ...commonOptions };
    case 'mysql':
    case 'mariadb':
      return { type: 'mysql', ...commonOptions };
    case 'mssql':
      return {
        type: 'mssql',
        ...commonOptions,
        options: {
          encrypt: true, // Required for Azure SQL and often for other MSSQL instances
          trustServerCertificate: true, // Adjust as per your security requirements
        },
      };
    case 'oracle':
      // For Oracle, connectionString is often preferred or required by the 'oracledb' driver.
      // The environment variable DB_CONNECTION_STRING should contain the full connection string.
      // Example: 'oracle://user:password@host:port/service_name'
      // Alternatively, you can use individual parameters if supported by your setup and LangChain.js
      // For now, let's assume DB_CONNECTION_STRING is primary for Oracle.
      if (!process.env.DB_CONNECTION_STRING) {
        // Fallback to individual parameters if DB_CONNECTION_STRING is not set,
        // though this might not be standard for oracledb.
        console.warn("DB_CONNECTION_STRING not set for Oracle, attempting to use individual parameters. This might not work as expected.");
        return {
            type: 'oracle', // This type name might need adjustment based on TypeORM/Langchain support
            host: process.env.DB_HOST,
            port: parseInt(process.env.DB_PORT || '', 10) || config.defaultPort,
            user: process.env.DB_USER,
            password: process.env.DB_PASSWORD,
            database: process.env.DB_NAME, // Or SID/Service Name depending on driver
            // connectionString: process.env.DB_CONNECTION_STRING, // If using connection string
        };
      }
      // If DB_CONNECTION_STRING is set, it's often used directly by the driver.
      // LangChain.js or TypeORM might handle this differently.
      // The `type` property here is for TypeORM. The actual connection might be
      // more complex or use a connection string directly.
      return {
        type: 'oracle', // This type name might need adjustment
        connectionString: process.env.DB_CONNECTION_STRING,
        // Include other parameters if necessary and supported, e.g., for thick client mode
        // libDir: process.env.ORACLE_LIB_DIR, // Example for Oracle Instant Client
      };
    default:
      throw new Error(`Database type ${dbType} connection logic not implemented.`);
  }
}
