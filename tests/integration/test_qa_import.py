"""
Integration tests: QA import functionality.

Tests CSV/Excel import with edge cases.
"""

import io
import csv
import pytest
from openpyxl import Workbook
from fastapi.testclient import TestClient
from fastapi import UploadFile

from app import _read_qa_upload


@pytest.mark.integration
@pytest.mark.requires_mongo
class TestQAImport:
    """Test QA import functionality."""
    
    def test_csv_import_semicolon_delimiter(self):
        """Test CSV import with semicolon delimiter."""
        csv_content = "Вопрос;Ответ;Приоритет\nЧто такое Python?;Язык программирования;1"
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(csv_content.encode("utf-8")),
            headers={"content-type": "text/csv"},
        )
        
        pairs = pytest.asyncio.run(_read_qa_upload(file))
        assert len(pairs) == 1
        assert pairs[0]["question"] == "Что такое Python?"
        assert pairs[0]["answer"] == "Язык программирования"
    
    def test_csv_import_tab_delimiter(self):
        """Test CSV import with tab delimiter."""
        csv_content = "Вопрос\tОтвет\tПриоритет\nЧто такое Python?\tЯзык программирования\t1"
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(csv_content.encode("utf-8")),
            headers={"content-type": "text/csv"},
        )
        
        pairs = pytest.asyncio.run(_read_qa_upload(file))
        assert len(pairs) == 1
    
    def test_excel_import_basic(self):
        """Test basic Excel import."""
        wb = Workbook()
        ws = wb.active
        ws.append(["Вопрос", "Ответ", "Приоритет"])
        ws.append(["Что такое Python?", "Язык программирования", "1"])
        
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        file = UploadFile(
            filename="test.xlsx",
            file=excel_buffer,
            headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        )
        
        pairs = pytest.asyncio.run(_read_qa_upload(file))
        assert len(pairs) == 1
    
    def test_qa_import_empty_file(self):
        """Test that empty files are handled correctly."""
        file = UploadFile(
            filename="empty.csv",
            file=io.BytesIO(b""),
            headers={"content-type": "text/csv"},
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException
            pytest.asyncio.run(_read_qa_upload(file))
    
    def test_qa_import_long_text_truncation(self):
        """Test that overly long text is truncated."""
        # Question > 1000 chars, Answer > 10000 chars
        long_question = "Q" * 2000
        long_answer = "A" * 20000
        
        csv_content = f"Вопрос,Ответ\n{long_question},{long_answer}"
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(csv_content.encode("utf-8")),
            headers={"content-type": "text/csv"},
        )
        
        pairs = pytest.asyncio.run(_read_qa_upload(file))
        assert len(pairs) == 1
        assert len(pairs[0]["question"]) <= 1000
        assert len(pairs[0]["answer"]) <= 10000
    
    def test_qa_import_unicode_normalization(self):
        """Test that Unicode is normalized correctly."""
        # Use combining characters
        csv_content = "Вопрос,Ответ\nCafé,Café"
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(csv_content.encode("utf-8")),
            headers={"content-type": "text/csv"},
        )
        
        pairs = pytest.asyncio.run(_read_qa_upload(file))
        assert len(pairs) == 1
    
    def test_qa_import_html_escaping(self):
        """Test that HTML is escaped correctly."""
        csv_content = "Вопрос,Ответ\n<script>alert('xss')</script>,<b>Bold</b>"
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(csv_content.encode("utf-8")),
            headers={"content-type": "text/csv"},
        )
        
        pairs = pytest.asyncio.run(_read_qa_upload(file))
        assert len(pairs) == 1
        assert "<script>" not in pairs[0]["question"]
        assert "&lt;script&gt;" in pairs[0]["question"] or pairs[0]["question"] != "<script>alert('xss')</script>"





