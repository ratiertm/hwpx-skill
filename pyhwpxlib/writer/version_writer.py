"""Write version.xml - Port of VersionWriter.java."""
from __future__ import annotations

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.objects.root.version import VersionXMLFile
from pyhwpxlib.writer.xml_builder import XMLStringBuilder

# Default XML version written by the Java library
_XML_VERSION = "1.4"


def write_version(xsb: XMLStringBuilder, version_file: VersionXMLFile) -> None:
    """Serialize a VersionXMLFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.hv_HCFVersion)
    xsb.namespace(Namespaces.hv)

    if version_file.target_application is not None:
        xsb.attribute(AN.tagetApplication, version_file.target_application)

    v = version_file.version
    xsb.attribute(AN.major, v.major)
    xsb.attribute(AN.minor, v.minor)
    xsb.attribute(AN.micro, v.micro)
    xsb.attribute(AN.buildNumber, v.build_number)
    xsb.attribute(AN.os, getattr(version_file, "os", getattr(v, "os", None)))
    xml_ver = getattr(v, "xml_version", None) or _XML_VERSION
    xsb.attribute(AN.xmlVersion, xml_ver)
    xsb.attribute(AN.application, version_file.application)
    xsb.attribute(AN.appVersion, version_file.app_version)
    xsb.close_element()
