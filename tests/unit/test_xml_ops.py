"""Unit tests for pyhwpxlib.xml_ops — XML text node operations."""
import pytest
from pyhwpxlib.xml_ops import replace_text_nodes, safe_xml_escape, iter_section_entries


class TestSafeXmlEscape:
    def test_ampersand(self):
        assert safe_xml_escape("A&B") == "A&amp;B"

    def test_less_than(self):
        assert safe_xml_escape("x < y") == "x &lt; y"

    def test_greater_than(self):
        assert safe_xml_escape("x > y") == "x &gt; y"

    def test_double_quote(self):
        assert safe_xml_escape('say "hi"') == "say &quot;hi&quot;"

    def test_single_quote(self):
        assert safe_xml_escape("it's") == "it&apos;s"

    def test_all_special_chars(self):
        result = safe_xml_escape('A&B <"C"> \'D\'')
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&quot;" in result
        assert "&apos;" in result

    def test_plain_text_unchanged(self):
        assert safe_xml_escape("hello world") == "hello world"

    def test_korean_unchanged(self):
        assert safe_xml_escape("홍길동") == "홍길동"


class TestReplaceTextNodes:
    """replace_text_nodes replaces text only inside <hp:t> nodes."""

    def test_braced_key_replaced(self):
        xml = '<hp:t>{{name}}</hp:t>'
        result = replace_text_nodes(xml, {"name": "홍길동"})
        assert result == '<hp:t>홍길동</hp:t>'

    def test_braces_fully_removed(self):
        xml = '<hp:t>Hello {{name}}</hp:t>'
        result = replace_text_nodes(xml, {"name": "World"})
        assert "{{" not in result
        assert "}}" not in result
        assert "World" in result

    def test_literal_key_replaced_with_braces_off(self):
        """Literal key matching requires support_braced_keys=False."""
        xml = '<hp:t>PLACEHOLDER</hp:t>'
        result = replace_text_nodes(xml, {"PLACEHOLDER": "VALUE"}, support_braced_keys=False)
        assert result == '<hp:t>VALUE</hp:t>'

    def test_literal_key_not_matched_in_braced_mode(self):
        """In braced mode (default), bare keys don't match — only {{key}} does."""
        xml = '<hp:t>이름: 홍길동</hp:t>'
        result = replace_text_nodes(xml, {"이름": "X"})
        assert result == '<hp:t>이름: 홍길동</hp:t>'  # unchanged

    def test_ampersand_escaped_in_value(self):
        xml = '<hp:t>{{co}}</hp:t>'
        result = replace_text_nodes(xml, {"co": "A&B"})
        assert result == '<hp:t>A&amp;B</hp:t>'

    def test_less_than_escaped_in_value(self):
        xml = '<hp:t>{{x}}</hp:t>'
        result = replace_text_nodes(xml, {"x": "a < b"})
        assert "&lt;" in result
        assert "{{" not in result

    def test_greater_than_escaped_in_value(self):
        xml = '<hp:t>{{x}}</hp:t>'
        result = replace_text_nodes(xml, {"x": "a > b"})
        assert "&gt;" in result

    def test_all_special_chars_in_value(self):
        xml = '<hp:t>{{v}}</hp:t>'
        result = replace_text_nodes(xml, {"v": 'A&B <"C">'})
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&quot;" in result

    def test_attribute_not_touched(self):
        """XML attributes must never be modified by replacement."""
        xml = '<hp:t textpos="0" vertsize="100">x</hp:t>'
        result = replace_text_nodes(xml, {"x": "REPLACED"})
        # The regex only matches <hp:t>content</hp:t> (no attributes in tag)
        # So this should NOT match and text stays unchanged
        assert "textpos" not in result or 'textpos="0"' in result

    def test_multiple_t_nodes(self):
        xml = '<hp:t>{{a}}</hp:t><hp:t>{{b}}</hp:t>'
        result = replace_text_nodes(xml, {"a": "X", "b": "Y"})
        assert result == '<hp:t>X</hp:t><hp:t>Y</hp:t>'

    def test_multiple_replacements_in_one_node(self):
        xml = '<hp:t>{{first}} {{last}}</hp:t>'
        result = replace_text_nodes(xml, {"first": "Kim", "last": "Jr"})
        assert result == '<hp:t>Kim Jr</hp:t>'

    def test_placeholder_repeated_twice(self):
        xml = '<hp:t>{{x}} and {{x}}</hp:t>'
        result = replace_text_nodes(xml, {"x": "A"})
        assert result == '<hp:t>A and A</hp:t>'

    def test_no_braces_mode(self):
        xml = '<hp:t>OLD TEXT</hp:t>'
        result = replace_text_nodes(xml, {"OLD TEXT": "NEW TEXT"}, support_braced_keys=False)
        assert result == '<hp:t>NEW TEXT</hp:t>'

    def test_no_braces_mode_does_not_match_braced(self):
        xml = '<hp:t>{{key}}</hp:t>'
        result = replace_text_nodes(xml, {"key": "val"}, support_braced_keys=False)
        # In no-braces mode, only literal "key" is matched, not "{{key}}"
        # "key" appears inside "{{key}}" so it WILL match
        assert "val" in result

    def test_empty_replacements(self):
        xml = '<hp:t>hello</hp:t>'
        result = replace_text_nodes(xml, {})
        assert result == '<hp:t>hello</hp:t>'

    def test_non_matching_placeholder(self):
        xml = '<hp:t>hello</hp:t>'
        result = replace_text_nodes(xml, {"MISSING": "value"})
        assert result == '<hp:t>hello</hp:t>'

    def test_empty_t_node(self):
        xml = '<hp:t></hp:t>'
        result = replace_text_nodes(xml, {"x": "y"})
        assert result == '<hp:t></hp:t>'

    def test_korean_placeholder_and_value(self):
        xml = '<hp:t>이름: {{이름}}</hp:t>'
        result = replace_text_nodes(xml, {"이름": "홍길동"})
        assert result == '<hp:t>이름: 홍길동</hp:t>'
        assert "{{" not in result


class TestIterSectionEntries:
    def test_finds_sections(self, tmp_path):
        import zipfile
        hwpx = tmp_path / "test.hwpx"
        with zipfile.ZipFile(hwpx, 'w') as z:
            z.writestr("mimetype", "application/hwp+zip")
            z.writestr("Contents/section0.xml", "<sec/>")
            z.writestr("Contents/section1.xml", "<sec/>")
            z.writestr("Contents/header.xml", "<head/>")
        result = iter_section_entries(str(hwpx))
        assert result == ["Contents/section0.xml", "Contents/section1.xml"]
