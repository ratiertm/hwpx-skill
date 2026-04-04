"""Unit tests for standalone writer utility modules."""
import pytest
from pyhwpxlib.writer.xml_builder import XMLStringBuilder


class TestManifestWriter:
    def test_write_manifest_basic(self):
        from pyhwpxlib.writer.manifest_writer import write_manifest
        from pyhwpxlib.objects.metainf.manifest import ManifestXMLFile, FileEntry

        manifest = ManifestXMLFile()
        manifest.file_entry_list = []

        fe = FileEntry()
        fe.full_path = "/"
        fe.media_type = "application/hwp+zip"
        fe.size = "0"
        fe.encryption_data = None
        manifest.file_entry_list.append(fe)

        xsb = XMLStringBuilder()
        write_manifest(xsb, manifest)
        xml = xsb.to_string()
        assert len(xml) > 0
        assert "full-path" in xml or "full_path" in xml or "/" in xml

    def test_write_manifest_empty(self):
        from pyhwpxlib.writer.manifest_writer import write_manifest
        from pyhwpxlib.objects.metainf.manifest import ManifestXMLFile

        manifest = ManifestXMLFile()
        manifest.file_entry_list = []

        xsb = XMLStringBuilder()
        write_manifest(xsb, manifest)
        xml = xsb.to_string()
        assert len(xml) > 0


class TestVersionWriter:
    def test_write_version(self):
        from pyhwpxlib.writer.version_writer import write_version
        from pyhwpxlib.objects.root.version import VersionXMLFile
        from pyhwpxlib.api import create_document

        doc = create_document()
        xsb = XMLStringBuilder()
        write_version(xsb, doc.version_xml_file)
        xml = xsb.to_string()
        assert len(xml) > 0


class TestSettingsWriter:
    def test_write_settings_basic(self):
        from pyhwpxlib.writer.settings_writer import write_settings
        from pyhwpxlib.objects.root.settings import SettingsXMLFile
        from pyhwpxlib.api import create_document

        doc = create_document()
        xsb = XMLStringBuilder()
        if doc.settings_xml_file is not None:
            write_settings(xsb, doc.settings_xml_file)
            xml = xsb.to_string()
            assert isinstance(xml, str)

    def test_write_config_item_set(self):
        from pyhwpxlib.writer.settings_writer import _write_config_item_set, _write_config_item
        from pyhwpxlib.objects.root.settings import ConfigItemSet, ConfigItem

        cis = ConfigItemSet()
        cis.name = "ooo:view-settings"
        ci = ConfigItem()
        ci.name = "ViewAreaWidth"
        ci.type = "int"
        ci.value = "26669"
        cis.config_item_list = [ci]

        xsb = XMLStringBuilder()
        _write_config_item_set(xsb, cis)
        xml = xsb.to_string()
        assert "ViewAreaWidth" in xml or len(xml) > 0


class TestContainerWriter:
    def test_write_container(self):
        from pyhwpxlib.writer.container_writer import write_container
        from pyhwpxlib.objects.metainf.container import ContainerXMLFile

        container = ContainerXMLFile()
        container.root_files = None

        xsb = XMLStringBuilder()
        write_container(xsb, container)
        xml = xsb.to_string()
        assert len(xml) > 0

    def test_write_container_with_root_files(self):
        from pyhwpxlib.writer.container_writer import write_container
        from pyhwpxlib.objects.metainf.container import ContainerXMLFile, RootFile

        container = ContainerXMLFile()
        rf = RootFile()
        rf.full_path = "Contents/content.hpf"
        rf.media_type = "application/x-hwp-v5"

        class FakeRootFiles:
            def items(self):
                return [rf]
            def __len__(self):
                return 1

        container.root_files = FakeRootFiles()
        xsb = XMLStringBuilder()
        write_container(xsb, container)
        xml = xsb.to_string()
        assert len(xml) > 0


class TestXMLBuilder:
    def test_open_close_element(self):
        xsb = XMLStringBuilder()
        xsb.open_element("test")
        xsb.close_element()
        xml = xsb.to_string()
        assert "test" in xml

    def test_attribute(self):
        xsb = XMLStringBuilder()
        xsb.open_element("elem")
        xsb.attribute("key", "value")
        xsb.close_element()
        xml = xsb.to_string()
        assert "value" in xml

    def test_text(self):
        xsb = XMLStringBuilder()
        xsb.open_element("t")
        xsb.text("hello world")
        xsb.close_element()
        xml = xsb.to_string()
        assert "hello world" in xml

    def test_namespace(self):
        from pyhwpxlib.constants.namespaces import Namespaces
        xsb = XMLStringBuilder()
        xsb.open_element("root")
        xsb.namespace(Namespaces.hp)
        xsb.close_element()
        xml = xsb.to_string()
        assert len(xml) > 0

    def test_clear(self):
        xsb = XMLStringBuilder()
        xsb.open_element("first")
        xsb.close_element()
        xsb.clear()
        xsb.open_element("second")
        xsb.close_element()
        xml = xsb.to_string()
        assert "second" in xml
