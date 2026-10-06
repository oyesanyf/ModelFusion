#!/usr/bin/env python3
"""
Test Suite: Resume Parsing Engine Verification
Tests scripts/parse_resume.py against TXT, DOCX, and PDF fixtures.
Verifies candidate detail extraction and screening question grounding.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
PARSE_RESUME_SCRIPT = SCRIPTS_DIR / "parse_resume.py"

def run_parser(file_path: Path, jd: str = ""):
    cmd = [sys.executable, str(PARSE_RESUME_SCRIPT), str(file_path)]
    if jd:
        cmd.extend(["--jd", jd])
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), encoding="utf-8")
    assert result.returncode == 0, f"Parser failed with returncode {result.returncode}:\n{result.stderr}"
    
    data = json.loads(result.stdout)
    return data

def test_txt_resume():
    txt_file = FIXTURES_DIR / "sample_resume.txt"
    assert txt_file.exists(), f"Missing fixture: {txt_file}"
    
    jd = "Seeking a Senior Rust and Python Engineer with 5+ years experience in distributed systems and cloud services."
    data = run_parser(txt_file, jd)
    
    assert data.get("status") == "ok", f"Expected ok status: {data}"
    assert "Jane Doe" in data.get("full_name", "") or "Alex" in data.get("full_name", ""), f"Unexpected name: {data.get('full_name')}"
    assert "@" in data.get("email", ""), f"Unexpected email: {data.get('email')}"
    assert data.get("phone"), "Phone number not extracted"
    assert "linkedin.com" in data.get("linkedin", ""), f"Unexpected linkedin: {data.get('linkedin')}"
    assert data.get("years_experience"), "Years of experience not extracted"
    assert len(data.get("skills", [])) >= 3, f"Expected at least 3 skills: {data.get('skills')}"
    
    # Check screening questions
    sqs = data.get("screening_questions", [])
    assert len(sqs) >= 3, f"Expected at least 3 screening questions: {sqs}"
    for sq in sqs:
        assert "question" in sq and "answer" in sq
        assert sq.get("answer"), f"Empty answer for: {sq['question']}"
    print("PASS: test_txt_resume")

def test_docx_resume():
    docx_file = FIXTURES_DIR / "sample_resume.docx"
    assert docx_file.exists(), f"Missing fixture: {docx_file}"
    
    data = run_parser(docx_file)
    assert data.get("status") == "ok", f"Expected ok status: {data}"
    assert data.get("full_name") or data.get("email")
    print("PASS: test_docx_resume")

def test_pdf_resume():
    pdf_file = FIXTURES_DIR / "sample_resume.pdf"
    assert pdf_file.exists(), f"Missing fixture: {pdf_file}"
    
    data = run_parser(pdf_file)
    assert data.get("status") == "ok", f"Expected ok status: {data}"
    assert data.get("full_name") or data.get("email")
    print("PASS: test_pdf_resume")

def main():
    print("=" * 60)
    print("Running Resume Parser Test Suite...")
    print("=" * 60)
    
    test_txt_resume()
    test_docx_resume()
    test_pdf_resume()
    
    print("=" * 60)
    print("ALL RESUME PARSER TESTS PASSED (100% GREEN)")
    print("=" * 60)

if __name__ == "__main__":
    main()
