"""Port of HWPXFile.java - the ROOT container that holds the entire HWPX document."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional

from pyhwpxlib.base import HWPXObject, ObjectList
from pyhwpxlib.object_type import ObjectType
from pyhwpxlib.objects.chart import ChartXMLFile
from pyhwpxlib.objects.content_hpf.content_hpf import ContentHPFFile
from pyhwpxlib.objects.etc import UnparsedXMLFile
from pyhwpxlib.objects.masterpage.masterpage import MasterPageXMLFile
from pyhwpxlib.objects.metainf.container import ContainerXMLFile
from pyhwpxlib.objects.metainf.manifest import ManifestXMLFile
from pyhwpxlib.objects.root.settings import SettingsXMLFile
from pyhwpxlib.objects.root.version import VersionXMLFile

if TYPE_CHECKING:
    pass
    # Future imports when these modules exist:
    # from pyhwpxlib.objects.header.header_xml_file import HeaderXMLFile
    # from pyhwpxlib.objects.section.section_xml_file import SectionXMLFile
    # from pyhwpxlib.objects.dochistory.history_xml_file import HistoryXMLFile


@dataclass
class HWPXFile(HWPXObject):
    """Root container representing an entire HWPX document.

    Holds references to all sub-files: version.xml, manifest.xml,
    container.xml, content.hpf, header.xml, master pages, sections,
    settings.xml, history, charts, and unparsed/attached files.
    """

    version_xml_file: VersionXMLFile = field(default_factory=VersionXMLFile)
    manifest_xml_file: ManifestXMLFile = field(default_factory=ManifestXMLFile)
    container_xml_file: ContainerXMLFile = field(default_factory=ContainerXMLFile)
    content_hpf_file: ContentHPFFile = field(default_factory=ContentHPFFile)

    # HeaderXMLFile - use Any until header module is available
    header_xml_file: Any = field(default=None)

    # ObjectList[MasterPageXMLFile]
    master_page_xml_file_list: ObjectList[MasterPageXMLFile] = field(
        default_factory=lambda: ObjectList(
            _item_class=MasterPageXMLFile,
        )
    )

    # ObjectList[SectionXMLFile] - use Any items until section module is available
    section_xml_file_list: ObjectList[Any] = field(
        default_factory=lambda: ObjectList()
    )

    settings_xml_file: SettingsXMLFile = field(default_factory=SettingsXMLFile)

    # ObjectList[HistoryXMLFile] - use Any items until dochistory module is available
    history_xml_file_list: ObjectList[Any] = field(
        default_factory=lambda: ObjectList()
    )

    # ObjectList[ChartXMLFile]
    chart_xml_file_list: ObjectList[ChartXMLFile] = field(
        default_factory=lambda: ObjectList(
            _item_class=ChartXMLFile,
        )
    )

    unparsed_xml_file_list: List[UnparsedXMLFile] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.HWPXFile

    # --- Unparsed XML helpers ---

    def add_unparsed_xml_file(self, href: str, xml: str) -> None:
        f = UnparsedXMLFile(href=href, xml=xml)
        self.unparsed_xml_file_list.append(f)

    def unparsed_xml_files(self) -> List[UnparsedXMLFile]:
        return list(self.unparsed_xml_file_list)

    def remove_unparsed_xml_file(self, unparsed: UnparsedXMLFile) -> None:
        self.unparsed_xml_file_list.remove(unparsed)

    def remove_all_unparsed_xml_files(self) -> None:
        self.unparsed_xml_file_list.clear()

    # --- Clone / Copy ---

    def clone(self) -> HWPXFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: HWPXFile) -> None:
        self.version_xml_file.copy_from(from_obj.version_xml_file)
        self.manifest_xml_file.copy_from(from_obj.manifest_xml_file)
        self.container_xml_file.copy_from(from_obj.container_xml_file)
        self.content_hpf_file.copy_from(from_obj.content_hpf_file)

        if from_obj.header_xml_file is not None:
            if hasattr(from_obj.header_xml_file, "clone"):
                self.header_xml_file = from_obj.header_xml_file.clone()
            else:
                self.header_xml_file = copy.deepcopy(from_obj.header_xml_file)

        for mp in from_obj.master_page_xml_file_list.items():
            self.master_page_xml_file_list.add(mp.clone())

        for sec in from_obj.section_xml_file_list.items():
            if hasattr(sec, "clone"):
                self.section_xml_file_list.add(sec.clone())
            else:
                self.section_xml_file_list.add(copy.deepcopy(sec))

        self.settings_xml_file.copy_from(from_obj.settings_xml_file)

        for hist in from_obj.history_xml_file_list.items():
            if hasattr(hist, "clone"):
                self.history_xml_file_list.add(hist.clone())
            else:
                self.history_xml_file_list.add(copy.deepcopy(hist))

        for chart in from_obj.chart_xml_file_list.items():
            self.chart_xml_file_list.add(chart.clone())

        for unparsed in from_obj.unparsed_xml_file_list:
            self.unparsed_xml_file_list.append(unparsed.clone())
