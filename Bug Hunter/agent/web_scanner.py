from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '"<img src=x onerror=alert(1)>',
]
SQLI_PAYLOADS = [
    "' OR 1=1--",
    '"; DROP TABLE users;--',
]
REDIRECT_PAYLOADS = [
    '//evil.com',
    'javascript:alert(1)'
]

class WebScanner:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.visited = set()
        self.findings = []

    def scan(self, url):
        print(f"Scanning web app at {url} for vulnerabilities...")
        self._crawl(url)
        self._report()
        self.driver.quit()

    def _crawl(self, base_url):
        to_visit = [base_url]
        while to_visit:
            url = to_visit.pop()
            if url in self.visited:
                continue
            self.visited.add(url)
            try:
                self.driver.get(url)
                time.sleep(1)  # Wait for page to load
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                # Find and queue new links
                for link in soup.find_all('a', href=True):
                    next_url = urljoin(url, link['href'])
                    if self._is_same_domain(base_url, next_url) and next_url not in self.visited:
                        to_visit.append(next_url)
                # Find and test forms
                forms = soup.find_all('form')
                for form in forms:
                    self._test_form(url, form)
            except WebDriverException as e:
                print(f"Error visiting {url}: {e}")

    def _is_same_domain(self, base, url):
        return urlparse(base).netloc == urlparse(url).netloc

    def _test_form(self, page_url, form):
        action = form.get('action')
        method = form.get('method', 'get').lower()
        form_url = urljoin(page_url, action) if action else page_url
        inputs = form.find_all(['input', 'textarea'])
        for payload in XSS_PAYLOADS + SQLI_PAYLOADS + REDIRECT_PAYLOADS:
            data = {}
            for inp in inputs:
                name = inp.get('name')
                if name:
                    data[name] = payload
            try:
                if method == 'post':
                    self.driver.get(form_url)
                    for name, value in data.items():
                        elem = self.driver.find_element(By.NAME, name)
                        elem.clear()
                        elem.send_keys(value)
                    self.driver.find_element(By.XPATH, '//form').submit()
                else:
                    params = '&'.join(f"{k}={v}" for k, v in data.items())
                    test_url = f"{form_url}?{params}" if params else form_url
                    self.driver.get(test_url)
                time.sleep(1)
                if payload in self.driver.page_source:
                    self.findings.append({
                        'url': form_url,
                        'payload': payload,
                        'type': self._classify_payload(payload),
                        'evidence': 'Payload reflected in response.'
                    })
            except Exception as e:
                continue

    def _classify_payload(self, payload):
        if payload in XSS_PAYLOADS:
            return 'XSS'
        if payload in SQLI_PAYLOADS:
            return 'SQL Injection'
        if payload in REDIRECT_PAYLOADS:
            return 'Open Redirect'
        return 'Unknown'

    def _report(self):
        print("\n--- Vulnerability Report ---")
        if not self.findings:
            print("No vulnerabilities detected.")
        for finding in self.findings:
            print(f"[!] {finding['type']} at {finding['url']} with payload: {finding['payload']} | Evidence: {finding['evidence']}") 