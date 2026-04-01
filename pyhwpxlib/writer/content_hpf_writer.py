"""Write Contents/content.hpf - Port of ContentWriter + MetaDataWriter +
ContentManifestWriter + SpineWriter."""
from __future__ import annotations

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.objects.content_hpf.content_hpf import (
    ContentHPFFile,
    ManifestItem,
    Meta,
    MetaData,
    SpineItemRef,
)
from pyhwpxlib.writer.xml_builder import XMLStringBuilder

# All namespaces written on content.hpf root element (matching Java order)
_CONTENT_NAMESPACES = [
    Namespaces.ha,
    Namespaces.hp,
    Namespaces.hp10,
    Namespaces.hs,
    Namespaces.hc,
    Namespaces.hh,
    Namespaces.hhs,
    Namespaces.hm,
    Namespaces.hpf,
    Namespaces.dc,
    Namespaces.opf,
    Namespaces.ooxmlchart,
    Namespaces.hwpunitchar,
    Namespaces.epub,
    Namespaces.config,
]


def write_content_hpf(xsb: XMLStringBuilder, content: ContentHPFFile) -> None:
    """Serialize a ContentHPFFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.opf_package)
    for ns in _CONTENT_NAMESPACES:
        xsb.namespace(ns)
    xsb.attribute(AN.version, content.version)
    xsb.attribute(AN.unique_identifier, content.unique_identifier)
    xsb.attribute(AN.id, content.id)

    if content.meta_data is not None:
        _write_metadata(xsb, content.meta_data)

    if content.manifest is not None:
        _write_manifest(xsb, content.manifest)

    if content.spine is not None:
        _write_spine(xsb, content.spine)

    xsb.close_element()


# ------------------------------------------------------------------
# MetaData
# ------------------------------------------------------------------

def _write_metadata(xsb: XMLStringBuilder, md: MetaData) -> None:
    xsb.open_element(EN.opf_metadata)

    if md.title is not None:
        xsb.open_element(EN.opf_title)
        xsb.text(md.title.text())
        xsb.close_element()

    if md.language is not None:
        xsb.open_element(EN.opf_language)
        xsb.text(md.language.text())
        xsb.close_element()

    for meta in md.meta_list:
        _write_meta(xsb, meta)

    xsb.close_element()


def _write_meta(xsb: XMLStringBuilder, meta: Meta) -> None:
    xsb.open_element(EN.opf_meta)
    xsb.attribute(AN.name, meta.name)
    xsb.attribute(AN.content, meta.content)
    xsb.text(meta.text)
    xsb.close_element()


# ------------------------------------------------------------------
# Manifest (content manifest items)
# ------------------------------------------------------------------

def _write_manifest(xsb: XMLStringBuilder, manifest) -> None:
    xsb.open_element(EN.opf_manifest)

    for item in manifest.items():
        _write_item(xsb, item)

    xsb.close_element()


def _write_item(xsb: XMLStringBuilder, item: ManifestItem) -> None:
    xsb.open_element(EN.opf_item)
    xsb.attribute(AN.id, item.id)
    xsb.attribute(AN.href, item.href)
    xsb.attribute(AN.media_type, item.media_type)
    xsb.attribute(AN.fallback, item.fallback)
    xsb.attribute(AN.fallback_style, item.fallback_style)
    xsb.attribute(AN.required_namespace, item.required_namespace)
    xsb.attribute(AN.required_modules, item.required_modules)
    xsb.attribute(AN.encryption, item.encryption)
    xsb.attribute(AN.file_size, item.file_size)
    xsb.attribute(AN.isEmbeded, item.is_embedded)
    xsb.attribute(AN.sub_path, item.sub_path)
    xsb.close_element()


# ------------------------------------------------------------------
# Spine
# ------------------------------------------------------------------

def _write_spine(xsb: XMLStringBuilder, spine) -> None:
    xsb.open_element(EN.opf_spine)

    for ref in spine.items():
        _write_itemref(xsb, ref)

    xsb.close_element()


def _write_itemref(xsb: XMLStringBuilder, ref: SpineItemRef) -> None:
    xsb.open_element(EN.opf_itemref)
    xsb.attribute(AN.idref, ref.idref)
    xsb.attribute(AN.linear, ref.linear)
    xsb.close_element()
