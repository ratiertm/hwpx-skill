"""Integration tests for merge_documents — block order preservation."""
import os
import pytest
from pyhwpxlib.api import (
    create_document, add_paragraph, add_table, save,
    merge_documents, extract_text,
)


class TestMergeDocumentsOrder:
    """merge_documents must preserve paragraph/table interleaving."""

    def test_para_table_para_order_preserved(self, tmp_path):
        """Document with para→table→para must keep that order after merge."""
        src = str(tmp_path / "src.hwpx")
        out = str(tmp_path / "merged.hwpx")

        doc = create_document()
        add_paragraph(doc, "BEFORE")
        add_table(doc, 2, 2, data=[["H1", "H2"], ["r1", "r2"]])
        add_paragraph(doc, "AFTER")
        save(doc, src)

        merge_documents([src], out)

        text = extract_text(out)
        before_pos = text.find("BEFORE")
        after_pos = text.find("AFTER")
        assert before_pos >= 0, "BEFORE not found"
        assert after_pos >= 0, "AFTER not found"
        assert before_pos < after_pos, f"Order wrong: BEFORE@{before_pos} AFTER@{after_pos}"

    def test_two_documents_merged(self, tmp_path):
        """Two documents should both appear in merged output."""
        src1 = str(tmp_path / "a.hwpx")
        src2 = str(tmp_path / "b.hwpx")
        out = str(tmp_path / "merged.hwpx")

        doc1 = create_document()
        add_paragraph(doc1, "DOC_A_CONTENT")
        save(doc1, src1)

        doc2 = create_document()
        add_paragraph(doc2, "DOC_B_CONTENT")
        save(doc2, src2)

        merge_documents([src1, src2], out)

        text = extract_text(out)
        assert "DOC_A_CONTENT" in text
        assert "DOC_B_CONTENT" in text

    def test_table_only_document(self, tmp_path):
        """Document with only a table should merge without error."""
        src = str(tmp_path / "tbl.hwpx")
        out = str(tmp_path / "merged.hwpx")

        doc = create_document()
        add_table(doc, 2, 2, data=[["A", "B"], ["1", "2"]])
        save(doc, src)

        merge_documents([src], out)
        assert os.path.exists(out)
        text = extract_text(out)
        assert "A" in text
