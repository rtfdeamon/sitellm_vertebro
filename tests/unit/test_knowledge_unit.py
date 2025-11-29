import io
import pytest
from fastapi import UploadFile, HTTPException
from openpyxl import Workbook
from backend.knowledge.api import _read_qa_upload

class TestKnowledgeUnit:
    """Unit tests for knowledge service components."""

    async def test_read_qa_upload_csv_semicolon(self):
        """Test parsing CSV with semicolon delimiter."""
        content = "Question;Answer;Priority\nWhat is AI?;Artificial Intelligence;1"
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(content.encode("utf-8")),
            headers={"content-type": "text/csv"}
        )
        pairs = await _read_qa_upload(file)
        assert len(pairs) == 1
        assert pairs[0]["question"] == "What is AI?"
        assert pairs[0]["answer"] == "Artificial Intelligence"
        assert pairs[0]["priority"] == 1

    async def test_read_qa_upload_csv_comma(self):
        """Test parsing CSV with comma delimiter."""
        content = "Question,Answer,Priority\nWhat is AI?,Artificial Intelligence,1"
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(content.encode("utf-8")),
            headers={"content-type": "text/csv"}
        )
        pairs = await _read_qa_upload(file)
        assert len(pairs) == 1
        assert pairs[0]["question"] == "What is AI?"
        assert pairs[0]["answer"] == "Artificial Intelligence"

    async def test_read_qa_upload_excel(self):
        """Test parsing Excel file."""
        wb = Workbook()
        ws = wb.active
        ws.append(["Question", "Answer", "Priority"])
        ws.append(["What is ML?", "Machine Learning", 2])
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        file = UploadFile(
            filename="test.xlsx",
            file=buffer,
            headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        )
        pairs = await _read_qa_upload(file)
        assert len(pairs) == 1
        assert pairs[0]["question"] == "What is ML?"
        assert pairs[0]["answer"] == "Machine Learning"
        assert pairs[0]["priority"] == 2

    async def test_read_qa_upload_text(self):
        """Test parsing plain text file with Q:/A: format."""
        content = "Q: What is Python?\nA: A programming language.\n\nQ: What is Pytest?\nA: A testing framework."
        file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(content.encode("utf-8")),
            headers={"content-type": "text/plain"}
        )
        pairs = await _read_qa_upload(file)
        assert len(pairs) == 2
        assert pairs[0]["question"] == "What is Python?"
        assert pairs[0]["answer"] == "A programming language."
        assert pairs[1]["question"] == "What is Pytest?"
        assert pairs[1]["answer"] == "A testing framework."

    async def test_read_qa_upload_empty(self):
        """Test handling of empty file."""
        file = UploadFile(
            filename="empty.txt",
            file=io.BytesIO(b""),
            headers={"content-type": "text/plain"}
        )
        with pytest.raises(HTTPException) as exc:
            await _read_qa_upload(file)
        assert exc.value.status_code == 400
        assert "File is empty" in exc.value.detail

    async def test_read_qa_upload_truncation(self):
        """Test truncation of long questions and answers."""
        long_q = "Q" * 2000
        long_a = "A" * 20000
        content = f"Q: {long_q}\nA: {long_a}"
        file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(content.encode("utf-8")),
            headers={"content-type": "text/plain"}
        )
        pairs = await _read_qa_upload(file)
        assert len(pairs) == 1
        assert len(pairs[0]["question"]) == 1000
        assert len(pairs[0]["answer"]) == 10000

    async def test_read_qa_upload_html_escaping(self):
        """Test HTML escaping of content."""
        content = "Q: <script>alert(1)</script>\nA: <b>Bold</b>"
        file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(content.encode("utf-8")),
            headers={"content-type": "text/plain"}
        )
        pairs = await _read_qa_upload(file)
        assert len(pairs) == 1
        assert "&lt;script&gt;" in pairs[0]["question"]
        assert "<script>" not in pairs[0]["question"]
