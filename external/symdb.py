# -*- coding: utf-8 -*-
import os
import time
import os.path
import sqlite3
import RSBIDE.common.ast_rsl as ast_rsl
from RSBIDE.common.notice import *

PERF_DATA_DB = None


def get_package(path, orig_case=False):
    if path.endswith('.mac') or path.endswith('.xml'):
        path = path[:-4]
    path, module = os.path.split(path)
    if module == '__init__':
        package = []
    else:
        package = [module]
    if orig_case:
        return '.'.join(reversed(package))
    else:
        return '.'.join(reversed(package)).lower()


class InstrumentedCursor(object):
    ''' A limited SQLite3 cursor implementation that records some query
    execution data into another table.
    '''

    def __init__(self, db):
        self.perfdata_cur = db.cursor()
        self.perfdata_cur.executescript('''
            CREATE TABLE IF NOT EXISTS perfdata (
                query TEXT NOT NULL,
                plan TEXT NOT NULL,
                time REAL NOT NULL
            );
        ''')
        self.cur = db.cursor()

    def execute(self, query, params=None):
        query = query.strip()
        if params is None:
            params = ()
        else:
            params = params,

        self.perfdata_cur.execute('EXPLAIN QUERY PLAN ' + query, *params)
        plan = '\n'.join(row[3] for row in self.perfdata_cur)
        tm = time.time()
        self.cur.execute(query, *params)
        tm = time.time() - tm
        self.perfdata_cur.execute('''
            INSERT INTO perfdata(query, plan, time)
            VALUES(:query, :plan, :tm)
        ''', locals())

    def __getattr__(self, name):
        return getattr(self.cur, name)

    def __iter__(self):
        return self.cur


class SymbolDatabase(object):
    has_file_ids = False

    def __init__(self, paths):
        if PERF_DATA_DB:
            self.db = sqlite3.connect(PERF_DATA_DB)
            self.cur = InstrumentedCursor(self.db)
        else:
            self.db = sqlite3.connect(':memory:', check_same_thread=False)
            self.cur = self.db.cursor()
            self.cur.execute('PRAGMA synchronous = 0')
            self.cur.execute('PRAGMA mmap_size = 268435456')
            self.cur.execute('PRAGMA journal_mode = MEMORY')
            self.cur.execute('PRAGMA cache_size = 20480')

        # Load specified databases.
        for dbi, path in enumerate(paths):
            self.cur.execute('''
                ATTACH DATABASE ? AS ?
            ''', (path, 'db{0}'.format(dbi)))
            self.try_create_schema(dbi)

        # Create views of all files and symbols defined in specified databases.
        self.cur.execute('CREATE TEMP VIEW all_symbols AS ' +
                         ' UNION ALL '.join(
                             'SELECT *, {0} AS dbid FROM db{0}.symbols'.format(dbi)
                             for dbi in range(len(paths))))
        self.cur.execute('CREATE TEMP VIEW all_xml_symbols AS ' +
                         ' UNION ALL '.join(
                             'SELECT *, {0} AS dbid FROM db{0}.xml_symbols'.format(dbi)
                             for dbi in range(len(paths))))
        self.cur.execute('CREATE TEMP VIEW all_files AS ' +
                         ' UNION ALL '.join(
                             'SELECT *, {0} AS dbid FROM db{0}.files'.format(dbi)
                             for dbi in range(len(paths))))
        self.cur.execute('CREATE TEMP VIEW all_imports AS ' +
                         ' UNION ALL '.join(
                             'SELECT *, {0} AS dbid FROM db{0}.import_graph'.format(dbi)
                             for dbi in range(len(paths))))
        self.cur.execute('CREATE TEMP VIEW all_parents AS ' +
                         ' UNION ALL '.join(
                             'SELECT *, {0} AS dbid FROM db{0}.parent_graph'.format(dbi)
                             for dbi in range(len(paths))))

    def try_create_schema(self, dbi):
        self.cur.executescript('''
            CREATE TABLE IF NOT EXISTS db{0}.symbols (
                id INTEGER PRIMARY KEY,
                file_id INTEGER REFERENCES files(id),
                symbol TEXT NOT NULL,
                scope TEXT NOT NULL,
                row INTEGER NOT NULL,
                col INTEGER NOT NULL,
                hint TEXT NULL
            );
            CREATE INDEX IF NOT EXISTS db{0}.symbols_symbol ON symbols(symbol);
            CREATE INDEX IF NOT EXISTS db{0}.symbols_scope ON symbols(scope);

            CREATE TABLE IF NOT EXISTS db{0}.xml_symbols (
                file_id INTEGER REFERENCES files(id),
                symbol TEXT NOT NULL,
                scope TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS db{0}.xml_symbols_symbol ON xml_symbols(symbol);

            CREATE TABLE IF NOT EXISTS db{0}.files (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                package TEXT NOT NULL,
                timestamp REAL NOT NULL,
                package_case TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS db{0}.files_path ON files(path);
            CREATE INDEX IF NOT EXISTS db{0}.files_package ON files(package);
            CREATE INDEX IF NOT EXISTS db{0}.files_package_case ON files(package_case);

            CREATE TABLE IF NOT EXISTS db{0}.import_graph (
                id INTEGER PRIMARY KEY,
                file_id INTEGER REFERENCES files(id),
                file_name TEXT NOT NULL,
                import_file_id INTEGER REFERENCES files(id),
                import_name TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS db{0}.import_graph_import_name ON import_graph(import_name);
            CREATE INDEX IF NOT EXISTS db{0}.import_graph_import_file_id ON import_graph(import_file_id, file_id);

            CREATE TABLE IF NOT EXISTS db{0}.parent_graph (
                            id INTEGER PRIMARY KEY,
                            file_id INTEGER REFERENCES files(id),
                            cls_name TEXT NOT NULL,
                            parent_name TEXT NULL);

            CREATE INDEX IF NOT EXISTS db{0}.parent_graph_parent_name ON parent_graph(parent_name);
            CREATE INDEX IF NOT EXISTS db{0}.parent_graph_all ON parent_graph(parent_name, cls_name);
        '''.format(dbi))

    def add(self, dbi, symbol, scope, path, row, col, hint):
        self.cur.execute('''
            INSERT INTO db{0}.symbols(file_id, symbol, scope, row, col, hint)
            VALUES(
                (SELECT id FROM db{0}.files WHERE path = :path),
                :symbol, :scope, :row, :col, :hint
            )
        '''.format(dbi), locals())

    def add_xml(self, dbi, symbol, scope, path):
        self.cur.execute('''
            INSERT INTO db{0}.xml_symbols(file_id, symbol, scope)
            VALUES(
                (SELECT id FROM db{0}.files WHERE path = :path),
                :symbol, :scope
            )
        '''.format(dbi), locals())

    def clear_file(self, dbi, name):
        self.cur.execute('''
            DELETE FROM db{0}.symbols WHERE
                file_id = (SELECT id FROM db{0}.files WHERE path = :name)
        '''.format(dbi), locals())
        self.cur.execute('''
            DELETE FROM db{0}.import_graph WHERE
                file_id = (SELECT id FROM db{0}.files WHERE path = :name)
        '''.format(dbi), locals())
        self.cur.execute('''
            DELETE FROM db{0}.parent_graph WHERE
                file_id = (SELECT id FROM db{0}.files WHERE path = :name)
        '''.format(dbi), locals())
        self.cur.execute('''
            DELETE FROM db{0}.xml_symbols WHERE
                file_id = (SELECT id FROM db{0}.files WHERE path = :name)
        '''.format(dbi), locals())

    def begin_file_processing(self, dbi):
        self.has_file_ids = True
        self.cur.execute('DROP TABLE IF EXISTS file_ids')
        self.cur.execute('''
            CREATE TEMP TABLE file_ids (
                file_id INTEGER NOT NULL
            )
        ''')

    def end_file_processing(self, dbi):
        self.cur.execute('''
            DELETE FROM db{0}.symbols WHERE file_id NOT IN (
                SELECT file_id FROM file_ids)
        '''.format(dbi))
        self.cur.execute('''
            DELETE FROM db{0}.xml_symbols WHERE file_id NOT IN (
                SELECT file_id FROM file_ids)
        '''.format(dbi))
        self.cur.execute('''
            DELETE FROM db{0}.files WHERE id NOT IN (
                SELECT file_id FROM file_ids)
        '''.format(dbi))
        self.cur.execute('''
            DELETE FROM db{0}.parent_graph WHERE file_id NOT IN (
                SELECT file_id FROM file_ids)
        '''.format(dbi))

        self.cur.execute('DELETE FROM db{0}.import_graph WHERE import_file_id IS NULL'.format(dbi))
        self.cur.execute('''
            DELETE FROM db{0}.import_graph WHERE file_id NOT IN (
                SELECT file_id FROM file_ids)
        '''.format(dbi))
        self.cur.execute('DROP TABLE file_ids')
        self.has_file_ids = False
        log('END')

    def update_file_time(self, dbi, path, time):
        self.cur.execute('''
            SELECT id, timestamp FROM db{0}.files WHERE path = :path
        '''.format(dbi), locals())
        try:
            file_id, timestamp = self.cur.fetchone()
        except TypeError:
            package = get_package(path)
            package_case = get_package(path, True)
            self.cur.execute('''
                INSERT INTO db{0}.files(path, package, timestamp, package_case)
                VALUES(:path, :package, :time, :package_case)
            '''.format(dbi), locals())
            file_id = self.cur.lastrowid
            result = True
        else:
            if timestamp < time:
                package = get_package(path)
                self.cur.execute('''
                    UPDATE db{0}.files
                    SET timestamp = :time, package = :package
                    WHERE id = :file_id
                '''.format(dbi), locals())
                result = True
            else:
                result = False

        if self.has_file_ids:
            self.cur.execute('INSERT INTO file_ids VALUES(:file_id)', locals())

        return result

    def add_import(self, dbi, package, import_file, path):
        self.cur.execute('''
            SELECT id FROM db{0}.import_graph WHERE
                file_name = :package
                AND
                import_name = :import_file
        '''.format(dbi), locals())
        _id = self.cur.fetchone()
        if _id is not None:
            return False
        self.cur.execute('''
            INSERT INTO db{0}.import_graph(file_name, import_name, file_id)
            VALUES(:package, :import_file, (SELECT id FROM db{0}.files where path = :path))
        '''.format(dbi), locals())
        self.cur.execute('''
            UPDATE db{0}.import_graph SET import_file_id = (SELECT fl.id FROM db{0}.files fl WHERE fl.package = db{0}.import_graph.import_name)
            WHERE db{0}.import_graph.import_file_id IS NULL AND EXISTS (SELECT 1 FROM db{0}.files WHERE db{0}.files.package = db{0}.import_graph.import_name
            )
        '''.format(dbi))
        result = True

        return result

    def add_parent(self, dbi, cls, parent, path):
        self.cur.execute('''
            INSERT INTO db{0}.parent_graph(cls_name, parent_name, file_id)
            VALUES(:cls, :parent, (SELECT id FROM db{0}.files where path = :path))
        '''.format(dbi), locals())
        result = True

        return result

    def commit(self):
        self.db.commit()

    def _result_row_to_dict(self, row):
        return {
            'symbol': row[0],
            'scope': row[1],
            'package': row[2],
            'row': row[3],
            'col': row[4],
            'file': row[5]
        }

    def occurrences(self, symbol):
        namespace, sep, symbol = symbol.rpartition('.')
        if sep:
            namespace = '*.' + namespace
        else:
            namespace = '*'

        self.cur.execute('''
            SELECT s.symbol, s.scope, f.package, s.row, s.col, f.path
            FROM all_symbols s, all_files f
            WHERE
                s.file_id = f.id AND
                s.dbid = f.dbid AND
                s.symbol = :symbol AND
                '.' || f.package || '.' || s.scope GLOB :namespace
            ORDER BY s.symbol, f.path, s.row
        ''', locals())
        for row in self.cur:
            yield self._result_row_to_dict(row)

    def members(self, package, prefix):
        self.cur.execute('''
            SELECT DISTINCT s.symbol
            FROM all_symbols s, all_files f
            WHERE
                s.file_id = f.id AND
                s.dbid = f.dbid AND
                f.package = :package AND
                s.symbol GLOB :prefix || '*' AND
                s.scope = ''
            ORDER BY s.symbol, f.path, s.row
        ''', locals())
        return (row[0] for row in self.cur)

    def packages(self, prefix, ret_fild='packege', exac=False):
        if exac:
            wh = "= :prefix"
        else:
            wh = "GLOB :prefix || '*'"
        self.cur.execute('''
            SELECT DISTINCT {0}
            FROM all_files
            WHERE package {1}
        '''.format(ret_fild, wh), locals())
        for row in self.cur:
            yield row[0]

    def imports(self, package):
        self.cur.execute('''
            WITH RECURSIVE
            directreports(file_id, import_file_id, lvl) AS (
                SELECT file_id, import_file_id, 0
                FROM all_imports f WHERE f.file_id = (SELECT id FROM all_files WHERE package = :package)
                UNION ALL
                SELECT e.file_id, e.import_file_id, dr.lvl + 1
                FROM all_imports e
                INNER JOIN directreports dr ON e.file_id = dr.import_file_id
            ),
            rep(import_file_id, lvl, parent) AS (
                SELECT DISTINCT dr.import_file_id, dr.lvl, dr.file_id
                from directreports dr ORDER BY dr.lvl
            )
            SELECT af.package_case
            , MAX (af1.package_case) parent
            , MAX (dr.lvl)
            FROM rep dr
            INNER JOIN all_files af ON af.id = dr.import_file_id
            INNER JOIN all_files af1 ON af1.id = dr.parent
            GROUP BY af.package_case
            ORDER BY dr.lvl
        ''', locals())
        for row in self.cur:
            yield (row[0], row[1], row[2])

    def metadata(self, prefix, isbac=False):
        self.cur.execute('''
            SELECT DISTINCT symbol, substr(scope, instr(scope, '.') + 1)
            FROM all_xml_symbols
            WHERE symbol LIKE :prefix || '%'
            AND (scope GLOB 'Object' OR scope GLOB '*Fields' OR scope GLOB '*Methods')
        ''', locals())
        for row in self.cur:
            i = row[0]
            if isbac:
                i = '\\"' + row[0] + '\\"'
            yield ('%s\t%s' % (row[0], row[1]), i)

    def metadata_object(self, obj):
        self.cur.execute('''
            WITH RECURSIVE
                directreports(symbol, "scope", AncestorID, "level") AS (
                    SELECT symbol, "scope", (SELECT symbol FROM all_xml_symbols WHERE "scope" LIKE s.symbol || '.AncestorID') as AncestorID, 0
                    FROM all_xml_symbols s WHERE s.symbol = :obj AND s."scope" = 'Object'
                    UNION ALL
                    SELECT SUBSTR(s1."scope", 1, instr(s1."scope", '.') -1 ) as parent, s1."scope"
                    , (SELECT symbol FROM all_xml_symbols WHERE "scope" LIKE SUBSTR(s1."scope", 1, instr(s1."scope", '.') -1 ) || '.AncestorID') as AncestorID
                    , directreports."level" + 1
                    FROM directreports, all_xml_symbols s1
                    WHERE directreports.AncestorID = s1.symbol AND s1."scope" LIKE '%.GUID'
                )
                select DISTINCT symbol, SUBSTR("scope", instr("scope", '.') + 1) as sTYPE from all_xml_symbols WHERE "scope" IN
                (
                    select DISTINCT symbol || '.Fields' from directreports
                )
                ORDER by sTYPE
        ''', locals())
        for row in self.cur:
            yield ('%s\t%s' % (row[0], row[1]), '\\"' + row[0] + '\\"')

    def symbol_in_parent(self, symbol, cur_class):
        self.cur.execute('''
        SELECT DISTINCT
            (SELECT "scope" from all_symbols where symbol = :symbol and "scope" LIKE s.symbol || '.%'),
            s.symbol,
            s.file_id
        FROM all_symbols s
        WHERE s."scope" = :cur_class || '.parent'
        ''', locals())
        for row in self.cur:
            if row[0] is None:
                yield from self.symbol_in_parent(symbol, row[1])
            yield (row[1], row[2])

    def parent_symbols(self, obj, prefix='', exac=False):
        if exac:
            wh = "= :prefix"
        else:
            wh = "LIKE :prefix || '%'"
        self.cur.execute('''
            WITH RECURSIVE
                rep(pn, "level") AS (
                SELECT pg.parent_name as pn, 0
                FROM all_parents pg WHERE pg.cls_name = :obj
                UNION ALL
                SELECT pg1.parent_name,
                rep."level" + 1
                FROM rep, all_parents pg1
                WHERE rep.pn = pg1.cls_name
            )
            select DISTINCT s.symbol, s."scope", hint from all_symbols s
            WHERE "scope" IN
            (
                select DISTINCT pn || '.var in class' from rep
                UNION ALL
                select DISTINCT pn || '.macro in class' from rep
            )
            AND symbol {0}
            ORDER by "scope" COLLATE NOCASE
        '''.format(wh), locals())
        for row in self.cur:
            hint = '(%s)' % (row[2]) if row[2] else ''
            yield ('%s\t%s' % (row[0], row[1]), row[0] + hint)

    def parent_symbols_go(self, obj, prefix=''):
        self.cur.execute('''
            WITH RECURSIVE
                rep(pn, "level") AS (
                SELECT pg.parent_name AS pn, 0
                FROM all_parents pg WHERE pg.cls_name like :obj
                UNION ALL
                SELECT pg1.parent_name,
                rep."level" + 1
                FROM rep, all_parents pg1
                WHERE rep.pn = pg1.cls_name
            ),
            repd(pn) AS (
                SELECT DISTINCT pn FROM rep
            )
            select DISTINCT s.symbol, s."scope", f.package, s."row", s.col, f."path"
                FROM repd r
                INNER JOIN all_symbols s ON s."scope" = r.pn || '.var in class' OR s."scope" = r.pn || '.macro in class'
                INNER JOIN all_files f ON s.file_id = f.id
            WHERE s.symbol LIKE :prefix
        ''', locals())
        for row in self.cur:
            yield self._result_row_to_dict(row)

    def globals_in_packages(self, package, prefix, get_types=['class', 'const', 'var', 'macro', 'global']):
        include = Settings.proj_settings.get('ALWAYS_IMPORT')
        s_inc = "in ('%s')" % ("', '".join(include)) if len(include) > 0 else ' = 0'
        self.cur.execute('''
            WITH RECURSIVE
                directreports(file_id, import_file_id, lvl) AS (
                    SELECT file_id, import_file_id, 0
                    FROM all_imports f WHERE f.file_id = (SELECT id FROM all_files WHERE package = :package)
                    UNION ALL
                    SELECT e.file_id, e.import_file_id, dr.lvl + 1
                    FROM all_imports e
                    INNER JOIN directreports dr ON e.file_id = dr.import_file_id
                ),
                rep(import_file_id) AS (
                    SELECT DISTINCT import_file_id
                    from directreports dr
                    UNION ALL
                    SELECT f.ID as import_file_id
                    FROM all_files f
                    WHERE package {1}
                )
            SELECT DISTINCT s.symbol, s."scope", s.hint
            FROM rep dr
            INNER JOIN all_files af ON af.id = dr.import_file_id
            INNER JOIN all_symbols s on af.id = s.file_id AND s."scope" IN ('{0}')
            WHERE s.symbol LIKE :prefix || '%'
        '''.format("', '".join(get_types), s_inc.lower()), locals())
        for row in self.cur:
            hint = '(%s)' % (row[2]) if row[2] else ''
            yield ('%s\t%s' % (row[0], row[1]), row[0] + hint)

    def globals_in_packages_go(self, package, prefix, get_types=['class', 'const', 'var', 'macro', 'global']):
        include = Settings.proj_settings.get('ALWAYS_IMPORT')
        s_inc = "in ('%s')" % ("', '".join(include)) if len(include) > 0 else ' = 0'
        ssql = '''
            WITH RECURSIVE
                directreports(file_id, import_file_id, lvl) AS (
                    SELECT file_id, import_file_id, 0
                    FROM all_imports f WHERE f.file_id = (SELECT id FROM all_files WHERE package = :package)
                    UNION ALL
                    SELECT e.file_id, e.import_file_id, dr.lvl + 1
                    FROM all_imports e
                    INNER JOIN directreports dr ON e.file_id = dr.import_file_id
                ),
                rep(import_file_id) AS (
                    SELECT DISTINCT import_file_id
                    from directreports dr
                    UNION ALL
                    SELECT f.ID as import_file_id
                    FROM all_files f
                    WHERE package {1}
                )
            SELECT DISTINCT s.symbol, s."scope", af.package, s.row, s.col, af."path"
            FROM rep dr
            INNER JOIN all_files af ON af.id = dr.import_file_id
            INNER JOIN all_symbols s on af.id = s.file_id AND s."scope" IN ('{0}')
            WHERE s.symbol LIKE :prefix
        '''.format("', '".join(get_types), s_inc.lower())
        self.cur.execute(ssql, locals())
        for row in self.cur:
            yield self._result_row_to_dict(row)


class SymbolExtractor(object):
    def __init__(self, db, dbi, path):
        self.path = path
        self.db = db
        self.dbi = dbi
        self.scope = []
        self.this = None

    def add_symbol(self, name, rowcol, _hint):
        self.db.add(self.dbi, name, '.'.join(self.scope), self.path,
                    rowcol[0], rowcol[1], hint=_hint)

    def add_xml_symbol(self, name):
        self.db.add_xml(self.dbi, name, '.'.join(self.scope), self.path)

    def visit(self, file_ast):
        for key, value in file_ast.items():
            if key == 'import':
                for item in value:
                    self.db.add_import(self.dbi, get_package(self.path), get_package(item), self.path)
            elif key == 'symbols':
                for item in value:
                    self.scope = item[1]
                    self.add_symbol(item[0], item[3], item[2])
            elif key == 'parent':
                for item in value:
                    self.db.add_parent(self.dbi, item[0], item[1], self.path)
            elif key == 'xml_symbols':
                for item in value:
                    self.scope = item[1]
                    self.add_xml_symbol(item[0])


db = None
Settings = None


def set_databases(paths):
    global db
    db = SymbolDatabase(paths)


def set_settings(settings):
    global Settings
    Settings = settings


def begin_file_processing(dbi):
    db.begin_file_processing(dbi)


def end_file_processing(dbi):
    t = time.time()
    db.end_file_processing(dbi)
    log('end_file_processing', "%.3f" % (time.time() - t))


def process_file(dbi, path):
    path = os.path.normpath(path)
    debug('process_file', path)
    if db.update_file_time(dbi, path, os.path.getmtime(path)):
        db.clear_file(dbi, path)
        try:
            file_ast = ast_rsl.parse(open(path, encoding='Windows 1251').read(), path, os.path.splitext(path)[1])
        except Exception as e:
            log('Ошибка парсинга')
            return False
        SymbolExtractor(db, dbi, path).visit(file_ast)
        return True
    else:
        return False


def query_occurrences(symbol):
    return list(db.occurrences(symbol))


def query_members(package, prefix):
    return list(db.members(package, prefix))


def query_packages(prefix, case=False):
    if case:
        return list(db.packages(prefix, 'package_case'))
    return list(db.packages(prefix))


def query_packages_info(prefix, flds_info=['path']):
    return list(db.packages(prefix, ', '.join(flds_info), True))


def query_imports(package):
    yield from db.imports(package)


def query_metadata(prefix, isbac):
    return list(db.metadata(prefix, isbac))


def query_metadata_object(obj):
    if not obj:
        return []
    return list(db.metadata_object(obj))


def query_parent_symbols(obj, prefix):
    if not obj:
        return []
    yield from db.parent_symbols(obj, prefix)


def query_parent_symbols_go(obj, prefix):
    return list(db.parent_symbols_go(obj, prefix))


def query_globals_class(package, prefix):
    yield from db.globals_in_packages(package, prefix, ['class'])


def query_globals_in_packages(package, prefix):
    yield from db.globals_in_packages(package, prefix)


def query_globals_in_packages_go(package, prefix):
    return list(db.globals_in_packages_go(package, prefix))


def commit():
    db.commit()
