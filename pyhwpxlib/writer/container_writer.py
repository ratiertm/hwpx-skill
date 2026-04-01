"""Write META-INF/container.xml - Port of ContainerWriter + RootFilesWriter."""
from __future__ import annotations

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.objects.metainf.container import ContainerXMLFile, RootFile
from pyhwpxlib.writer.xml_builder import XMLStringBuilder


def write_container(xsb: XMLStringBuilder, container: ContainerXMLFile) -> None:
    """Serialize a ContainerXMLFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.ocf_container)
    xsb.namespace(Namespaces.ocf)
    xsb.namespace(Namespaces.hpf)

    if container.root_files is not None and len(container.root_files) > 0:
        _write_root_files(xsb, container.root_files)

    xsb.close_element()


def _write_root_files(xsb: XMLStringBuilder, root_files) -> None:
    xsb.open_element(EN.ocf_rootfiles)

    for rf in root_files.items():
        _write_root_file(xsb, rf)

    xsb.close_element()


def _write_root_file(xsb: XMLStringBuilder, rf: RootFile) -> None:
    xsb.open_element(EN.ocf_rootfile)
    xsb.attribute(AN.full_path, rf.full_path)
    xsb.attribute(AN.media_type, rf.media_type)
    xsb.close_element()
