import contextlib

from psycopg2.extensions import cursor

import jot


class JotCursor(cursor):
    def _jot_start(self, name, args, **dtags):
        self._jot_finish()
        if args is not None:
            dtags["args"] = ",".join(str(a) for a in args)
        jot.start(name, dtags)
        self.jot = jot.active
        return dtags

    def _jot_finish(self):
        if hasattr(self, "jot"):
            self.jot.finish()
            del self.jot

    @contextlib.contextmanager
    def _finishing(self):
        yield
        if self.rownumber >= self.rowcount:
            self._jot_finish()

    def execute(self, sql, args=None):
        dtags = self._jot_start("query", args, sql=sql)

        try:
            cursor.execute(self, sql, args)
            self.jot.event("query complete", dtags)
        except Exception as exc:
            self.jot.error("Query Error", exc, dtags)
            raise

    def executemany(self, sql, vars_list):
        with jot.span("multiquery", sql=sql):
            return cursor.executemany(self, sql, vars_list)

    def callproc(self, procname, args=[]):
        self._jot_start("callproc", args, function=procname)
        return cursor.callproc(self, procname, args)

    def close(self):
        self._jot_finish()
        return cursor.close(self)

    def __del__(self):
        self._jot_finish()

    def fetchall(self):
        with self._finishing():
            return cursor.fetchall(self)

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize
        with self._finishing():
            return cursor.fetchmany(self, size)

    def fetchone(self):
        with self._finishing():
            return cursor.fetchone(self)

    def copy_from(self, file, table, sep="\t", null="\\N", size=8192, columns=None):
        with jot.span("copy_from", table=table):
            return cursor.copy_from(self, file, table, sep, null, size, columns)

    def copy_to(self, file, table, sep="\t", null="\\N", columns=None):
        with jot.span("copy_to", table=table):
            return cursor.copy_to(self, file, table, sep, null, columns)

    def copy_expert(self, sql, file, size=8192):
        with jot.span("copy_expert", sql=sql):
            return cursor.copy_expert(self, sql, file, size)
