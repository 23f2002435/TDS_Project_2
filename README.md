# LLM Agent Project

An intelligent data analysis agent powered by Large Language Models that can automatically analyze data from various sources and generate Python code to answer user questions.

## Features

- **Multi-source Data Processing**: Handles data from web URLs, uploaded files (CSV, Excel, JSON, text), and direct text input
- **Intelligent Task Breakdown**: Uses LLM to break down complex user questions into structured analysis plans
- **Automated Code Generation**: Generates Python code for data analysis based on questions and data metadata
- **Safe Code Execution**: Executes generated code in a controlled environment with security restrictions
- **Error Correction Loop**: Automatically fixes code errors using LLM feedback
- **REST API Interface**: Simple HTTP API for integration with other applications

## Architecture

The project follows a modular architecture with the following components:

- **main.py**: Web server and API endpoints
- **orchestrator.py**: Central controller managing the workflow
- **llm_handler.py**: Communication with external LLM APIs
- **tool_executor.py**: Dispatcher for local tools
- **code_executor.py**: Safe Python code execution
- **tools/**: Collection of specialized tools
  - **web_scraper.py**: Web content extraction
  - **data_inspector.py**: Data structure analysis
- **prompts/**: LLM prompt templates
- **outputs/**: Temporary directory for generated files

## Installation

### Local Setup

1. Clone the repository:
```bash
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Google Generative AI (Gemini) credentials:
```env
GOOGLE_API_KEY=<YOUR_GEMINI_API_KEY>
LLM_MODEL=gemini-1.5-flash      # default model (override if needed)
MAX_TOKENS=800                  # optional
TEMPERATURE=0.7                 # optional
MAX_RETRIES=3                   # optional
RETRY_DELAY=1                   # optional (seconds)
CODE_EXECUTION_TIMEOUT=120      # optional (seconds)
```

5. Run the application:
```bash
python main.py             # loads .env automatically via python-dotenv
```

### Docker Setup

1. Build the Docker image:
```bash
docker build -t llm-agent-project .
```

2. Run the container:
```bash
docker run -p 5000:5000 --env-file .env llm-agent-project
```

## Configuration

Create a `.env` file and configure the following variables:

### Required Configuration

- `GOOGLE_API_KEY` – Your Google Generative AI (Gemini) API key. Obtain one from [Google AI Studio](https://aistudio.google.com/).

### Optional Configuration

- `LLM_MODEL` – Gemini model name (default: `gemini-1.5-flash`)
- `MAX_TOKENS` – Max output tokens per request (default: 800)
- `TEMPERATURE` – Sampling temperature (default: 0.7)
- `MAX_RETRIES` – Number of retries for LLM calls (default: 3)
- `RETRY_DELAY` – Base delay between retries in seconds (default: 1)
- `CODE_EXECUTION_TIMEOUT` – Sandbox timeout in seconds (default: 120)
- `PORT`, `DEBUG` – Flask server settings

## API Usage

### Health Check

```bash
GET /health
```

Response:
```json
{
    "status": "healthy",
    "service": "llm-agent-project"
}
```

### Data Analysis

```bash
POST /analyze
Content-Type: multipart/form-data
```

Parameters:
- `questions` (file, required): Text file containing questions to analyze
- `url` (form field, optional): URL to analyze web data
- Additional files (optional): Data files to analyze (CSV, Excel, JSON, text)

Example using curl:
```bash
curl -X POST http://localhost:5000/analyze \
  -F "questions=@questions.txt" \
  -F "data=@dataset.csv" \
  -F "url=https://example.com/data"
```

Response:
```json
{
    "status": "success",
    "questions": "What are the main trends in the data?",
    "results": "Analysis results and insights",
    "metadata": {
        "execution_success": true,
        "processing_pipeline": "completed"
    }
}
```

## Workflow

1. **Request Reception**: API receives questions and optional data sources
2. **Task Breakdown**: LLM creates structured analysis plan
3. **Data Sourcing**: Tools fetch data from URLs or process uploaded files
4. **Metadata Extraction**: Data structure is analyzed and summarized
5. **Code Generation**: LLM generates Python analysis code
6. **Execution**: Code is executed safely with error handling
7. **Correction Loop**: Errors are automatically fixed using LLM
8. **Output**: Results are formatted and returned as JSON

## Security Features

- **Code Sandboxing**: Generated code runs in isolated environment
- **Import Restrictions**: Only safe libraries are allowed
- **Function Blocking**: Dangerous functions are blocked
- **Timeout Protection**: Code execution has time limits
- **Input Validation**: All inputs are validated and sanitized

## Supported Data Sources

### Web Sources
- HTML pages with tables and structured content
- JSON APIs
- CSV data served over HTTP
- Plain text content

### File Uploads
- CSV files
- Excel files (.xlsx, .xls)
- JSON files
- Text files

### Analysis Capabilities
- Descriptive statistics
- Data visualization
- Trend analysis
- Statistical testing
- Data cleaning and preprocessing
- Custom analysis based on user questions

## Development

### Project Structure
```
Project_TDS 2 2/
├── main.py                 # Main server
├── orchestrator.py         # Central controller
├── llm_handler.py         # LLM communication
├── tool_executor.py       # Tool dispatcher
├── code_executor.py       # Code execution
├── tools/                 # Specialized tools
│   ├── __init__.py
│   ├── web_scraper.py
│   └── data_inspector.py
├── prompts/               # LLM prompt templates
│   ├── 1_task_breakdown.txt
│   ├── 2_code_generation.txt
│   └── 3_code_correction.txt
├── outputs/               # Temporary files
├── requirements.txt       # Dependencies
├── Dockerfile            # Container configuration

└── README.md            # This file
```

### Adding New Tools

1. Create a new tool in the `tools/` directory
2. Implement the required interface with an `execute()` function
3. Add the tool to `tool_executor.py`
4. Update the tool registry

### Customizing Prompts

Edit the prompt templates in the `prompts/` directory to customize LLM behavior:
- `1_task_breakdown.txt`: Controls how tasks are planned
- `2_code_generation.txt`: Controls code generation
- `3_code_correction.txt`: Controls error correction

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure `GOOGLE_API_KEY` is set in your `.env` file
2. **Import Errors**: Install all dependencies with `pip install -r requirements.txt`
3. **Port Conflicts**: Change the `PORT` environment variable
4. **Timeout Errors**: Increase `CODE_EXECUTION_TIMEOUT` for complex analyses

### Logs

The application logs important events and errors. Check the console output for debugging information.

### Testing

Run tests with:
```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For questions and support, please open an issue in the repository.