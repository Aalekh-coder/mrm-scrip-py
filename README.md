# Scraping Scripts Usage Guide

This project contains Python scripts designed to crawl websites, find contact information, and audit exposed documents for metadata leaks.

## Project Structure

*   **[main.py](file:///D:/tsn/mrm-scrip-py/main.py)**: Scrapes contact information (emails, phone numbers, addresses, and social profile links) by scanning the homepage, contact, and about pages.
*   **[docs_main.py](file:///D:/tsn/mrm-scrip-py/docs_main.py)**: Deep-crawls a site and probes common exposed paths to find documents (PDF, Word, Excel, etc.) and audit them for metadata or contact information leaks.
*   **[super_script.py](file:///D:/tsn/mrm-scrip-py/super_script.py)**: An orchestrated hybrid script that extracts contact information and groups exposed documents found on key pages.

---

## 1. Environment Setup

The project uses a Python virtual environment (`.venv`) to manage dependencies. Follow these steps to prepare your environment.

### Step A: Activate the Virtual Environment
Open your terminal (PowerShell or Command Prompt) and navigate to the project directory:

**PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

**Command Prompt (cmd):**
```cmd
.venv\Scripts\activate.bat
```

### Step B: Install Dependencies
Ensure the required external libraries are installed:
```bash
pip install requests beautifulsoup4 lxml
```

---

## 2. How to Run the Scripts

You can run any of the scripts interactively or directly by passing input through your terminal.

### Contact Detail Scraper (`main.py`)
Run the script and enter the domain when prompted:
```bash
python main.py
```
*Example input:* `matrixtissues.com`

Alternatively, execute programmatically from Python:
```python
import main
result = main.extract_contact_details("matrixtissues.com")
print(result)
```

### Document Audit Scraper (`docs_main.py`)
Run the script interactively:
```bash
python docs_main.py
```
*Example input:* `matrixtissues.com`

Or run programmatically to analyze a target:
```python
import docs_main
report = docs_main.scrape_documents("matrixtissues.com")
docs_main.print_report(report)
```

### Orchestrated Scraper (`super_script.py`)
Run the combined script interactively:
```bash
python super_script.py
```

Or run programmatically:
```python
import super_script
result = super_script.extract_contact_details("matrixtissues.com")
print(result)
```
