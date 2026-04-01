"""Write META-INF/manifest.xml - Port of ManifestWriter + FileEntryWriter."""
from __future__ import annotations

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.objects.metainf.manifest import (
    EncryptionData,
    FileEntry,
    ManifestXMLFile,
)
from pyhwpxlib.writer.xml_builder import XMLStringBuilder


def write_manifest(xsb: XMLStringBuilder, manifest: ManifestXMLFile) -> None:
    """Serialize a ManifestXMLFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.odf_manifest)
    xsb.namespace(Namespaces.odf)

    for fe in manifest.file_entry_list:
        _write_file_entry(xsb, fe)

    xsb.close_element()


def _write_file_entry(xsb: XMLStringBuilder, fe: FileEntry) -> None:
    xsb.open_element(EN.odf_file_entry)
    xsb.attribute(AN.full_path, fe.full_path)
    xsb.attribute(AN.media_type, fe.media_type)
    xsb.attribute(AN.size, fe.size)

    if fe.encryption_data is not None:
        _write_encryption_data(xsb, fe.encryption_data)

    xsb.close_element()


def _write_encryption_data(xsb: XMLStringBuilder, ed: EncryptionData) -> None:
    xsb.open_element(EN.odf_encryption_data)
    xsb.attribute(AN.checksum_type, ed.checksum_type)
    xsb.attribute(AN.checksum, ed.checksum)

    if ed.algorithm is not None:
        xsb.open_element(EN.odf_algorithm)
        xsb.attribute(AN.algorithm_name, ed.algorithm.algorithm_name)
        xsb.attribute("initialisation-vector", ed.algorithm.initialisation_vector)
        xsb.close_element()

    if ed.key_derivation is not None:
        xsb.open_element(EN.odf_key_derivation)
        xsb.attribute("key-derivation-name", ed.key_derivation.key_derivation_name)
        xsb.attribute(AN.key_size, ed.key_derivation.key_size)
        xsb.attribute("iteration-count", ed.key_derivation.iteration_count)
        xsb.attribute(AN.salt, ed.key_derivation.salt)
        xsb.close_element()

    if ed.start_key_generation is not None:
        xsb.open_element(EN.odf_start_key_generation)
        xsb.attribute(
            "start-key-generation-name",
            ed.start_key_generation.start_key_generation_name,
        )
        xsb.attribute(AN.key_size, ed.start_key_generation.key_size)
        xsb.close_element()

    xsb.close_element()
