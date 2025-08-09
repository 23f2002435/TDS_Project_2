"""
Orchestrator module - Central controller managing the workflow.
Coordinates between different modules to process user requests.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from llm_handler import LLMHandler
from tool_executor import ToolExecutor
from code_executor import CodeExecutor
from string import Template

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Central controller that manages the sequence of operations:
    1. Initial analysis and triage
    2. Task breakdown
    3. Data sourcing
    4. Metadata extraction
    5. Code generation
    6. Local execution and correction loop
    7. Final output generation
    """
    
    def __init__(self):
        self.llm_handler = LLMHandler()
        self.tool_executor = ToolExecutor()
        self.code_executor = CodeExecutor()
        self.max_correction_attempts = 3
    
    def process_request(self, questions: str, data_files: List[Dict], data_url: str = "") -> Dict[str, Any]:
        """
        Main processing pipeline for incoming requests.
        
        Args:
            questions: User's questions as text
            data_files: List of uploaded files with filename and content
            data_url: Optional URL for data source
            
        Returns:
            Dict containing the analysis results in JSON format
        """
        try:
            logger.info("Starting request processing pipeline")
            
            # Step 1: Request reception and triage
            data_source_type = self._analyze_data_source(questions, data_files, data_url)
            logger.info(f"Identified data source type: {data_source_type}")
            
            # If the question contains a URL, extract it early
            if data_source_type == "url_in_text":
                extracted_url = self._extract_url_from_text(questions)
                if extracted_url:
                    data_url = extracted_url
                    logger.info(f"Extracted URL from questions: {data_url}")
            
            # Step 2: Task breakdown
            task_plan = self._get_task_breakdown(questions)
            logger.info("Generated task breakdown plan")
            
            # Step 3: Data sourcing
            raw_data = self._source_data(data_source_type, data_files, data_url, task_plan)
            logger.info("Data sourcing completed")
            
            # Step 4: Metadata extraction
            metadata = self._extract_metadata(raw_data, data_source_type)
            logger.info("Metadata extraction completed")
            
            # Step 5: Code generation
            generated_code = self._generate_code(questions, metadata)
            logger.info("Code generation completed")
            
            # Step 6: Local execution and correction loop
            execution_result = self._execute_with_correction(generated_code, raw_data)
            logger.info("Code execution completed")
            
            # Step 7: Final output generation
            final_output = self._format_final_output(execution_result, questions)
            logger.info("Request processing completed successfully")
            
            return final_output
            
        except Exception as e:
            logger.error(f"Error in processing pipeline: {str(e)}")
            return {
                "status": "error",
                "message": f"Processing failed: {str(e)}",
                "results": []
            }
    
    def _analyze_data_source(self, questions: str, data_files: List[Dict], data_url: str) -> str:
        """Determine the nature of the data source."""
        if data_url and data_url.strip():
            return "url"
        elif data_files:
            return "file"
        elif "http" in questions.lower() or "www." in questions.lower():
            return "url_in_text"
        else:
            return "text_only"
    
    def _get_task_breakdown(self, questions: str) -> Dict[str, Any]:
        """Get structured task breakdown from LLM."""
        prompt_template = self._load_prompt_template("1_task_breakdown")
        prompt = Template(prompt_template).safe_substitute(questions=questions)
        
        response = self.llm_handler.call_llm(prompt)
        
        try:
            # Try to parse as JSON, fallback to text plan
            task_plan = json.loads(response)
        except json.JSONDecodeError:
            task_plan = {"plan": response, "steps": []}
        
        return task_plan
    
    def _source_data(self, data_source_type: str, data_files: List[Dict], 
                     data_url: str, task_plan: Dict[str, Any]) -> Any:
        """Source data based on the identified type and task plan."""
        if data_source_type == "url" or data_source_type == "url_in_text":
            # Extract URL if it's in text
            if data_source_type == "url_in_text" and not data_url:
                # Fallback: try extracting from the task plan if URL not already found
                data_url = self._extract_url_from_text(task_plan.get("plan", ""))
            
            return self.tool_executor.execute_tool("web_scraper", {"url": data_url})
        
        elif data_source_type == "file":
            # Process uploaded files
            processed_files = []
            for file_info in data_files:
                processed_data = self.tool_executor.execute_tool("data_reader", {
                    "filename": file_info["filename"],
                    "content": file_info["content"]
                })
                processed_files.append(processed_data)
            return processed_files
        
        else:
            # Text-only analysis
            return {"type": "text", "content": ""}
    
    def _extract_metadata(self, raw_data: Any, data_source_type: str) -> Dict[str, Any]:
        """Extract compact metadata from raw data."""
        return self.tool_executor.execute_tool("data_inspector", {
            "data": raw_data,
            "source_type": data_source_type
        })
    
    def _generate_code(self, questions: str, metadata: Dict[str, Any]) -> str:
        """Generate Python code based on questions and metadata."""
        prompt_template = self._load_prompt_template("2_code_generation")
        prompt = Template(prompt_template).safe_substitute(
            questions=questions,
            metadata=json.dumps(metadata, indent=2)
        )
        
        return self.llm_handler.call_llm(prompt)
    
    def _execute_with_correction(self, code: str, raw_data: Any = None) -> Dict[str, Any]:
        """Execute code with correction loop if needed."""
        attempts = 0
        current_code = code

        # Inject data into the code if provided
        if raw_data is not None:
            data_json = json.dumps(raw_data, default=str)
            # Provide metadata as a Python object parsed from JSON when raw_data is a dict; otherwise None
            metadata_json = json.dumps(raw_data, default=str) if isinstance(raw_data, dict) else 'null'
            data_injection = f"""
# Data injection
import json
data = json.loads(r'''{data_json}''')
metadata = json.loads(r'''{metadata_json}''')

# User code starts here
"""
            current_code = data_injection + current_code

        while attempts < self.max_correction_attempts:
            try:
                # Pre-clean code and validate syntax before attempting to run
                current_code = self.code_executor.prepare_code(current_code)
                syntax_check = self.code_executor.validate_code_syntax(current_code)
                if not syntax_check.get("valid", False):
                    attempts += 1
                    logger.warning(
                        f"Code syntax invalid, attempt {attempts}: {syntax_check.get('error','Invalid code')}"
                    )
                    if attempts < self.max_correction_attempts:
                        current_code = self._correct_code(
                            current_code,
                            syntax_check.get("error", "Invalid Python code. Return only Python code."),
                        )
                        continue
                    else:
                        return {"success": False, "error": syntax_check.get("error", "Invalid code"), "output": ""}

                # Execute only when syntax is valid
                result = self.code_executor.execute_code(current_code)
                if result["success"]:
                    return result
                else:
                    # Attempt correction on runtime error
                    attempts += 1
                    logger.warning(f"Code execution failed, attempt {attempts}: {result['error']}")
                    if attempts < self.max_correction_attempts:
                        current_code = self._correct_code(current_code, result["error"])
                    else:
                        return result

            except Exception as e:
                attempts += 1
                logger.error(f"Execution error, attempt {attempts}: {str(e)}")
                if attempts < self.max_correction_attempts:
                    current_code = self._correct_code(current_code, str(e))
                else:
                    return {"success": False, "error": str(e), "output": ""}

        return {"success": False, "error": "Max correction attempts exceeded", "output": ""}
    
    def _correct_code(self, faulty_code: str, error_message: str) -> str:
        """Use LLM to correct faulty code."""
        prompt_template = self._load_prompt_template("3_code_correction")
        prompt = Template(prompt_template).safe_substitute(
            code=faulty_code,
            error=error_message
        )
        
        return self.llm_handler.call_llm(prompt)
    
    def _format_final_output(self, execution_result: Dict[str, Any], 
                           original_questions: str):
        """Format the final output into required JSON structure."""
        if execution_result["success"]:
            # Try to parse output as JSON array, fallback to string
            output = execution_result["output"]
            try:
                # Look for JSON array pattern in the output
                import re
                json_match = re.search(r'\[.*\]', output, re.DOTALL)
                if json_match:
                    parsed_results = json.loads(json_match.group())
                    if isinstance(parsed_results, list):
                        results = parsed_results
                    else:
                        results = [output]
                else:
                    results = [output]
            except (json.JSONDecodeError, ValueError):
                results = [output]

            # If the instructions ask for a JSON array response, return the array directly
            if 'json array' in original_questions.lower():
                return results

            return {
                "status": "success",
                "questions": original_questions,
                "results": results,
                "metadata": {
                    "execution_success": True,
                    "processing_pipeline": "completed"
                }
            }
        else:
            return {
                "status": "error",
                "questions": original_questions,
                "error": execution_result["error"],
                "metadata": {
                    "execution_success": False,
                    "processing_pipeline": "failed_at_execution"
                }
            }
    
    def _load_prompt_template(self, template_name: str) -> str:
        """Load prompt template from prompts directory."""
        template_path = os.path.join("prompts", f"{template_name}.txt")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt template {template_name} not found, using default")
            return self._get_default_prompt(template_name)
    
    def _get_default_prompt(self, template_name: str) -> str:
        """Provide default prompts if templates are missing."""
        defaults = {
            "1_task_breakdown": """
            Analyze the following questions and create a structured plan to answer them:
            
            Questions: {questions}
            
            Please provide a step-by-step plan in JSON format with the following structure:
            {{
                "plan": "Brief description of the overall approach",
                "steps": ["Step 1", "Step 2", "Step 3", ...]
            }}
            """,
            "2_code_generation": """
            Based on the following questions and data metadata, write Python code to perform the analysis:
            
            Questions: {questions}
            
            Data Metadata: {metadata}
            
            Please write clean, executable Python code that answers the questions using the provided data structure.
            Include all necessary imports and ensure the code is self-contained.
            """,
            "3_code_correction": """
            The following Python code has an error. Please fix it:
            
            Code:
            {code}
            
            Error:
            {error}
            
            Please provide the corrected version of the code.
            """
        }
        return defaults.get(template_name, "")
    
    def _extract_url_from_text(self, text: str) -> str:
        """Extract URL from text content."""
        import re
        url_pattern = r'https?://[^\s<>"{{}}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls[0] if urls else ""