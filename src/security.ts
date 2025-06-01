// src/security.ts
export function validateSqlQuery(query: string, dbType: string): boolean {
    const dangerousKeywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'REPLACE'];
    const queryUpper = query.toUpperCase();

    for (const keyword of dangerousKeywords) {
        if (queryUpper.includes(keyword)) {
            // Instead of throwing an error, let's return false or an object indicating failure
            // This allows the caller to handle the validation result more gracefully.
            console.warn(`Disallowed keyword detected in query: ${keyword}`);
            throw new Error(`Disallowed keyword detected in query: ${keyword}`);
            // return false;
        }
    }

    // Specific checks for MSSQL
    if (dbType === "mssql") {
        const mssqlRestrictedPatterns = ['EXEC', 'EXECUTE', 'SP_'];
        for (const pattern of mssqlRestrictedPatterns) {
            if (queryUpper.includes(pattern)) {
                console.warn(`Disallowed MSSQL pattern detected: ${pattern}`);
                throw new Error(`Execution of ${pattern} is not allowed for MSSQL.`);
                // return false;
            }
        }
    }

    // Specific checks for PostgreSQL (example, can be expanded)
    if (dbType === "postgres" || dbType === "postgresql") {
        // Example: Disallow modifying system tables or calling certain admin functions
        // This is highly dependent on security requirements.
        // For now, let's keep it simple.
    }

    // Add more database-specific checks if necessary

    return true;
}
