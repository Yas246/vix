// src/tests/security.test.ts
import { validateSqlQuery } from '../security'; // Adjust path as needed

describe('validateSqlQuery', () => {
    const allowedQueries = [
        "SELECT * FROM users;",
        "SELECT name, email FROM customers WHERE id = 123;",
        "select count(*) from orders where order_date > '2023-01-01';"
    ];

    const disallowedKeywordsQueries = [
        "DROP TABLE users;",
        "DELETE FROM products WHERE id = 1;",
        "UPDATE customers SET email = 'test@example.com' WHERE id = 1;",
        "INSERT INTO logs (message) VALUES ('test');",
        "ALTER TABLE products ADD COLUMN new_col VARCHAR(255);",
        "CREATE INDEX idx_email ON users (email);",
        "TRUNCATE TABLE sessions;",
        "REPLACE INTO settings (id, value) VALUES (1, 'config');"
    ];

    const mssqlSpecificDisallowed = [
        "EXEC sp_configure 'show advanced options', 1;",
        "EXECUTE myProcedure;",
        "SELECT * FROM fn_myFunction(); -- Though this is a SELECT, EXEC/SP_ are the primary concern"
    ];

    allowedQueries.forEach(query => {
        it(`should allow valid SELECT query: ${query}`, () => {
            expect(() => validateSqlQuery(query, "postgres")).not.toThrow();
            expect(() => validateSqlQuery(query, "mysql")).not.toThrow();
            expect(() => validateSqlQuery(query, "sqlite")).not.toThrow();
            expect(() => validateSqlQuery(query, "mssql")).not.toThrow();
        });
    });

    disallowedKeywordsQueries.forEach(query => {
        const keyword = query.split(" ")[0].toUpperCase();
        it(`should block query with disallowed keyword ${keyword}: ${query}`, () => {
            expect(() => validateSqlQuery(query, "postgres")).toThrowError(`Disallowed keyword detected in query: ${keyword}`);
            expect(() => validateSqlQuery(query, "mssql")).toThrowError(`Disallowed keyword detected in query: ${keyword}`);
        });
    });

    it('should handle mixed case disallowed keywords', () => {
        expect(() => validateSqlQuery("DrOp TaBlE users;", "postgres")).toThrowError(/Disallowed keyword detected in query: DROP/);
    });

    mssqlSpecificDisallowed.forEach(query => {
        const pattern = query.match(/EXEC|EXECUTE|SP_/i)?.[0]?.toUpperCase();
        it(`should block MSSQL specific disallowed pattern ${pattern}: ${query}`, () => {
            expect(() => validateSqlQuery(query, "mssql")).toThrowError(`Execution of ${pattern} is not allowed for MSSQL.`);
        });
    });

    it('should allow EXEC/EXECUTE/SP_ in queries for non-MSSQL databases if not a disallowed keyword itself', () => {
        // Example: A query that coincidentally contains "execute" but is not a disallowed SQL verb itself.
        // This scenario is a bit contrived as EXECUTE is a command, but if it were part of a string in a SELECT for instance.
        // The main check is that the MSSQL specific block doesn't trigger for other DBs.
        const queryWithExecPattern = "SELECT 'execute this string' FROM data_table WHERE notes LIKE '%execute%';";
        expect(() => validateSqlQuery(queryWithExecPattern, "postgres")).not.toThrow();

        const queryWithSPPatternInComment = "SELECT * FROM users; -- SP_HELPTEXT users";
         expect(() => validateSqlQuery(queryWithSPPatternInComment, "postgres")).not.toThrow();
    });

    it('should pass valid MSSQL select query', () => {
         expect(() => validateSqlQuery("SELECT data FROM [My Table] WHERE id = @param;", "mssql")).not.toThrow();
    });

});
