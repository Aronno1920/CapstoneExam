"""
Database connection configuration for AI Examiner System
"""
import os
from urllib.parse import quote_plus

# MSSQL Server Configuration
class DatabaseConfig:
    """Database connection configuration"""
    
    # Database settings - modify these for your environment
    SERVER = os.getenv('DB_SERVER', 'localhost')  # e.g., 'localhost' or '192.168.1.100'
    PORT = os.getenv('DB_PORT', '1433')
    DATABASE = os.getenv('DB_NAME', 'AIExaminerDB')
    DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    
    # Authentication methods
    # Option 1: Windows Authentication (recommended for development)
    USE_WINDOWS_AUTH = os.getenv('USE_WINDOWS_AUTH', 'true').lower() == 'true'
    
    # Option 2: SQL Server Authentication
    USERNAME = os.getenv('DB_USERNAME', 'sa')
    PASSWORD = os.getenv('DB_PASSWORD', 'abc@123')
    
    @classmethod
    def get_connection_string(cls) -> str:
        """
        Generate SQLAlchemy connection string for MSSQL Server
        
        Returns:
            str: SQLAlchemy connection string
        """
        if cls.USE_WINDOWS_AUTH:
            # Windows Authentication
            conn_str = (
                f"mssql+pyodbc://@{cls.SERVER}:{cls.PORT}/{cls.DATABASE}"
                f"?driver={quote_plus(cls.DRIVER)}"
                f"&trusted_connection=yes"
            )
        else:
            # SQL Server Authentication
            conn_str = (
                f"mssql+pyodbc://{cls.USERNAME}:{quote_plus(cls.PASSWORD)}"
                f"@{cls.SERVER}:{cls.PORT}/{cls.DATABASE}"
                f"?driver={quote_plus(cls.DRIVER)}"
            )
        
        return conn_str
    
    @classmethod
    def get_raw_connection_params(cls) -> dict:
        """
        Get raw connection parameters for direct pyodbc connection
        
        Returns:
            dict: Connection parameters
        """
        if cls.USE_WINDOWS_AUTH:
            return {
                'server': cls.SERVER,
                'port': cls.PORT,
                'database': cls.DATABASE,
                'driver': cls.DRIVER,
                'trusted_connection': 'yes'
            }
        else:
            return {
                'server': cls.SERVER,
                'port': cls.PORT,
                'database': cls.DATABASE,
                'uid': cls.USERNAME,
                'pwd': cls.PASSWORD,
                'driver': cls.DRIVER
            }


# Connection string templates for different scenarios
CONNECTION_TEMPLATES = {
    'windows_auth': (
        "mssql+pyodbc://@{server}:{port}/{database}"
        "?driver={driver}&trusted_connection=yes"
    ),
    'sql_auth': (
        "mssql+pyodbc://{username}:{password}@{server}:{port}/{database}"
        "?driver={driver}"
    ),
    'azure_sql': (
        "mssql+pyodbc://{username}:{password}@{server}:1433/{database}"
        "?driver=ODBC+Driver+17+for+SQL+Server"
        "&encrypt=yes&trustServerCertificate=no&connection timeout=30"
    )
}

# Example usage and documentation
if __name__ == "__main__":
    print("AI Examiner Database Configuration")
    print("=" * 50)
    print(f"Server: {DatabaseConfig.SERVER}")
    print(f"Port: {DatabaseConfig.PORT}")
    print(f"Database: {DatabaseConfig.DATABASE}")
    print(f"Driver: {DatabaseConfig.DRIVER}")
    print(f"Windows Auth: {DatabaseConfig.USE_WINDOWS_AUTH}")
    print("\nConnection String:")
    print(DatabaseConfig.get_connection_string())
    print("\nRaw Connection Parameters:")
    for key, value in DatabaseConfig.get_raw_connection_params().items():
        print(f"  {key}: {value}")