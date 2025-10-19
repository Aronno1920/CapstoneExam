-- Reset AI Examiner Database
USE master;
GO

-- Drop database if it exists
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'AIExaminerDB')
BEGIN
    ALTER DATABASE AIExaminerDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE AIExaminerDB;
    PRINT 'Database AIExaminerDB dropped successfully.';
END
ELSE
BEGIN
    PRINT 'Database AIExaminerDB does not exist.';
END
GO