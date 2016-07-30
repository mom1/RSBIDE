# -*- coding: utf-8 -*-
# @Author: mom1
# @Date:   2016-07-28 12:47:41
# @Last Modified by:   mom1
# @Last Modified time: 2016-07-30 15:16:29
import os
import time
import RSBIDE.common.path as Path
from RSBIDE.common.verbose import log, verbose


ID = 'Parser'
global done_im
done_im = []


def get_imports_cache(fName, project):
    global done_im
    t = time.time()
    if not fName:
        verbose(ID, 'Нет файла для анализа')
        return []
    if not project:
        verbose(ID, 'Без проекта импорта нет')
        return []
    imports = []
    always_import = []
    if len(done_im) == 0:
        always_import += project.filecache.cache.always_import
        always_import = [i for j in always_import for i in project.find_file('/' + j + '.mac')]
        imports += always_import
    project_folder = project.get_directory()
    file = Path.posix(Path.get_absolute_path(project_folder, fName))
    sfile = Path.posix(os.path.relpath(file, project_folder))
    find_files = project.find_file(sfile)
    for x, val in find_files.items():
        if x not in done_im:
            imports += [x]
            done_im += [x]
        for i in val[3].get('imports', []):
            relatives = [rf for rf in project.find_file('/' + i) if rf not in done_im]
            relatives += [ai for ai in always_import if ai not in done_im]
            imports += relatives
            done_im += relatives
            for k in relatives:
                imports += get_imports_cache(k, project)
    imports += [i for i in always_import if i not in done_im]
    if (time.time() - t) > 0.5:
        log(ID, 'Догая обработка файла:', sfile, len(imports), str(time.time() - t))
    return imports
