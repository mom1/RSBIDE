# -*- coding: utf-8 -*-
# @Author: mom1
# @Date:   2016-07-28 12:47:41
# @Last Modified by:   mom1
# @Last Modified time: 2016-08-11 19:46:52
import os
import time
import RSBIDE.common.path as Path
from RSBIDE.common.verbose import log


ID = 'Parser'


def get_imp2(i, project, all_imports):
    for rf in project.find_file(i):
        if not rf:
            continue
        if rf in all_imports:
            continue
        all_imports.append(rf)
    return all_imports


def get_imp(find_files, project, all_imports):
    for x, val in find_files.items():
        for i in val[3].get('imports', []):
            all_imports = get_imp2(i, project, all_imports)
    return all_imports


def get_import_tree(fName, project, add_self=False):
    t = time.time()
    all_imports = []
    always_import = []
    project_folder = project.get_directory()
    file = Path.posix(Path.get_absolute_path(project_folder, fName))
    sfile = Path.posix(os.path.relpath(file, project_folder))
    always_import += project.filecache.cache.always_import
    always_import = [i for j in always_import for i in project.find_file(j + '.mac')]
    if add_self:
        all_imports.append(sfile)
    else:
        all_imports += get_imp(project.find_file(sfile), project, all_imports)
    for i in all_imports:
        all_imports = get_imp(project.find_file(i), project, all_imports)
    if (time.time() - t) > 0.5:
        log(ID, 'Долгая обработка файла:', sfile, len(all_imports), str(time.time() - t))
    all_imports.extend(always_import)
    return all_imports


def get_globals_completion(imports, project, prefix=None):
    result = []
    for x in imports:
        filecache = project.filecache.cache.files.get(x, {})
        if len(filecache) > 3:
            result += filecache[3].get('globals', [])
    return result


def get_parent_completion(s_class, project, prefix=None):
    result = []
    l_class = []
    if s_class is None or s_class == '':
        return []
    l_class.append(s_class)
    for x in l_class:
        filecache = project.filecache.cache.class_struct.get(x, {})
        if filecache.get('parent', None) is not None:
            l_class.append(filecache.get('parent'))
        result += filecache.get('variable', [])
        result += filecache.get('macro', [])
    return result
