# -*- coding: utf-8 -*-
# @Author: Maximus
# @Date:   2018-03-19 20:17:13
# @Last Modified by:   mom1
# @Last Modified time: 2018-03-29 20:03:46

import sublime
import xml.etree.ElementTree as ET
from RSBIDE.common.RsbIde_print_panel import get_panel, kill_panel
# import time


def generat_scope(panel, scope):
    reg_list = panel.find_by_selector(scope)
    for reg in reg_list:
        yield reg


def parse(source, filename='<unknown>', mode='.mac'):
    pref = 'RSBIDE:Parse_file_'  # Префикс для панели парсинга
    ret_ast = {}
    if mode == '.xml':
        return parse_xml(source, filename)

    parse_panel = get_panel(sublime.active_window().active_view(), source, name_panel=pref + filename)
    # t = time.time()
    ret_ast['import'] = [parse_panel.substr(i) for i in parse_panel.find_by_selector('import.file.mac')]
    ret_ast['symbols'] = []
    ret_ast['parent'] = []

    def add_symbol(symbol, scope, hint='', rowcol=(0, 0)):
        ret_ast['symbols'].append((symbol, scope, hint, rowcol))

    # lists
    all_cls_macros_names = parse_panel.find_by_selector('meta.class.mac meta.macro.mac entity.name.function.mac')
    all_cls_macros = parse_panel.find_by_selector('meta.class.mac meta.macro.mac')
    all_cls_vars = parse_panel.find_by_selector('meta.class.mac variable.declare.name.mac - (meta.macro.mac, meta.class.mac meta.class.mac)')
    all_cls_parent = parse_panel.find_by_selector('entity.other.inherited-class.mac')

    # generators
    g_class = generat_scope(parse_panel, 'meta.class.mac')
    all_cls_name_reg = generat_scope(parse_panel, 'meta.class.mac entity.name.class.mac')
    g_all = generat_scope(
        parse_panel,
        'variable.declare.name.mac - (meta.class.mac, meta.macro.mac)'
    )
    all_g_macros = generat_scope(parse_panel, 'meta.macro.mac - (meta.class.mac)')
    all_g_name_macros = generat_scope(parse_panel, 'meta.macro.mac entity.name.function.mac - (meta.class.mac)')

    # join name region
    g_class = zip(g_class, all_cls_name_reg)
    g_macros = zip(all_g_macros, all_g_name_macros)

    for g in g_all:
        g_scop = ['global']
        if parse_panel.match_selector(g.begin(), 'meta.const.mac'):
            g_scop = ['const']
        elif parse_panel.match_selector(g.begin(), 'variable.declare.name.mac'):
            g_scop = ['var']
        add_symbol(parse_panel.substr(g), g_scop, rowcol=parse_panel.rowcol(g.begin()))

    for g_m in g_macros:
        g_param_macros = [gpm for gpm in parse_panel.find_by_selector('variable.parameter.macro.mac - (meta.class.mac)') if g_m[0].contains(gpm)]
        hint = ", ".join(["${%s:%s}" % (k + 1, parse_panel.substr(v).strip()) for k, v in enumerate(g_param_macros)])
        add_symbol(parse_panel.substr(g_m[1]), ['macro'], hint=hint, rowcol=parse_panel.rowcol(g_m[1].begin()))

    for itc_cls in g_class:
        cls = itc_cls[0]
        cls_vars = [cv for cv in all_cls_vars if cls.contains(cv)]
        cls_macros = [cl for cl in all_cls_macros if cls.contains(cl)]
        cls_macros_names = [cmn for cmn in all_cls_macros_names if cls.contains(cmn)]
        name_cls = parse_panel.substr(itc_cls[1])
        add_symbol(name_cls, ['class'], rowcol=parse_panel.rowcol(itc_cls[1].begin()))
        scope = [name_cls]

        cls_parent = [parent for parent in all_cls_parent if cls.contains(parent)]

        if cls_parent:
            ret_ast['parent'] += [(name_cls, parse_panel.substr(cls_parent[0]))]

        for c_var in cls_vars:
            add_symbol(parse_panel.substr(c_var), scope + ['var in class'], rowcol=parse_panel.rowcol(c_var.begin()))

        gen_mac = zip(cls_macros, cls_macros_names)
        for c_elem in gen_mac:
            param_macros = [gpm for gpm in parse_panel.find_by_selector('meta.class.mac variable.parameter.macro.mac') if c_elem[0].contains(gpm)]
            hint = ", ".join(["${%s:%s}" % (k + 1, parse_panel.substr(v).strip()) for k, v in enumerate(param_macros)])
            add_symbol(parse_panel.substr(c_elem[1]), scope + ['macro in class'], hint=hint, rowcol=parse_panel.rowcol(c_elem[1].begin()))

    kill_panel(pref + filename)
    return ret_ast


def parse_xml(source, filename):
        """ Кэшируем метаданные
        """
        ret_ast = {}
        ret_ast['xml_symbols'] = []

        def add_symbol(symbol, scope, hint='', rowcol=(0, 0)):
            ret_ast['xml_symbols'].append((symbol, scope, hint, rowcol))

        root = ET.fromstring(source)
        for o in root.findall("./object"):
            add_symbol(o.get('Name'), ['Object'])
            scope = [o.get('Name')]
            add_symbol(o.get('GUID'), scope + ['GUID'])
            if o.get('AncestorID'):
                add_symbol(o.get('AncestorID'), scope + ['AncestorID'])
            for f in o.findall("Field"):
                add_symbol(f.get('Name'), scope + ['Fields'])
            for m in o.findall("Method"):
                add_symbol(m.get('Name'), scope + ['Methods'])
            for k in o.findall("Key"):
                add_symbol(k.get('Name'), scope + ['Keys'])
        return ret_ast
