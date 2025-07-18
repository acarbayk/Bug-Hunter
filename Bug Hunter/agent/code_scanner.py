import os
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_EXTENSIONS = ['.py', '.js', '.java', '.ts', '.go', '.rb', '.php']
CHUNK_SIZE = 1000  # characters

class CodeScanner:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.use_mock = not self.api_key
        if not self.use_mock:
            from langchain.chat_models import ChatOpenAI
            from langchain.prompts import ChatPromptTemplate
            self.llm = ChatOpenAI(model_name="gpt-4", temperature=0)
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", "You are a cybersecurity expert. Analyze the following code for security vulnerabilities. List each vulnerability, its severity, and a suggested fix."),
                ("human", "{code_chunk}")
            ])
        self.findings = []

    def scan(self, path):
        print(f"Scanning codebase at {path} for vulnerabilities...")
        if self.use_mock:
            print("[Mock Mode] No OpenAI API key found. Using mock vulnerability analysis.")
        code_files = self._collect_code_files(path)
        for file_path in code_files:
            print(f"\n--- Scanning {file_path} ---")
            for chunk in self._chunk_file(file_path):
                findings = self._analyze_chunk(chunk)
                self.findings.append({
                    'file': file_path,
                    'chunk': chunk[:100] + ("..." if len(chunk) > 100 else ""),
                    'result': findings
                })
        self._report()

    def _collect_code_files(self, path):
        code_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    code_files.append(os.path.join(root, file))
        return code_files

    def _chunk_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Split content into chunks
        return [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]

    def _analyze_chunk(self, code_chunk):
        if self.use_mock:
            # Simple mock logic for demonstration
            findings = []
            if 'password' in code_chunk:
                findings.append("Hardcoded password detected. Severity: High. Fix: Use environment variables or a secure vault.")
            if 'input(' in code_chunk or 'raw_input(' in code_chunk:
                findings.append("Unsanitized user input detected. Severity: Medium. Fix: Sanitize and validate all user inputs.")
            if not findings:
                return "No obvious vulnerabilities detected in this chunk."
            return '\n'.join(findings)
        else:
            prompt = self.prompt_template.format_messages(code_chunk=code_chunk)
            response = self.llm(prompt)
            return response.content

    def _report(self):
        print("\n--- Vulnerability Report ---")
        if not self.findings:
            print("No vulnerabilities detected.")
        for finding in self.findings:
            print(f"[File: {finding['file']}]\nChunk: {finding['chunk']}\nFindings: {finding['result']}\n{'-'*40}") 