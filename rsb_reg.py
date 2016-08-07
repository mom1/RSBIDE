# coding=cp1251
import os
import sublime
import sublime_plugin

global fallback_encoding
fallback_encoding = "Cyrillic (Windows 1251)"
global currfolder
currfolder = ""

global FastReport3
global FieldControl
global RSBarCode
global RSBlobDriver
global RSCmnCtl
global RSComProvider
global RSFileRunner
global RSFM
global RSFMDT
global RSFUtils
global RSGrid
global RSOleDBProvider
global TreeControl
global RSBControls
global ChilkatFtp2
global ChilkatMail_v7_9
global ChilkatUtil

FastReport3 = r'frxCOM.dll'
FieldControl = r'FieldControl.dll'
RSBarCode = r'RSBarCode.dll'
RSBlobDriver = r'RSBlobDriver.dll'
RSCmnCtl = r'RSCmnCtl.dll'
RSComProvider = r'RSComProvider.dll'
RSFileRunner = r'RSFileRunner.dll'
RSFM = r'RSFM.dll'
RSFMDT = r'RSFMDT.dll'
RSFUtils = r'RSFUtils.dll'
RSGrid = r'RSGrid.dll'
RSOleDBProvider = r'RSOleDBProvider.dll'
TreeControl = r'TreeControl.dll'
RSBControls = r'RSBControls.dll'
ChilkatFtp2 = r'ChilkatFtp2.dll'
ChilkatMail_v7_9 = r'ChilkatMail_v7_9.dll'
ChilkatUtil = r'ChilkatUtil.dll'


class RsbRegCommand(sublime_plugin.WindowCommand):

    def run(self):
        os.chdir(currfolder)
        import struct
        from subprocess import call

        global FastReport3
        global FieldControl
        global RSBarCode
        global RSBlobDriver
        global RSCmnCtl
        global RSComProvider
        global RSFileRunner
        global RSFM
        global RSFMDT
        global RSFUtils
        global RSGrid
        global RSOleDBProvider
        global TreeControl
        global RSBControls
        global ChilkatFtp2
        global ChilkatMail_v7_9
        global ChilkatUtil

        regsvr32 = "regsvr32.exe"
        if 8 * struct.calcsize("P") == 64:
            regsvr32 = os.path.join(
                os.path.expandvars("%SystemRoot%"), "syswow64", regsvr32)

        print(self.ok_false(call(
            [regsvr32, FastReport3, FieldControl, RSBarCode,
             RSBlobDriver, RSCmnCtl, RSComProvider,
             RSFileRunner, RSFM, RSFMDT, RSFUtils,
             RSGrid, RSOleDBProvider, TreeControl, RSBControls,
             ChilkatFtp2, ChilkatMail_v7_9, ChilkatUtil,
              "-s"])))

    def ok_false(self, iRet):
        if iRet == 0:
            sublime.status_message("DllRegister RS-Balance 3: OK")
            return _make_text_safeish(
                "DllRegister RS-Balance 3: OK", fallback_encoding)
        else:
            sublime.status_message("DllRegister RS-Balance 3: FAIL")
            return _make_text_safeish(
                "DllRegister RS-Balance 3: Ошибка", fallback_encoding)

    def active_view(self):
        return self.window.active_view()

    def _is_rsb(self):
        global currfolder
        global FastReport3
        global FieldControl
        global RSBarCode
        global RSBlobDriver
        global RSCmnCtl
        global RSComProvider
        global RSFileRunner
        global RSFM
        global RSFMDT
        global RSFUtils
        global RSGrid
        global RSOleDBProvider
        global TreeControl
        global RSBControls
        global ChilkatFtp2
        global ChilkatMail_v7_9
        global ChilkatUtil

        currfolder = sublime.expand_variables(
            "$folder", sublime.active_window().extract_variables())
        return (
            os.path.lexists(currfolder + '\\' + FastReport3) and
            os.path.lexists(currfolder + '\\' + FieldControl) and
            os.path.lexists(currfolder + '\\' + RSBarCode) and
            os.path.lexists(currfolder + '\\' + RSBlobDriver) and
            os.path.lexists(currfolder + '\\' + RSCmnCtl) and
            os.path.lexists(currfolder + '\\' + RSComProvider) and
            os.path.lexists(currfolder + '\\' + RSFileRunner) and
            os.path.lexists(currfolder + '\\' + RSFM) and
            os.path.lexists(currfolder + '\\' + RSFMDT) and
            os.path.lexists(currfolder + '\\' + RSFUtils) and
            os.path.lexists(currfolder + '\\' + RSGrid) and
            os.path.lexists(currfolder + '\\' + RSOleDBProvider) and
            os.path.lexists(currfolder + '\\' + TreeControl) and
            os.path.lexists(currfolder + '\\' + RSBControls) and
            os.path.lexists(currfolder + '\\' + ChilkatFtp2) and
            os.path.lexists(currfolder + '\\' + ChilkatMail_v7_9) and
            os.path.lexists(currfolder + '\\' + ChilkatUtil)
        )

    def is_enabled(self):
        return self._is_rsb()


def plugin_loaded():
    global fallback_encoding
    fallback_encoding = sublime.active_window().active_view().settings().get(
        'fallback_encoding').rpartition('(')[2].rpartition(')')[0]


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
