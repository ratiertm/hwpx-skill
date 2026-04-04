"""Tests for pyhwpxlib object model classes — shapes, drawing objects, etc."""
import pytest


class TestShapeObjects:
    def test_import_shapes(self):
        from pyhwpxlib.objects.section.objects.shapes import (
            Rectangle, Ellipse, Arc, Polygon, Curve,
        )
        assert Rectangle is not None
        assert Ellipse is not None

    def test_rectangle_create(self):
        from pyhwpxlib.objects.section.objects.shapes import Rectangle
        from pyhwpxlib.object_type import ObjectType
        r = Rectangle()
        assert r._object_type() == ObjectType.hp_rect

    def test_rectangle_points(self):
        from pyhwpxlib.objects.section.objects.shapes import Rectangle
        r = Rectangle()
        p0 = r.create_pt0()
        p1 = r.create_pt1()
        p2 = r.create_pt2()
        p3 = r.create_pt3()
        assert p0 is not None
        assert r.pt0 is p0
        assert r.pt1 is p1
        assert r.pt2 is p2
        assert r.pt3 is p3

    def test_ellipse_create(self):
        from pyhwpxlib.objects.section.objects.shapes import Ellipse
        from pyhwpxlib.object_type import ObjectType
        e = Ellipse()
        assert e._object_type() == ObjectType.hp_ellipse

    def test_ellipse_points(self):
        from pyhwpxlib.objects.section.objects.shapes import Ellipse
        e = Ellipse()
        center = e.create_center()
        ax1 = e.create_ax1()
        ax2 = e.create_ax2()
        assert center is not None
        assert ax1 is not None
        assert ax2 is not None

    def test_arc_create(self):
        from pyhwpxlib.objects.section.objects.shapes import Arc
        from pyhwpxlib.object_type import ObjectType
        a = Arc()
        assert a._object_type() == ObjectType.hp_arc

    def test_arc_points(self):
        from pyhwpxlib.objects.section.objects.shapes import Arc
        a = Arc()
        center = a.create_center()
        ax1 = a.create_ax1()
        ax2 = a.create_ax2()
        assert center is not None
        assert ax1 is not None
        assert ax2 is not None

    def test_polygon_create(self):
        from pyhwpxlib.objects.section.objects.shapes import Polygon
        from pyhwpxlib.object_type import ObjectType
        p = Polygon()
        assert p._object_type() == ObjectType.hp_polygon

    def test_polygon_add_point(self):
        from pyhwpxlib.objects.section.objects.shapes import Polygon
        p = Polygon()
        pt = p.add_new_pt()
        assert pt is not None

    def test_curve_create(self):
        from pyhwpxlib.objects.section.objects.shapes import Curve
        from pyhwpxlib.object_type import ObjectType
        c = Curve()
        assert c._object_type() == ObjectType.hp_curve

    def test_curve_add_segment(self):
        from pyhwpxlib.objects.section.objects.shapes import Curve
        c = Curve()
        seg = c.add_new_seg()
        assert seg is not None


class TestDrawingObject:
    def test_import(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        assert DrawingObject is not None

    def test_drawing_object_create(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        assert d is not None

    def test_drawing_object_methods(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        offset = d.create_offset()
        sz = d.create_sz()
        assert offset is not None
        assert sz is not None

    def test_outer_margin(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        margin = d.create_out_margin()
        assert margin is not None

    def test_captions(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        caption = d.create_caption()
        assert caption is not None

    def test_rotation_info(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        m = d.create_rotation_info()
        assert m is not None

    def test_flip(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        flip = d.create_flip()
        assert flip is not None

    def test_shadow(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        shadow = d.create_shadow()
        assert shadow is not None

    def test_draw_text(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        dt = d.create_draw_text()
        assert dt is not None

    def test_pos(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        pos = d.create_pos()
        assert pos is not None

    def test_rendering_info(self):
        from pyhwpxlib.objects.section.objects.drawing_object import DrawingObject
        d = DrawingObject()
        ri = d.create_rendering_info()
        assert ri is not None


class TestConnectLine:
    def test_import_and_create(self):
        from pyhwpxlib.objects.section.objects.connect_line import ConnectLine
        from pyhwpxlib.object_type import ObjectType
        c = ConnectLine()
        assert c._object_type() == ObjectType.hp_connectLine

    def test_create_points(self):
        from pyhwpxlib.objects.section.objects.connect_line import ConnectLine
        c = ConnectLine()
        sp = c.create_start_pt()
        ep = c.create_end_pt()
        assert sp is not None
        assert ep is not None

    def test_create_control_points(self):
        from pyhwpxlib.objects.section.objects.connect_line import ConnectLine
        c = ConnectLine()
        cp = c.create_control_points()
        assert cp is not None


class TestEquation:
    def test_import_and_create(self):
        from pyhwpxlib.objects.section.objects.equation import Equation
        from pyhwpxlib.object_type import ObjectType
        e = Equation()
        assert e._object_type() == ObjectType.hp_equation

    def test_equation_fields(self):
        from pyhwpxlib.objects.section.objects.equation import Equation
        e = Equation()
        e.script = "x^2 + y^2 = r^2"
        assert e.script == "x^2 + y^2 = r^2"


class TestPicture:
    def test_import_and_create(self):
        from pyhwpxlib.objects.section.objects.picture import Picture
        from pyhwpxlib.object_type import ObjectType
        p = Picture()
        assert p._object_type() == ObjectType.hp_pic

    def test_picture_methods(self):
        from pyhwpxlib.objects.section.objects.picture import Picture
        p = Picture()
        # Check methods exist
        assert hasattr(p, 'create_caption') or hasattr(p, 'create_sz')

    def test_picture_sz(self):
        from pyhwpxlib.objects.section.objects.picture import Picture
        p = Picture()
        sz = p.create_sz()
        assert sz is not None


class TestTable:
    def test_import_and_create(self):
        from pyhwpxlib.objects.section.objects.table import Table
        from pyhwpxlib.object_type import ObjectType
        t = Table()
        assert t._object_type() == ObjectType.hp_tbl

    def test_table_add_row(self):
        from pyhwpxlib.objects.section.objects.table import Table
        t = Table()
        row = t.add_new_tr()
        assert row is not None

    def test_table_sz(self):
        from pyhwpxlib.objects.section.objects.table import Table
        t = Table()
        sz = t.create_sz()
        assert sz is not None

    def test_table_in_margin(self):
        from pyhwpxlib.objects.section.objects.table import Table
        t = Table()
        m = t.create_in_margin()
        assert m is not None


class TestFormObjects:
    def test_import(self):
        from pyhwpxlib.objects.section.objects.form_objects import (
            Button, RadioButton, CheckButton, ComboBox, Edit, ListBox, ScrollBar,
        )
        assert Button is not None
        assert RadioButton is not None

    def test_button_create(self):
        from pyhwpxlib.objects.section.objects.form_objects import Button
        from pyhwpxlib.object_type import ObjectType
        b = Button()
        assert b._object_type() == ObjectType.hp_btn

    def test_radio_button_create(self):
        from pyhwpxlib.objects.section.objects.form_objects import RadioButton
        from pyhwpxlib.object_type import ObjectType
        r = RadioButton()
        assert r._object_type() == ObjectType.hp_radioBtn

    def test_check_button_create(self):
        from pyhwpxlib.objects.section.objects.form_objects import CheckButton
        from pyhwpxlib.object_type import ObjectType
        c = CheckButton()
        assert c._object_type() == ObjectType.hp_checkBtn

    def test_edit_create(self):
        from pyhwpxlib.objects.section.objects.form_objects import Edit
        from pyhwpxlib.object_type import ObjectType
        e = Edit()
        assert e._object_type() == ObjectType.hp_edit

    def test_combobox_create(self):
        from pyhwpxlib.objects.section.objects.form_objects import ComboBox
        from pyhwpxlib.object_type import ObjectType
        c = ComboBox()
        assert c._object_type() == ObjectType.hp_comboBox

    def test_listbox_create(self):
        from pyhwpxlib.objects.section.objects.form_objects import ListBox
        from pyhwpxlib.object_type import ObjectType
        lb = ListBox()
        assert lb._object_type() == ObjectType.hp_listBox

    def test_scrollbar_create(self):
        from pyhwpxlib.objects.section.objects.form_objects import ScrollBar
        from pyhwpxlib.object_type import ObjectType
        s = ScrollBar()
        assert s._object_type() == ObjectType.hp_scrollBar


class TestTextArt:
    def test_import_and_create(self):
        from pyhwpxlib.objects.section.objects.text_art import TextArt
        from pyhwpxlib.object_type import ObjectType
        t = TextArt()
        assert t._object_type() == ObjectType.hp_textart

    def test_textart_fields(self):
        from pyhwpxlib.objects.section.objects.text_art import TextArt
        t = TextArt()
        # Just verify object creation and field access
        t.script = "test"
        assert t.script == "test"


class TestOLE:
    def test_import_and_create(self):
        from pyhwpxlib.objects.section.objects.ole import OLE
        from pyhwpxlib.object_type import ObjectType
        o = OLE()
        assert o._object_type() == ObjectType.hp_ole


class TestParameters:
    def test_import(self):
        from pyhwpxlib.objects.common.parameters import ParameterListCore, Param
        assert ParameterListCore is not None

    def test_create_parameter_list(self):
        from pyhwpxlib.objects.common.parameters import ParameterListCore
        pl = ParameterListCore()
        assert pl is not None

    def test_string_param(self):
        from pyhwpxlib.objects.common.parameters import StringParam
        p = StringParam()
        assert p is not None

    def test_integer_param(self):
        from pyhwpxlib.objects.common.parameters import IntegerParam
        p = IntegerParam()
        assert p is not None

    def test_bool_param(self):
        from pyhwpxlib.objects.common.parameters import BooleanParam
        p = BooleanParam()
        assert p is not None

    def test_float_param(self):
        from pyhwpxlib.objects.common.parameters import FloatParam
        p = FloatParam()
        assert p is not None

    def test_list_param(self):
        from pyhwpxlib.objects.common.parameters import ListParam
        p = ListParam()
        assert p is not None
