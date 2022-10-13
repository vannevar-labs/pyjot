import random
from cmath import exp
from io import StringIO
import os

import psycopg2
import pytest

import jot
from jot import log
from jot.base import Target
from jot.pg import JotCursor

PG_CONNECTION_PARAMS = ["user", "password", "host", "port", "database",]

def pg_connection_args():
    args = {}
    for p in PG_CONNECTION_PARAMS:
        env_var_name = f"PG_{p.upper()}"
        if env_var_name in os.environ:
            args[p] = os.environ[env_var_name]
    return args

@pytest.fixture(autouse=True)
def init():
    jot.init(Target(level=log.ALL))


@pytest.fixture
def finish(mocker):
    return mocker.spy(jot.active.target, "finish")


@pytest.fixture(scope="session")
def connection(request):
    if "PG_TESTS" not in os.environ:
        pytest.skip("Psycopg2 tests not configured")
    ctl_args = pg_connection_args()
    ctl_args["database"] = "postgres"
    ctlconn = psycopg2.connect(**ctl_args)
    ctlconn.autocommit = True

    name = f"jot_test_{hex(random.getrandbits(32))[2:]}"
    with ctlconn.cursor() as cursor:
        cursor.execute(f"create database {name}")

    test_args = {**ctl_args, "database": name}
    connection = psycopg2.connect(cursor_factory=JotCursor, **test_args)
    connection.autocommit = True

    yield connection

    connection.close()
    with ctlconn.cursor() as cursor:
        cursor.execute(f"drop database {name}")
    ctlconn.close()


@pytest.fixture
def silent_cursor(connection):
    cursor = connection.cursor(cursor_factory=psycopg2.extensions.cursor)
    yield cursor
    cursor.close()


@pytest.fixture
def cursor(connection):
    cursor = connection.cursor()
    yield cursor
    cursor.close()


@pytest.fixture(scope="session")
def kv_table(connection):
    cursor = connection.cursor(cursor_factory=psycopg2.extensions.cursor)
    cursor.execute("create table kv(k text, v integer)")
    yield
    cursor.execute("drop table kv")


@pytest.fixture
def kv_empty(connection, kv_table):
    cursor = connection.cursor(cursor_factory=psycopg2.extensions.cursor)
    cursor.execute("truncate table kv")


@pytest.fixture
def ab(silent_cursor, kv_empty):
    silent_cursor.execute("insert into kv values ('a', 1), ('b', 2)")


@pytest.fixture(params=["execute", "callproc"])
def rows(request, connection, finish):
    # figure out how many rows to generate
    marker = request.node.get_closest_marker("rows")
    num_rows = marker.args[0] if marker is not None else 1

    # figure out if we're calling execute() or callproc()
    if request.param not in ["execute", "callproc"]:
        raise ValueError("Parameter should be execute or callproc")
    executing = request.param == "execute"

    # create the cursor
    cursor = connection.cursor()

    # start the request to the server
    if executing:
        sql = f"select generate_series(1, {num_rows})"
        cursor.execute(sql)
        expected_name = "query"
        expected_tags = {"sql": sql}
    else:
        cursor.callproc("generate_series", [1, num_rows])
        expected_name = "callproc"
        expected_tags = {"function": "generate_series", "args": f"1,{num_rows}"}

    yield cursor

    if finish.called:
        [tags, span] = finish.call_args.args
        assert tags == expected_tags
        assert span.name == expected_name


#
# cursor tests
#
execute_parameters = [
    ["select * from pg_tables", None],
    ["select * from pg_tables where tablename = %s", ["pg_namespace"]],
    ["select * from pg_tables where tablename = %s or tablename = %s", ["pg_namespace", "pg_class"]],
]


@pytest.mark.parametrize("sql, args", execute_parameters, ids=["nullary", "unary", "binary"])
def test_execute(sql, args, connection, finish):
    cursor = connection.cursor()
    cursor.execute(sql, args)
    cursor.close()

    expected_tags = {"sql": sql}
    if args is not None:
        expected_tags["args"] = ",".join(args)
    [tags, span] = finish.call_args.args
    assert tags == expected_tags
    assert span.name == "query"


def test_execute_del(connection, finish):
    cursor = connection.cursor()
    cursor.execute("select * from pg_tables")
    cursor = None
    finish.assert_called_once()


def test_executemany(cursor, finish):
    result = cursor.executemany("select %s", [[1], [2], [3]])
    assert result is None
    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"sql": "select %s"}
    assert span.name == "multiquery"


def test_callproc(connection, finish):
    cursor = connection.cursor()
    retval = cursor.callproc("generate_series", [1, 3])
    assert retval == [1, 3]
    cursor.close()
    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"function": "generate_series", "args": "1,3"}
    assert span.name == "callproc"


def test_callproc_del(connection, finish):
    cursor = connection.cursor()
    cursor.callproc("generate_series", [1, 2])
    cursor = None
    finish.assert_called_once()


@pytest.mark.rows(3)
def test_fetch_all(rows, finish):
    all = rows.fetchall()
    assert type(all) == list
    assert len(all) == 3
    finish.assert_called_once()


@pytest.mark.rows(2)
def test_fetchone(rows, finish):
    first = rows.fetchone()
    assert type(first) == tuple
    finish.assert_not_called()


@pytest.mark.rows(2)
def test_fetchone_last(rows, finish):
    first = rows.fetchone()
    assert type(first) == tuple
    second = rows.fetchone()
    finish.assert_called_once()


def test_fetchone_extra(rows, finish):
    rows.fetchone()
    second = rows.fetchone()
    assert second is None
    finish.assert_called_once()


@pytest.mark.rows(3)
def test_fetchmany_partial(rows, finish):
    rows = rows.fetchmany(2)
    assert type(rows) == list
    assert len(rows) == 2
    assert type(rows[0]) == tuple

    finish.assert_not_called()


@pytest.mark.rows(3)
def test_fetchmany_exact(rows, finish):
    many = rows.fetchmany(3)
    assert len(many) == 3
    finish.assert_called_once()


@pytest.mark.rows(3)
def test_fetchmany_extra(rows, finish):
    many = rows.fetchmany(4)
    assert len(many) == 3
    finish.assert_called_once()


def test_copy_from_minimal(kv_empty, cursor, finish):
    f = StringIO("z\t26\ny\t\\N\nx\t24\n")
    cursor.copy_from(f, "kv")

    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"table": "kv"}
    assert span.name == "copy_from"


def test_copy_from_maximal(kv_empty, cursor, finish):
    f = StringIO("z\t26\ny\t\\N\nx\t24\n")
    cursor.copy_from(f, "kv", sep="\t", null="\\N", size=8192, columns=["k", "v"])
    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"table": "kv"}
    assert span.name == "copy_from"

    cursor.execute("select * from kv order by k")
    rows = cursor.fetchall()
    assert rows == [("x", 24), ("y", None), ("z", 26)]


def test_copy_to_minimal(ab, cursor, finish):
    f = StringIO()
    cursor.copy_to(f, "kv")

    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"table": "kv"}
    assert span.name == "copy_to"

    data = f.getvalue()
    assert data == "a\t1\nb\t2\n"


def test_copy_to_maximal(ab, cursor, finish):
    f = StringIO()
    cursor.copy_to(f, "kv", sep="\t", null="\\N", columns=["k", "v"])

    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"table": "kv"}
    assert span.name == "copy_to"

    data = f.getvalue()
    assert data == "a\t1\nb\t2\n"


def test_copy_expert_from(kv_empty, cursor, finish):
    sql = "COPY kv FROM STDIN"
    f = StringIO("z\t26\ny\t\\N\nx\t24\n")
    cursor.copy_expert(sql, f, size=1024)

    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"sql": sql}
    assert span.name == "copy_expert"

    cursor.execute("select * from kv order by k")
    rows = cursor.fetchall()
    assert rows == [("x", 24), ("y", None), ("z", 26)]


def test_copy_expert_to(ab, cursor, finish):
    sql = "COPY kv TO STDOUT"
    f = StringIO()
    cursor.copy_expert(sql, f, size=1024)

    finish.assert_called_once()
    [tags, span] = finish.call_args.args
    assert tags == {"sql": sql}
    assert span.name == "copy_expert"

    data = f.getvalue()
    assert data == "a\t1\nb\t2\n"
