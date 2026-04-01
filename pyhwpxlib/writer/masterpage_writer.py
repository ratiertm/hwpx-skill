"""Write masterpage*.xml - Port of MasterPageWriter.java."""
from __future__ import annotations

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.objects.masterpage.masterpage import MasterPageXMLFile
from pyhwpxlib.writer.section.section_writer import _write_sub_list
from pyhwpxlib.writer.xml_builder import XMLStringBuilder

# Same namespace set as sections
_MP_NAMESPACES = [
    Namespaces.ha, Namespaces.hp, Namespaces.hp10, Namespaces.hs,
    Namespaces.hc, Namespaces.hh, Namespaces.hhs, Namespaces.hm,
    Namespaces.hpf, Namespaces.dc, Namespaces.opf, Namespaces.ooxmlchart,
    Namespaces.hwpunitchar, Namespaces.epub, Namespaces.config,
]


def write_masterpage(xsb: XMLStringBuilder, mp: MasterPageXMLFile) -> None:
    """Serialize a MasterPageXMLFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.masterPage)
    for ns in _MP_NAMESPACES:
        xsb.namespace(ns)
    xsb.attribute(AN.id, mp.id)
    xsb.attribute(AN.type, mp.type)
    xsb.attribute(AN.pageNumber, mp.page_number)
    xsb.attribute(AN.pageDuplicate, mp.page_duplicate)
    xsb.attribute(AN.pageFront, mp.page_front)

    if mp.sub_list is not None:
        _write_sub_list(xsb, mp.sub_list)

    xsb.close_element()
