# -*- coding: utf-8 -*-
# @Author: Maximus
# @Date:   2018-03-29 00:23:41
# @Last Modified by:   Maximus
# @Last Modified time: 2018-03-29 17:02:15

import os
import sublime
import sublime_plugin
import struct
from RSBIDE.common.notice import *
from subprocess import call


class RsbRegCommand(sublime_plugin.WindowCommand):
    currfolder = ""
    dll_for_reg = [
        r'frxCOM.dll',
        r'FieldControl.dll',
        r'RSBarCode.dll',
        r'RSBlobDriver.dll',
        r'RSCmnCtl.dll',
        r'RSComProvider.dll',
        r'RSFileRunner.dll',
        r'RSFM.dll',
        r'RSFMDT.dll',
        r'RSFUtils.dll',
        r'RSGrid.dll',
        r'RSOleDBProvider.dll',
        r'TreeControl.dll',
        r'RSBControls.dll',
        r'ChilkatFtp2.dll',
        r'ChilkatMail_v7_9.dll',
        r'ChilkatUtil.dll'
    ]
    fallback_encoding = "Cyrillic (Windows 1251)"

    def run(self):
        os.chdir(self.currfolder)

        regsvr32 = "regsvr32.exe"
        if 8 * struct.calcsize("P") == 64:
            regsvr32 = os.path.join(
                os.path.expandvars("%SystemRoot%"), "syswow64", regsvr32)

        log(self.ok_false(call([regsvr32] + self.dll_for_reg + ['-s'])))

    def ok_false(self, iRet):
        if iRet == 0:
            sublime.status_message("DllRegister RS-Balance 3: OK")
            return _make_text_safeish(
                "DllRegister RS-Balance 3: OK", self.fallback_encoding)
        else:
            sublime.status_message("DllRegister RS-Balance 3: FAIL")
            return _make_text_safeish(
                "DllRegister RS-Balance 3: Ошибка", self.fallback_encoding)

    def active_view(self):
        return self.window.active_view()

    def _is_rsb(self):
        self.currfolder = sublime.expand_variables(
            "$folder", sublime.active_window().extract_variables())
        for x in self.dll_for_reg:
            if not os.path.lexists(self.currfolder + '\\' + x):
                log('Нет файла: ' + self.currfolder + '\\' + x)
                return False
        return True

    def is_enabled(self):
        return self._is_rsb()


def plugin_loaded():
    pass


def _make_text_safeish(text, fallback_encoding, method='decode'):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal... and there's no way to tell what's coming out of
    # git in output. So...
    try:
        unitext = getattr(text, method)('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        unitext = getattr(text, method)(fallback_encoding)
    except AttributeError:
        # strongly implies we're already unicode, but just in case let's cast
        # to string
        unitext = str(text)
    return unitext


def norm_path_string(file):
    return file.strip().lower().replace('\\', '/').replace('//', '/')


if int(sublime.version()) < 3000:
    sublime.set_timeout(lambda: plugin_loaded(), 0)
