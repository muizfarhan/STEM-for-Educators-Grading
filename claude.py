
import sys
import subprocess
import json
import os
import re
import base64
import time

# Install Dependencies
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "anthropic", "python-dotenv"])

import anthropic
from dotenv import load_dotenv

def grade_student_submission(rubric_b64: str, submission_b64: str, client: anthropic.Client) -> str:
    
    static_instructions = """You are an expert academic grader. Evaluate the student's submission (Document 2) against the provided grading rubric (Document 1).

CRITICAL INSTRUCTIONS:
1. Provide a final total score as an INTEGER.
2. Provide a score for each criterion as an INTEGER (e.g., 5, not "5/5").
3. Provide exactly 5 sentences justifying your reasoning.
4. Output a valid JSON object matching the exact schema below. You MUST wrap the JSON in standard markdown formatting (i.e., ```json ... ```).
REQUIRED JSON SCHEMA:
{
  "totalscore": 0,
  "criteria": [
    {"criterion": "Real World Problems", "criteriascore": 0},
    {"criterion": "Context Integration", "criteriascore": 0},
    {"criterion": "Stated learning outcomes of overall unit", "criteriascore": 0},
    {"criterion": "Science concepts (NCP 2022)", "criteriascore": 0},
    {"criterion": "Mathematics concepts (NCP 2022)", "criteriascore": 0},
    {"criterion": "Technology as outcome of EDP", "criteriascore": 0},
    {"criterion": "Assessments aligned with outcomes", "criteriascore": 0},
    {"criterion": "Explicit opportunity to use EDP", "criteriascore": 0},
    {"criterion": "Plan & test prototype", "criteriascore": 0},
    {"criterion": "Redesign prototype", "criteriascore": 0},
    {"criterion": "Collaboration/teamwork", "criteriascore": 0},
    {"criterion": "Communicate concepts/solutions", "criteriascore": 0},
    {"criterion": "Lesson-specific driving questions", "criteriascore": 0},
    {"criterion": "Varied pedagogies/tasks", "criteriascore": 0},
    {"criterion": "Evidence-based reasoning", "criteriascore": 0},
    {"criterion": "Connections to design challenge", "criteriascore": 0},
    {"criterion": "Apply technology tools", "criteriascore": 0},
    {"criterion": "Resources/materials per lesson", "criteriascore": 0},
    {"criterion": "Promoting STEM careers", "criteriascore": 0}
  ],
  "comments": "Your exactly 5-sentence justification goes here."
}"""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": static_instructions
                    },
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": rubric_b64
                        },
                        "cache_control": {"type": "ephemeral"} # caching the rubric and the main prompt
                    },
                    {
                        "type": "text",
                        "text": "Here is the student submission (Document 2):"
                    },
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": submission_b64
                        }
                    }
                ]
            }
        ]
    )
    return response.content[0].text


def encode_pdf(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def process_llm_evaluation(raw_output: str, json_file_path: str, filename: str) -> str:
    """
    Extracts a JSON block from an LLM output string, sanitizes it, 
    injects the source filename, appends it to a JSON file, and returns the cleaned text.
    """

    pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
    match = pattern.search(raw_output)
    
    if not match:
        print(f"  [!] Error: No JSON block found in the output for {filename}.")
        return raw_output
        
    raw_json_str = match.group(1)
    sanitized_json_str = raw_json_str.replace('\xa0', ' ')
    
    try:
        new_evaluation = json.loads(sanitized_json_str)
    except json.JSONDecodeError as e:
        print(f"  [!] Error parsing JSON for {filename}: {e}")
        return raw_output
    
    new_evaluation["filename"] = filename

    cleaned_output = pattern.sub("", raw_output).strip()
    
    if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
        with open(json_file_path, "r", encoding="utf-8") as f:
            try:
                current_data = json.load(f)
                if not isinstance(current_data, list):
                    current_data = [current_data]
            except json.JSONDecodeError:
                current_data = []
    else:
        current_data = []

    current_data.append(new_evaluation)
    
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(current_data, f, indent=2, ensure_ascii=False)
        
    return cleaned_output
if __name__ == "__main__":
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Client(api_key=api_key)

    rubric_path = "Rubric.pdf"
    src_dir = "src"
    output_json = "results.json"

    print("Encoding static rubric...")
    rubric_b64 = encode_pdf(rubric_path)

    pdf_files = [f for f in os.listdir(src_dir) if f.lower().endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF(s) in '{src_dir}'. Starting batch evaluation...\n")

    for filename in pdf_files:
        file_path = os.path.join(src_dir, filename)
        print(f"Evaluating: {filename}")
        
        solution_b64 = encode_pdf(file_path)
        raw_output = grade_student_submission(rubric_b64, solution_b64, client)
        remaining_text = process_llm_evaluation(raw_output, output_json, filename)
        
        if remaining_text:
            print(f"  [w] Extraction complete, but unparsed text remains: {remaining_text[:50]}...")
        else:
            print(f"  [+] Successfully processed and saved {filename}")
        time.sleep(3)
            
    print("\nBatch evaluation complete.")
