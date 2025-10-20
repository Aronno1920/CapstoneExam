# AI Examiner System

**An AI-powered narrative answer grading system using Large Language Models (LLMs) for semantic understanding and automated evaluation.**

## 🌟 Overview

The AI Examiner System is a sophisticated solution for automatically grading narrative (essay-style) answers using advanced AI techniques. It employs Chain-of-Thought (CoT) reasoning and semantic analysis to understand the actual meaning of both ideal answers and student responses, providing fair, consistent, and detailed grading with comprehensive feedback.

### Key Features

- **🤖 Advanced AI Grading**: Uses GPT-4, Claude, or other powerful LLMs for semantic understanding
- **🔄 Chain-of-Thought Processing**: Structured reasoning approach for consistent and explainable grading
- **📊 Comprehensive Analysis**: Extracts key concepts, evaluates semantic similarity, and applies rubric-based scoring
- **📝 Detailed Feedback**: Provides constructive feedback with strengths, weaknesses, and improvement suggestions
- **⚡ REST API**: Easy integration with existing educational platforms
- **🎯 Bias Monitoring**: Built-in mechanisms to ensure fair and unbiased grading
- **📈 Scalable Architecture**: Supports both single and batch grading operations

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- OpenAI API key (for GPT models) OR Anthropic API key (for Claude models)
- pip package manager

### Installation

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables**
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env and add your API keys
OPENAI_API_KEY=your_openai_api_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
```

3. **Run the system**
```bash
# Start the REST API server
python main.py

# Or run the example usage
python examples/usage_example.py
```

## 📖 Quick Usage

### Python Example

```python
import asyncio
from src.models.schemas import IdealAnswer, StudentAnswer, GradingRubric, GradingCriteria
from src.services.grading_service import ai_examiner

# Create grading rubric
rubric = GradingRubric(
    subject="Physics",
    topic="Newton's Laws of Motion",
    criteria=[
        GradingCriteria(name="Understanding", description="Concept comprehension", max_points=100.0)
    ],
    total_max_points=100.0
)

# Define ideal answer
ideal_answer = IdealAnswer(
    question_id="physics_001",
    content="Newton's three laws describe forces and motion...",
    rubric=rubric,
    subject="Physics"
)

# Student answer
student_answer = StudentAnswer(
    student_id="STU001",
    question_id="physics_001",
    content="Newton has three laws about motion..."
)

# Grade the answer
async def grade():
    result = await ai_examiner.grade_answer(student_answer, ideal_answer)
    print(f"Score: {result.percentage:.1f}% - {result.detailed_feedback}")

asyncio.run(grade())
```

### REST API Example

```bash
# Start the server
python main.py

# Access the interactive docs
open http://localhost:8000/docs

# Grade an answer via API
curl -X POST "http://localhost:8000/grade" -H "Content-Type: application/json" -d '{
  "student_answer": {"student_id": "STU001", "question_id": "Q1", "content": "Answer text..."},
  "ideal_answer": {"question_id": "Q1", "content": "Ideal answer...", "subject": "Physics", "rubric": {...}}
}'
```

## 🏗️ System Architecture

The system implements the design principles you specified:

### 1. System Design & Tool Selection
- **Core LLM**: Supports GPT-4, Claude 3, and other powerful models
- **Grading Rubric**: Quantifiable criteria with points and weights
- **Prompting Framework**: Chain-of-Thought (CoT) for reasoning logic

### 2. Prompt Engineering
- **Expert Academic Examiner Role**: LLM adopts examiner persona
- **Ideal Answer Integration**: Comprehensive reference comparison
- **Chain-of-Thought Logic**: Step-by-step semantic analysis and scoring
- **Structured Output**: JSON format for consistent parsing

### 3. Deployment & Maintenance
- **REST API**: Scalable FastAPI implementation
- **Bias Monitoring**: Confidence scoring and audit trails
- **Explainability**: Detailed justifications for all scores

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `LLM_PROVIDER` | Provider (openai/anthropic) | openai |
| `LLM_MODEL` | Model to use | gpt-4 |
| `GRADING_TEMPERATURE` | Temperature (0.0-1.0) | 0.2 |
| `API_PORT` | API server port | 8000 |

## 📊 Grading Process

The system uses Chain-of-Thought reasoning with these steps:

1. **Semantic Understanding**: Extract key concepts from ideal answer
2. **Student Analysis**: Evaluate concept coverage and accuracy
3. **Concept Comparison**: Compare each concept with evidence
4. **Rubric Application**: Apply scoring criteria systematically
5. **Final Evaluation**: Generate comprehensive feedback

## 📋 API Endpoints

- `POST /grade` - Grade a single answer
- `POST /grade/batch` - Grade multiple answers
- `POST /analyze/concepts` - Extract key concepts
- `GET /health` - System health check
- `GET /examples/rubric` - Example grading rubric
- `GET /docs` - Interactive API documentation

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=src tests/
```

## 📈 Features

✅ **Core LLM Integration** (GPT-4, Claude)
✅ **Chain-of-Thought Prompting**
✅ **Semantic Analysis & Concept Extraction**
✅ **Rubric-based Scoring**
✅ **REST API with FastAPI**
✅ **Comprehensive Feedback**
✅ **Bias Monitoring & Confidence Scoring**
✅ **Batch Processing**
✅ **Interactive Documentation**
✅ **Example Usage Scripts**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

**Built for educators and students with AI-powered precision** 🎓
