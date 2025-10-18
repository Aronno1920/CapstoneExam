# CapstoneExam FastAPI Application

A FastAPI application built with Clean Architecture that supports multiple databases (SQL Server, MySQL, PostgreSQL, and MongoDB) for CRUD operations on Questions.

## Features

- **Clean Architecture**: Follows Robert C. Martin's Clean Architecture principles
- **Multiple Database Support**: SQL Server, MySQL, PostgreSQL, and MongoDB
- **CRUD Operations**: Complete Create, Read, Update, Delete operations for Questions
- **Search Functionality**: Text-based search across question content
- **Pagination**: Built-in pagination for list endpoints
- **Async/Await**: Full async support for better performance
- **Type Safety**: Pydantic models for request/response validation
- **Auto Documentation**: OpenAPI/Swagger documentation

## Question Model

The application manages questions with the following fields:

- `question_id`: Unique identifier (auto-generated)
- `set_id`: ID of the question set
- `category_id`: ID of the category
- `question`: The question text
- `narrative_answer`: Optional narrative answer
- `marks`: Points/marks for the question
- `is_update`: Whether the question has been updated
- `is_active`: Whether the question is active (for soft delete)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Project Structure (Flat Layout)

```
CapstoneExam/
├── domain/                     # Domain Layer (Clean Architecture)
│   ├── entities/              # Business entities
│   │   └── question.py
│   ├── repositories/          # Repository interfaces
│   │   └── question_repository.py
│   └── use_cases/            # Business logic/use cases
│       └── question_use_cases.py
├── infrastructure/            # Infrastructure Layer
│   ├── database/             # Database connections
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── factory.py
│   └── repositories/         # Repository implementations
│       ├── sql_question_repository.py
│       └── mongo_question_repository.py
├── presentation/             # Presentation Layer
│   ├── api/                 # FastAPI routes
│   │   ├── question_routes.py
│   │   └── dependencies.py
│   ├── schemas/             # Pydantic schemas
│   │   └── question_schemas.py
│   └── main_router.py       # Main API router
├── shared/                   # Shared utilities
│   └── config/
│       └── settings.py
├── main.py                   # Application entry point
├── create_tables.py         # Database setup script
├── requirements.txt         # Dependencies
└── .env.example            # Environment template
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure your database:

```env
# Set your database type
DATABASE_TYPE=postgresql  # Options: sqlserver, mysql, postgresql, mongodb

# Configure your specific database connection
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=capstoneexam
POSTGRESQL_USERNAME=postgres
POSTGRESQL_PASSWORD=your_password
```

### 3. Database Setup

```bash
python create_tables.py
```

### 4. Run the Application

```bash
python main.py
```

API available at: http://localhost:8000
Documentation: http://localhost:8000/docs

## API Endpoints

### Base URL: `/api/v1/questions`

- `POST /` - Create a new question
- `GET /{question_id}` - Get question by ID
- `GET /` - Get all questions (with pagination)
- `GET /set/{set_id}` - Get questions by set ID
- `GET /category/{category_id}` - Get questions by category ID
- `PUT /{question_id}` - Update a question
- `DELETE /{question_id}` - Soft delete a question
- `DELETE /{question_id}/permanent` - Permanently delete
- `POST /search` - Search questions by text

## Architecture

Follows Clean Architecture with:

1. **Domain Layer**: Business entities and rules
2. **Infrastructure Layer**: Database implementations
3. **Presentation Layer**: FastAPI routes and schemas
4. **Shared Layer**: Configuration and utilities

## Database Support

- **PostgreSQL**: `DATABASE_TYPE=postgresql`
- **MySQL**: `DATABASE_TYPE=mysql`
- **SQL Server**: `DATABASE_TYPE=sqlserver`
- **MongoDB**: `DATABASE_TYPE=mongodb`

Switch databases by changing the `DATABASE_TYPE` in your `.env` file.
