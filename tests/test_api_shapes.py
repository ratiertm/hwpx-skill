"""Tests for advanced shape/drawing API functions and round-trip open/save."""
import os
import pytest
from pathlib import Path

from pyhwpxlib.api import (
    create_document,
    add_arc,
    add_polygon,
    add_curve,
    add_connect_line,
    add_equation,
    add_container,
    save,
    extract_text,
    open_document,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestAddArc:
    def test_basic_arc(self, doc, tmp_hwpx):
        add_arc(doc, center_x=5000, center_y=5000,
                ax1_x=5000, ax1_y=0,
                ax2_x=10000, ax2_y=5000)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000

    def test_pie_arc(self, doc, tmp_hwpx):
        add_arc(doc, center_x=5000, center_y=5000,
                ax1_x=5000, ax1_y=0,
                ax2_x=10000, ax2_y=5000,
                arc_type="PIE")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_chord_arc(self, doc, tmp_hwpx):
        add_arc(doc, center_x=5000, center_y=5000,
                ax1_x=5000, ax1_y=0,
                ax2_x=10000, ax2_y=5000,
                arc_type="CHORD")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_returns_para(self, doc):
        result = add_arc(doc, center_x=5000, center_y=5000,
                         ax1_x=5000, ax1_y=0,
                         ax2_x=10000, ax2_y=5000)
        assert result is not None


class TestAddPolygon:
    def test_triangle(self, doc, tmp_hwpx):
        points = [(5000, 0), (10000, 10000), (0, 10000)]
        add_polygon(doc, points=points)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_square_polygon(self, doc, tmp_hwpx):
        points = [(0, 0), (5000, 0), (5000, 5000), (0, 5000)]
        add_polygon(doc, points=points)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_with_fill_color(self, doc, tmp_hwpx):
        points = [(0, 0), (5000, 0), (5000, 5000)]
        add_polygon(doc, points=points, fill_color="#FF0000")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_returns_para(self, doc):
        result = add_polygon(doc, points=[(0, 0), (5000, 0), (2500, 5000)])
        assert result is not None


class TestAddCurve:
    def test_basic_curve(self, doc, tmp_hwpx):
        segments = [
            {"type": "LINE", "x1": 0, "y1": 0, "x2": 5000, "y2": 0},
            {"type": "CURVE", "x1": 5000, "y1": 0, "x2": 10000, "y2": 5000},
        ]
        add_curve(doc, segments=segments)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_line_segments(self, doc, tmp_hwpx):
        segments = [
            {"type": "LINE", "x1": 0, "y1": 0, "x2": 5000, "y2": 5000},
        ]
        add_curve(doc, segments=segments)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


class TestAddConnectLine:
    def test_basic_connect_line(self, doc, tmp_hwpx):
        add_connect_line(doc, start_x=0, start_y=0, end_x=5000, end_y=5000)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_with_custom_color(self, doc, tmp_hwpx):
        add_connect_line(doc, start_x=1000, start_y=1000, end_x=8000, end_y=8000,
                         line_color="#FF0000")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


class TestAddEquation:
    def test_basic_equation(self, doc, tmp_hwpx):
        add_equation(doc, "x^2 + y^2 = r^2")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000

    def test_complex_equation(self, doc, tmp_hwpx):
        add_equation(doc, r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_custom_size(self, doc, tmp_hwpx):
        add_equation(doc, "E = mc^2", width=5000, height=4000)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


class TestAddContainer:
    def test_basic_container(self, doc, tmp_hwpx):
        add_container(doc, children_xml=[])
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


class TestAddImage:
    def test_add_png_image(self, doc, tmp_hwpx, tmp_path):
        # Create a minimal valid PNG
        import struct, zlib
        def make_png(w=10, h=10):
            def chunk(name, data):
                c = zlib.crc32(name + data) & 0xffffffff
                return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)
            IHDR = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
            raw = b''
            for _ in range(h):
                raw += b'\x00' + b'\xff\x00\x00' * w
            IDAT = zlib.compress(raw)
            return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', IHDR) + chunk(b'IDAT', IDAT) + chunk(b'IEND', b'')

        img_path = str(tmp_path / "test.png")
        with open(img_path, "wb") as f:
            f.write(make_png())

        from pyhwpxlib.api import add_image
        add_image(doc, img_path)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000

    def test_image_not_found_raises(self, doc):
        from pyhwpxlib.api import add_image
        with pytest.raises(FileNotFoundError):
            add_image(doc, "/nonexistent/path/image.png")


class TestOpenDocumentRoundTrip:
    """open_document exercises the full reader pipeline."""

    @pytest.fixture
    def sample_hwpx(self, tmp_path):
        from pyhwpxlib.api import add_paragraph, add_heading, add_table
        hwpx_path = str(tmp_path / "sample.hwpx")
        doc = create_document()
        add_heading(doc, "Test Document", level=1)
        add_paragraph(doc, "First paragraph")
        add_paragraph(doc, "Second paragraph with some content")
        add_table(doc, rows=2, cols=2, data=[["A", "B"], ["C", "D"]])
        save(doc, hwpx_path)
        return hwpx_path

    def test_open_document_returns_object(self, sample_hwpx):
        doc = open_document(sample_hwpx)
        assert doc is not None

    def test_open_document_has_sections(self, sample_hwpx):
        doc = open_document(sample_hwpx)
        assert hasattr(doc, "sections")
        assert len(doc.sections) > 0

    def test_open_document_has_paragraphs(self, sample_hwpx):
        doc = open_document(sample_hwpx)
        assert len(doc.sections) > 0
        section = doc.sections[0]
        assert len(section.paragraphs) > 0

    def test_open_document_text_content(self, sample_hwpx):
        doc = open_document(sample_hwpx)
        # Collect all text from paragraphs
        texts = []
        for section in doc.sections:
            for para in section.paragraphs:
                for run in para.runs:
                    if hasattr(run, 'text') and run.text:
                        texts.append(run.text)
        all_text = " ".join(texts)
        assert len(all_text) > 0

    def test_open_real_form(self):
        form_path = str(PROJECT_ROOT / "templates/sources/SimpleTable.hwpx")
        if not os.path.exists(form_path):
            pytest.skip("SimpleTable.hwpx not found")
        doc = open_document(form_path)
        assert doc is not None
        assert hasattr(doc, "sections")
