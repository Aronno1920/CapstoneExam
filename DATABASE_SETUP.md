# Database Setup Guide

## Quick Fix for Connection Issues

The error you're seeing indicates that the application cannot connect to SQL Server. Here are the steps to fix it:

## 1. Check SQL Server Status

First, make sure SQL Server is running:

### Windows:
```cmd
# Check if SQL Server service is running
sc query MSSQLSERVER

# Start SQL Server service if not running
net start MSSQLSERVER
```

### Alternative: Use SQL Server Management Studio (SSMS)
- Open SSMS and try to connect to your SQL Server instance
- If you can't connect, SQL Server is not running or not configured properly

## 2. Install Required Components

### Install ODBC Driver 17 for SQL Server:
1. Download from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Install the driver on your system

### Install SQL Server (if not already installed):
1. Download SQL Server Express (free): https://www.microsoft.com/en-us/sql-server/sql-server-downloads
2. Install with default settings

## 3. Configure Database

### Option A: Use Windows Authentication (Recommended for local development)
1. Set `USE_WINDOWS_AUTH=true` in your configuration
2. Make sure your Windows user has access to SQL Server

### Option B: Use SQL Server Authentication
1. Set `USE_WINDOWS_AUTH=false` in your configuration
2. Set `DB_USERNAME=sa` and `DB_PASSWORD=your_password`
3. Make sure SQL Server is configured for mixed authentication

## 4. Create Database and Tables

Run the database initialization script:

```sql
-- Execute the script in docs/init_database.sql
-- This will create the database and all required tables
```

## 5. Test Connection

Run the setup script to test your connection:

```bash
python setup_database.py
```

## 6. Environment Configuration

Create a `.env` file in your project root with these settings:

```env
# Database Configuration
DB_SERVER=localhost
DB_PORT=1433
DB_NAME=AIExaminerDB
DB_USERNAME=sa
DB_PASSWORD=your_password_here
DB_DRIVER=ODBC Driver 17 for SQL Server
USE_WINDOWS_AUTH=false

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
```

## Common Issues and Solutions

### Issue: "Named Pipes Provider: Could not open a connection"
**Solution**: SQL Server is not running or not accessible
- Start SQL Server service
- Check if SQL Server is configured to accept remote connections
- Verify the server name and port

### Issue: "Login timeout expired"
**Solution**: Network or authentication issues
- Check if SQL Server is configured for the authentication method you're using
- Verify credentials
- Check firewall settings

### Issue: "Server is not found or not accessible"
**Solution**: SQL Server instance not found
- Verify the server name (try `localhost`, `127.0.0.1`, or your machine name)
- Check if SQL Server is running on the expected port (default: 1433)
- Try connecting with SQL Server Management Studio first

## Testing the Fix

After making these changes:

1. Run `python setup_database.py` to test the connection
2. Start your application: `python main.py`
3. Test the endpoint: `GET /question/all`

The connection should now work properly!
