// src/tests/databaseConfig.test.ts
import { buildDbConnectionOptions, DB_CONFIGS } from '../databaseConfig'; // Adjust path as necessary

describe('buildDbConnectionOptions', () => {
    const OLD_ENV = process.env;

    beforeEach(() => {
        jest.resetModules(); // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });

    afterAll(() => {
        process.env = OLD_ENV; // Restore old environment
    });

    it('should build correct options for sqlite', () => {
        process.env.DB_PATH = 'test.db';
        const options = buildDbConnectionOptions('sqlite');
        expect(options.type).toBe('sqlite');
        expect(options.database).toBe('test.db');
    });

    it('should throw error for sqlite if DB_PATH is missing', () => {
        expect(() => buildDbConnectionOptions('sqlite')).toThrowError(/Missing required environment variables.*DB_PATH/);
    });

    it('should build correct options for postgresql', () => {
        process.env.DB_HOST = 'localhost';
        process.env.DB_PORT = '5432';
        process.env.DB_USER = 'pguser';
        process.env.DB_PASSWORD = 'pgpassword';
        process.env.DB_NAME = 'pgdb';

        const options = buildDbConnectionOptions('postgresql');
        expect(options.type).toBe('postgres');
        expect(options.host).toBe('localhost');
        expect(options.port).toBe(5432);
        expect(options.user).toBe('pguser');
        expect(options.password).toBe('pgpassword');
        expect(options.database).toBe('pgdb');
    });

    it('should throw error for postgresql if required env vars are missing', () => {
        process.env.DB_HOST = 'localhost'; // Missing other vars
        expect(() => buildDbConnectionOptions('postgresql')).toThrowError(/Missing required environment variables/);
    });

    // Add more tests for other database types (mysql, mssql, etc.)
    // Example for mysql
    it('should build correct options for mysql', () => {
        process.env.DB_HOST = 'mysqlhost';
        process.env.DB_PORT = '3306';
        process.env.DB_USER = 'mysqluser';
        process.env.DB_PASSWORD = 'mysqlpass';
        process.env.DB_NAME = 'mysqldb';

        const options = buildDbConnectionOptions('mysql');
        expect(options.type).toBe('mysql');
        expect(options.host).toBe('mysqlhost');
        expect(options.port).toBe(3306);
        // ... and so on for other properties
    });


    it('should throw error for unsupported db type', () => {
        expect(() => buildDbConnectionOptions('unsupported_db')).toThrowError(/Unsupported database type: unsupported_db/);
    });

    // Test default port usage
    it('should use default port if DB_PORT is not set for postgresql', () => {
        process.env.DB_HOST = 'localhost';
        process.env.DB_USER = 'pguser';
        process.env.DB_PASSWORD = 'pgpassword';
        process.env.DB_NAME = 'pgdb';
        // DB_PORT is not set

        const options = buildDbConnectionOptions('postgresql');
        expect(options.port).toBe(DB_CONFIGS.postgresql.defaultPort);
    });
});
