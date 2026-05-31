# Automated LLM-Based Grading Pipeline

This repository contains an automated grading pipeline that utilizes Anthropic's Claude Opus 4.8 to evaluate student submissions against a standardized grading rubric. The system batch-processes PDF documents, strictly enforces a JSON output schema, and aggregates the results into a single file.

### Prerequisites

Make sure your device has Python installed. If you haven't already installed the script will install the following dependencies for you:

```bash
pip install anthropic
pip install python-dotenv
```
### API Key Configuration (.env)

For security and convenience, this project uses a `.env` file to manage the Anthropic API key. Create a new file and name it exactly `.env` and add your Anthropic API key like this (no spaces around the equals sign):

```bash
ANTHROPIC_API_KEY="your_actual_api_key_goes_here"
```

# Usage Instructions

- Prepare the Rubric: Ensure the master grading rubric is named Rubric.pdf and is located in the root directory.
- Stage Submissions: Place all student submission files into the src/ directory. All files must be in PDF format.
- Execute the Pipeline: Run the claude.py file using `python claude.py`
- Review Results: Once execution is complete, the aggregated grades, criteria breakdowns, and evaluator comments will be available in the output file (e.g., results.json).

# System Architecture and Workflow

The pipeline is designed for robustness, cost-efficiency, and strict data formatting, utilizing four core components:

## 1. Prompt Engineering & Schema Enforcement
To guarantee parsable output, the system uses a highly structured prompt:
* **Strict Directives:** Forces the model to output *only* JSON wrapped in markdown backticks.
* **Few-Shot Schema:** Provides a complete `REQUIRED JSON SCHEMA` pre-filled with criteria and default `0` scores, ensuring the LLM replaces them with correctly formatted integer scores instead of unpredictable strings.

## 2. Prompt Caching
Batch evaluating submissions sends thousands of redundant tokens. The pipeline optimizes this using Anthropic's ephemeral prefix caching:
* Static instructions and the `Rubric.pdf` are bundled into the first message block.
* This block is tagged with `"cache_control": {"type": "ephemeral"}`.
* The API caches this static block after the first call, reducing latency and costs for all subsequent submissions in the batch.

## 3. Output Sanitization & Cleaning
To handle LLM variability and malformed characters:
* **Regex Extraction:** A robust regular expression safely extracts the JSON payload, ignoring any conversational text outside the code block.
* **Data Injection:** The `filename` is dynamically injected into the parsed JSON dictionary to map the score back to the source file.

## 4. Atomic File Operations
To prevent data loss during long runs:
* Results are continuously written to disk rather than stored in memory.
* The system safely reads, appends to, and atomically overwrites `results.json` on each iteration, ensuring all prior evaluations are saved even if the script is interrupted.