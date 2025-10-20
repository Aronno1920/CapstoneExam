# AI Examiner System - Database Setup

This directory contains the complete database setup for the AI Examiner System using Microsoft SQL Server.

## 📋 Files Overview

- **`init_database.sql`** - Complete database initialization script
- **`connection_config.py`** - Database connection configuration
- **`test_connection.py`** - Database connection testing script
- **`README.md`** - This setup guide

## 🚀 Quick Setup

### Prerequisites

1. **Microsoft SQL Server** (2016 or later) or **SQL Server Express**
2. **Python 3.8+** with required packages:
   ```bash
   pip install sqlalchemy pyodbc
   ```
3. **ODBC Driver 17 for SQL Server** ([Download](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server))

### Step 1: Install SQL Server (if needed)

**Option A: SQL Server Express (Free)**
```bash
# Download and install SQL Server Express from Microsoft
# Enable mixed mode authentication during setup
```

**Option B: SQL Server Developer Edition (Free)**
```bash
# Download from Microsoft Developer Network
# Full featured version for development use
```

### Step 2: Configure Database Connection

Edit the environment variables or modify `connection_config.py`:

```bash
# For Windows Authentication (recommended for local development)
set USE_WINDOWS_AUTH=true
set DB_SERVER=localhost
set DB_PORT=1433

# For SQL Server Authentication
set USE_WINDOWS_AUTH=false
set DB_USERNAME=sa
set DB_PASSWORD=YourPassword123!
set DB_SERVER=localhost
set DB_PORT=1433
```

### Step 3: Run Database Setup Script

**Option A: Using SQL Server Management Studio (SSMS)**
1. Open SSMS and connect to your SQL Server instance
2. Open `init_database.sql`
3. Execute the script (F5)

**Option B: Using Command Line (sqlcmd)**
```bash
# Windows Authentication
sqlcmd -S localhost -E -i "database\init_database.sql"

# SQL Authentication
sqlcmd -S localhost -U sa -P YourPassword123! -i "database\init_database.sql"
```

**Option C: Using PowerShell**
```powershell
# Navigate to the database directory
cd F:\Project\CapstoneExam\database

# Run the script
Invoke-Sqlcmd -ServerInstance "localhost" -InputFile "init_database.sql" -Database "master"
```

### Step 4: Verify Setup

Run the test script to verify everything is working:

```bash
cd F:\Project\CapstoneExam
python database\test_connection.py
```

Expected output:
```
🚀 Starting AI Examiner Database Tests
============================================================

📋 Basic Connection
------------------------------
✅ Basic connection successful

📋 Database Exists
------------------------------
✅ Connected to database: AIExaminerDB

📋 Tables Exist
------------------------------
✅ All required tables exist

📋 Sample Data
------------------------------
✅ Sample data found:
   - Questions: 2
   - Key concepts: 9
   - Rubric criteria: 6

📋 Stored Procedures
------------------------------
✅ sp_GetQuestionComplete works
✅ sp_GetGradingStatistics works

📋 Views
------------------------------
✅ vw_QuestionSummary: 2 records
✅ vw_GradingPerformance: 0 records

📋 DatabaseManager
------------------------------
✅ DatabaseManager session created successfully
✅ Retrieved 2 questions using ORM

============================================================
📊 TEST SUMMARY
============================================================
✅ PASS Basic Connection
✅ PASS Database Exists
✅ PASS Tables Exist
✅ PASS Sample Data
✅ PASS Stored Procedures
✅ PASS Views
✅ PASS DatabaseManager

🎯 Results: 7/7 tests passed
🎉 All tests passed! Database is ready for use.
```

## 📊 Database Schema

### Core Tables

1. **`questions`** - Stores questions and their ideal answers
2. **`key_concepts`** - Key concepts extracted from ideal answers
3. **`rubric_criteria`** - Grading criteria for each question
4. **`student_answers`** - Student submitted answers
5. **`grading_results`** - AI grading results with scores and feedback
6. **`concept_evaluations`** - Detailed evaluation of each concept
7. **`grading_sessions`** - Batch grading session tracking
8. **`audit_logs`** - System operation audit trail

### Views

- **`vw_QuestionSummary`** - Question statistics and metadata
- **`vw_GradingPerformance`** - Grading performance metrics

### Stored Procedures

- **`sp_GetQuestionComplete`** - Retrieve complete question data
- **`sp_GetGradingStatistics`** - Get grading statistics for time period
- **`sp_CleanOldAuditLogs`** - Clean old audit log entries

## 🔧 Configuration Options

### Connection String Formats

**Windows Authentication:**
```
mssql+pyodbc://@localhost:1433/AIExaminerDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

**SQL Server Authentication:**
```
mssql+pyodbc://username:password@localhost:1433/AIExaminerDB?driver=ODBC+Driver+17+for+SQL+Server
```

**Azure SQL Database:**
```
mssql+pyodbc://username:password@server.database.windows.net:1433/AIExaminerDB?driver=ODBC+Driver+17+for+SQL+Server&encrypt=yes&trustServerCertificate=no
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_SERVER` | SQL Server hostname/IP | `localhost` |
| `DB_PORT` | SQL Server port | `1433` |
| `DB_NAME` | Database name | `AIExaminerDB` |
| `DB_DRIVER` | ODBC driver name | `ODBC Driver 17 for SQL Server` |
| `USE_WINDOWS_AUTH` | Use Windows authentication | `true` |
| `DB_USERNAME` | SQL Server username | `sa` |
| `DB_PASSWORD` | SQL Server password | `` |

## 🔍 Sample Data

The setup script includes sample data for testing:

### Physics Question (PHYS_001)
- **Topic:** Newton's Laws of Motion
- **Key Concepts:** 4 concepts (First Law, Second Law, Third Law, Examples)
- **Rubric:** 3 criteria (Understanding, Examples, Communication)

### History Question (HIST_001)
- **Topic:** World War II Causes
- **Key Concepts:** 5 concepts (Versailles, Economics, Totalitarianism, Diplomacy, Interconnections)
- **Rubric:** 3 criteria (Knowledge, Analysis, Communication)

## 🛠️ Troubleshooting

### Common Issues

**1. Connection Failed**
```
❌ Connection failed: (pyodbc.OperationalError) ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]...)
```
**Solutions:**
- Ensure SQL Server is running
- Check server name and port
- Verify authentication credentials
- Enable TCP/IP protocol in SQL Server Configuration Manager

**2. Database Does Not Exist**
```
❌ Database check failed: Cannot open database "AIExaminerDB"
```
**Solutions:**
- Run the `init_database.sql` script first
- Check if you have permission to create databases

**3. Missing Tables**
```
❌ Missing tables: questions, key_concepts, ...
```
**Solutions:**
- Re-run the `init_database.sql` script
- Check for SQL syntax errors in the script output

**4. ODBC Driver Not Found**
```
❌ Connection failed: ('01000', "[01000] [unixODBC][Driver Manager]Can't open lib 'ODBC Driver 17 for SQL Server'")
```
**Solutions:**
- Install ODBC Driver 17 for SQL Server
- Update the driver name in `connection_config.py`

### Performance Optimization

**For Large Datasets:**
1. Consider partitioning large tables
2. Monitor index usage and add custom indexes
3. Use the `sp_CleanOldAuditLogs` procedure regularly
4. Archive old grading results periodically

**For High Load:**
1. Use connection pooling
2. Configure appropriate timeout values
3. Consider read replicas for reporting queries

## 🔐 Security Considerations

### Production Setup

1. **Authentication:**
   - Use strong passwords for SQL authentication
   - Prefer Windows/Active Directory authentication
   - Create dedicated application users with minimal permissions

2. **Network Security:**
   - Enable SSL/TLS encryption
   - Use firewall rules to restrict database access
   - Consider VPN for remote connections

3. **Data Protection:**
   - Enable Transparent Data Encryption (TDE)
   - Regular backups with encryption
   - Implement audit logging for sensitive operations

### User Permissions

```sql
-- Create application user
CREATE LOGIN ai_examiner_app WITH PASSWORD = 'SecurePassword123!';
CREATE USER ai_examiner_user FOR LOGIN ai_examiner_app;

-- Grant minimal required permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON questions TO ai_examiner_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON key_concepts TO ai_examiner_user;
-- ... (other table permissions as needed)
```

## 📁 Backup and Recovery

### Regular Backups

```sql
-- Full backup
BACKUP DATABASE AIExaminerDB 
TO DISK = 'C:\Backups\AIExaminerDB_Full.bak'
WITH FORMAT, INIT;

-- Transaction log backup
BACKUP LOG AIExaminerDB 
TO DISK = 'C:\Backups\AIExaminerDB_Log.trn';
```

### Recovery

```sql
-- Restore from backup
RESTORE DATABASE AIExaminerDB 
FROM DISK = 'C:\Backups\AIExaminerDB_Full.bak'
WITH REPLACE;
```

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review SQL Server error logs
3. Run the test script for detailed diagnostics
4. Consult the main project README for additional help

---

**Happy coding!** 🎓✨