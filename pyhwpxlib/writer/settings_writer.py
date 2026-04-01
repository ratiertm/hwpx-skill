"""Write settings.xml - Port of SettingsWriter + ConfigItemSetWriter."""
from __future__ import annotations

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.objects.root.settings import (
    CaretPosition,
    ConfigItem,
    ConfigItemSet,
    SettingsXMLFile,
)
from pyhwpxlib.writer.xml_builder import XMLStringBuilder


def write_settings(xsb: XMLStringBuilder, settings: SettingsXMLFile) -> None:
    """Serialize a SettingsXMLFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.ha_HWPApplicationSetting)
    xsb.namespace(Namespaces.ha)
    xsb.namespace(Namespaces.config)

    if settings.caret_position is not None:
        _write_caret_position(xsb, settings.caret_position)

    if settings.config_item_set is not None:
        _write_config_item_set(xsb, settings.config_item_set)

    xsb.close_element()


def _write_caret_position(xsb: XMLStringBuilder, cp: CaretPosition) -> None:
    xsb.open_element(EN.ha_CaretPosition)
    xsb.attribute(AN.listIDRef, cp.list_id_ref)
    xsb.attribute(AN.paraIDRef, cp.para_id_ref)
    xsb.attribute(AN.pos, cp.pos)
    xsb.close_element()


def _write_config_item_set(xsb: XMLStringBuilder, cis: ConfigItemSet) -> None:
    """Write config:config-item-set. Also used by TrackChangeConfig."""
    xsb.open_element(EN.config_item_set2)
    xsb.attribute(AN.name, cis.name)

    for item in cis.config_item_list:
        _write_config_item(xsb, item)

    xsb.close_element()


def _write_config_item(xsb: XMLStringBuilder, ci: ConfigItem) -> None:
    xsb.open_element(EN.config_item2)
    xsb.attribute(AN.name, ci.name)
    xsb.attribute(AN.type, ci.type)
    xsb.text(ci.value)
    xsb.close_element()
