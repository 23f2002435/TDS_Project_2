"""
Main server module for the LLM Agent Project.
Entry point that runs the web server and defines API endpoints.
"""

from flask import Flask, request, jsonify
import os
import logging
from orchestrator import Orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize orchestrator
orchestrator = Orchestrator()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "llm-agent-project"})

@app.route('/api', methods=['POST'])
@app.route('/api/', methods=['POST'])
def analyze_data():
    """
    Main API endpoint for data analysis.
    Accepts questions file and optional data attachments.
    Returns analysis results in JSON format.
    """
    try:
        # Validate request: support 'questions' or 'questions.txt' as the field name
        questions_key = 'questions' if 'questions' in request.files else (
            'questions.txt' if 'questions.txt' in request.files else None
        )
        if not questions_key:
            return jsonify({"error": "No questions file provided. Expected field 'questions' or 'questions.txt'"}), 400

        questions_file = request.files[questions_key]
        if questions_file.filename == '':
            return jsonify({"error": "No questions file selected"}), 400
        
        # Read questions
        questions_content = questions_file.read().decode('utf-8')
        
        # Get optional data attachments
        data_files = []
        for key in request.files:
            if key != questions_key:
                data_file = request.files[key]
                if data_file.filename:
                    data_files.append({
                        'filename': data_file.filename,
                        'content': data_file.read()
                    })
        
        # Get optional URL parameter
        data_url = request.form.get('url', '')
        
        logger.info(f"Processing analysis request with {len(data_files)} data files and URL: {data_url}")
        
        # Process through orchestrator
        result = orchestrator.process_request(
            questions=questions_content,
            data_files=data_files,
            data_url=data_url
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting LLM Agent Project server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)