"""ObjectType enum - all HWPX object types."""
from enum import Enum, auto


class ObjectType(Enum):
    Unknown = auto()
    NormalText = auto()
    HWPXFile = auto()
    hp_switch = auto()
    hp_case = auto()
    hp_default = auto()
    hp_parameterset = auto()
    hp_parameters = auto()
    hp_booleanParam = auto()
    hp_integerParam = auto()
    hp_unsignedintegerParam = auto()
    hp_floatParam = auto()
    hp_stringParam = auto()
    hp_listParam = auto()

    # Version.xml
    hv_HCFVersion = auto()

    # META-INF/manifest.xml
    odf_manifest = auto()
    odf_file_entry = auto()
    odf_encryption_data = auto()
    odf_algorithm = auto()
    odf_key_derivation = auto()
    odf_start_key_generation = auto()

    # META-INF/container.xml
    ocf_container = auto()
    ocf_rootfiles = auto()
    ocf_rootfile = auto()

    # Contents/content.hpf
    opf_package = auto()
    opf_metadata = auto()
    opf_title = auto()
    opf_language = auto()
    opf_meta = auto()
    opf_manifest = auto()
    opf_item = auto()
    opf_spine = auto()
    opf_itemref = auto()

    # Settings.xml
    ha_HWPApplicationSetting = auto()
    ha_CaretPosition = auto()
    config_item_set = auto()
    config_item = auto()

    # Contents/header.xml
    hh_head = auto()
    hh_beginNum = auto()
    hh_refList = auto()
    hh_fontfaces = auto()
    hh_fontface = auto()
    hh_font = auto()
    hh_substFont = auto()
    hh_typeInfo = auto()
    hh_borderFills = auto()
    hh_borderFill = auto()
    hh_slash = auto()
    hh_backSlash = auto()
    hh_leftBorder = auto()
    hh_rightBorder = auto()
    hh_topBorder = auto()
    hh_bottomBorder = auto()
    hh_diagonal = auto()
    hc_fillBrush = auto()
    hc_winBrush = auto()
    hc_gradation = auto()
    hc_color = auto()
    hc_imgBrush = auto()
    hc_img = auto()
    hh_charProperties = auto()
    hh_charPr = auto()
    hh_fontRef = auto()
    hh_ratio = auto()
    hh_spacing = auto()
    hh_relSz = auto()
    hh_offset = auto()
    hh_bold = auto()
    hh_italic = auto()
    hh_underline = auto()
    hh_strikeout = auto()
    hh_outline = auto()
    hh_shadow = auto()
    hh_emboss = auto()
    hh_engrave = auto()
    hh_supscript = auto()
    hh_subscript = auto()
    hh_tabProperties = auto()
    hh_tabPr = auto()
    hh_tabItem = auto()
    hh_numberings = auto()
    hh_numbering = auto()
    hh_paraHead = auto()
    hh_bullets = auto()
    hh_bullet = auto()
    hh_paraProperties = auto()
    hh_paraPr = auto()
    hh_align = auto()
    hh_heading = auto()
    hh_breakSetting = auto()
    hh_margin = auto()
    hc_intent = auto()
    hc_left = auto()
    hc_right = auto()
    hc_prev = auto()
    hc_next = auto()
    hh_lineSpacing = auto()
    hh_border = auto()
    hh_autoSpacing = auto()
    hh_styles = auto()
    hh_style = auto()
    hh_memoProperties = auto()
    hh_memoPr = auto()
    hh_trackChanges = auto()
    hh_trackChange = auto()
    hh_trackChangeAuthors = auto()
    hh_trackChangeAuthor = auto()
    hh_forbiddenWordList = auto()
    hh_forbiddenWord = auto()
    hh_compatibleDocument = auto()
    hh_layoutCompatibility = auto()
    each_layoutCompatibilityItem = auto()
    hh_docOption = auto()
    hh_linkinfo = auto()
    hh_metaTag = auto()
    hh_licensemark = auto()
    hh_trackchageConfig = auto()

    # Contents/section0.xml
    hs_sec = auto()
    hp_p = auto()
    hp_run = auto()
    hp_subList = auto()

    # secPr
    hp_secPr = auto()
    hp_grid = auto()
    hp_startNum = auto()
    hp_visibility = auto()
    hp_lineNumberShape = auto()
    hp_pagePr = auto()
    hp_margin = auto()
    hp_footNotePr = auto()
    hp_autoNumFormat = auto()
    hp_noteLine = auto()
    hp_noteSpacing = auto()
    hp_numbering_for_footnote = auto()
    hp_placement_for_footnote = auto()
    hp_endNotePr = auto()
    hp_numbering_for_endnote = auto()
    hp_placement_for_endnote = auto()
    hp_pageBorderFill = auto()
    hp_offset_for_pageBorderFill = auto()
    hp_masterPage = auto()
    hp_presentation = auto()

    # Control characters
    hp_ctrl = auto()
    hp_colPr = auto()
    hp_colSz = auto()
    hp_colLine = auto()
    hp_fieldBegin = auto()
    hp_metaTag = auto()
    hp_fieldEnd = auto()
    hp_bookmark = auto()
    hp_header = auto()
    hp_footer = auto()
    hp_footNote = auto()
    hp_endNote = auto()
    hp_autoNum = auto()
    hp_newNum = auto()
    hp_pageNumCtrl = auto()
    hp_pageHiding = auto()
    hp_pageNum = auto()
    hp_indexmark = auto()
    hp_firstKey = auto()
    hp_secondKey = auto()
    hp_hiddenComment = auto()

    hp_t = auto()
    hp_markpenBegin = auto()
    hp_markpenEnd = auto()
    hp_titleMark = auto()
    hp_tab = auto()
    hp_lineBreak = auto()
    hp_hyphen = auto()
    hp_nbSpace = auto()
    hp_fwSpace = auto()
    hp_insertBegin = auto()
    hp_insertEnd = auto()
    hp_deleteBegin = auto()
    hp_deleteEnd = auto()

    # AbstractShapeObjectType
    hp_sz = auto()
    hp_pos_for_shapeObject = auto()
    hp_outMargin = auto()
    hp_caption = auto()
    hp_shapeComment = auto()

    # Table object
    hp_tbl = auto()
    hp_inMargin = auto()
    hp_cellzoneList = auto()
    hp_cellzone = auto()
    hp_tr = auto()
    hp_tc = auto()
    hp_cellAddr = auto()
    hp_cellSpan = auto()
    hp_cellSz = auto()
    hp_cellMargin = auto()
    hp_label = auto()

    # Equation object
    hp_equation = auto()
    hp_script = auto()

    hp_chart = auto()

    # AbstractShapeComponentType
    hp_offset_for_shapeComponent = auto()
    hp_orgSz = auto()
    hp_curSz = auto()
    hp_flip = auto()
    hp_rotationInfo = auto()
    hp_renderingInfo = auto()
    hc_transMatrix = auto()
    hc_scaMatrix = auto()
    hc_rotMatrix = auto()

    # Picture object
    hp_pic = auto()
    hp_lineShape = auto()
    hp_imgRect = auto()
    hc_pt0 = auto()
    hc_pt1 = auto()
    hc_pt2 = auto()
    hc_pt3 = auto()
    hp_imgClip = auto()
    hp_imgDim = auto()
    hp_effects = auto()
    hp_shadow_for_effects = auto()
    hp_skew = auto()
    hp_scale = auto()
    hp_effectsColor = auto()
    hp_rgb = auto()
    hp_cmyk = auto()
    hp_scheme = auto()
    hp_system = auto()
    hp_effect = auto()
    hp_glow = auto()
    hp_softEdge = auto()
    hp_reflection = auto()
    hp_alpha = auto()
    hp_pos = auto()

    # OLE object
    hp_ole = auto()
    hc_extent = auto()

    # Container object
    hp_container = auto()

    # AbstractDrawingObjectType
    hp_drawText = auto()
    hp_textMargin = auto()
    hp_shadow_for_drawingObject = auto()

    # Line object
    hp_line = auto()
    hc_startPt = auto()
    hc_endPt = auto()

    # Rectangle object
    hp_rect = auto()

    # Ellipse object
    hp_ellipse = auto()
    hc_center = auto()
    hc_ax1 = auto()
    hc_ax2 = auto()
    hc_start1 = auto()
    hc_start2 = auto()
    hc_end1 = auto()
    hc_end2 = auto()

    # Arc object
    hp_arc = auto()

    # Polygon object
    hp_polygon = auto()
    hc_pt = auto()

    # Curve object
    hp_curve = auto()
    hp_seg = auto()

    # ConnectLine object
    hp_connectLine = auto()
    hp_startPt = auto()
    hp_endPt = auto()
    hp_controlPoints = auto()
    hp_point = auto()

    # TextArt object
    hp_textart = auto()
    hp_textartPr = auto()
    hp_outline = auto()

    # AbstractFormObjectType
    hp_formCharPr = auto()

    # Button object
    hp_btn = auto()

    # RadioButton object
    hp_radioBtn = auto()

    # CheckButton object
    hp_checkBtn = auto()

    # ComboBox object
    hp_comboBox = auto()
    hp_listItem = auto()

    # ListBox object
    hp_listBox = auto()

    # EditBox object
    hp_edit = auto()
    hp_text = auto()

    # ScrollBar object
    hp_scrollBar = auto()

    # Video object
    hp_video = auto()

    # Compose object
    hp_compose = auto()
    hp_charPr = auto()

    # Dutmal object
    hp_dutmal = auto()
    hp_mainText = auto()
    hp_subText = auto()

    hp_linesegarray = auto()
    hp_lineseg = auto()

    masterPage = auto()

    # Document history
    hhs_history = auto()
    hhs_historyEntry = auto()
    hhs_packageDiff = auto()
    hhs_headDiff = auto()
    hhs_bodyDiff = auto()
    hhs_insert = auto()
    hhs_update = auto()
    hhs_delete = auto()

    # Chart
    c_chartSpace = auto()
