import asyncio

import jot


def args(*args, **kwargs):
    def annotator(func):
        if not hasattr(func, "_jot_args"):
            func._jot_args = []
        func._jot_args.append((args, kwargs))
        return func

    return annotator


def select(*args):
    def annotator(func):
        if not hasattr(func, "_jot_selectors"):
            func._jot_selectors = set()
        for arg in args:
            func._jot_selectors.add(arg)
        return func

    return annotator


@args()
@select("uncalled")
@jot.instrument
def fn_uncalled_sync():
    jot.info("running", ord=1)
    return "done"


@args()
@select("tag_one")
@jot.instrument(tag_one=1)
def fn_sync_stag_1():
    jot.info("running", ord=1)
    return "done"


@args()
@select("tag_one", "tag_two")
@jot.instrument(tag_one=1, tag_two=2)
def fn_sync_stag_2():
    jot.info("running", ord=1)
    return "done"


@args()
@select("throws")
@jot.instrument
def fn_uncalled_sync_throws():
    jot.info("running", ord=1)
    raise RuntimeError("oops")
    jot.info("unreachable", ord=2)


@args()
@args(3)
@args(a=3)
@args(3, 4)
@args(3, b=4)
@args(a=3, b=4)
@args(b=4)
@select("uncalled")
@jot.instrument
def fn_uncalled_sync_mixed(a=1, b=2):
    jot.info("running", ord=1)
    return a + b


@args()
@args(3)
@args(a=3)
@args(3, 4)
@args(3, b=4)
@args(a=3, b=4)
@args(b=4)
@select("tag_one")
@jot.instrument(tag_one=1)
def fn_sync_mixed_stag_1(a=1, b=2):
    jot.info("running", ord=1)
    return a + b


@args()
@args(3)
@args(a=3)
@args(3, 4)
@args(3, b=4)
@args(a=3, b=4)
@args(b=4)
@select("tag_two")
@jot.instrument(tag_two=2)
def fn_sync_mixed_stag_2(a=1, b=2):
    jot.info("running", ord=1)
    return a + b


@args()
@args(3)
@args(a=3)
@args(3, 4)
@args(3, b=4)
@args(a=3, b=4)
@args(b=4)
@select("tag_one", "tag_two")
@jot.instrument(tag_two=2, tag_one=1)
def fn_sync_mixed_stag_3(a=1, b=2):
    jot.info("running", ord=1)
    return a + b


@args(tag_one=1)
@args(3, tag_one=1)
@args(a=3, tag_one=1)
@args(3, 4, tag_one=1)
@args(3, b=4, tag_one=1)
@args(a=3, b=4, tag_one=1)
@args(b=4, tag_one=1)
@select("tag_one")
@jot.instrument("tag_one")
def fn_sync_mixed_stag_4(a=1, b=2):
    jot.info("running", ord=1)
    return a + b


@args(tag_one=1)
@args(3, tag_one=1)
@args(a=3, tag_one=1)
@args(3, 4, tag_one=1)
@args(3, b=4, tag_one=1)
@args(a=3, b=4, tag_one=1)
@args(b=4, tag_one=1)
@select("tag_one", "tag_two")
@jot.instrument("tag_one", tag_two=2)
def fn_sync_mixed_stag_5(a=1, b=2):
    jot.info("running", ord=1)
    return a + b


@args()
@select("uncalled")
@jot.instrument
async def fn_uncalled_async():
    jot.info("running", ord=1)
    await asyncio.sleep(0.1)
    jot.info("running", ord=2)
    return "done"


@args()
@select("throws")
@jot.instrument
async def fn_uncalled_async_throws():
    jot.info("running", ord=1)
    await asyncio.sleep(0.1)
    raise RuntimeError("oops")
    jot.info("unreachable", ord=2)


@args()
@jot.instrument
async def fn_uncalled_async_no_suspend():
    jot.info("running", ord=1)
    return "done"


@args()
@jot.instrument
async def fn_uncalled_async_two_suspensions():
    jot.info("running", ord=1)
    await asyncio.sleep(0.1)
    jot.info("running", ord=2)
    await asyncio.sleep(0.1)
    jot.info("running", ord=3)
    return "done"


@args()
@select("tag_one")
@jot.instrument(tag_one=1)
async def fn_one_suspension_1():
    jot.info("running", ord=1)
    await asyncio.sleep(0.1)
    jot.info("running", ord=2)
    return "done"


@args(tag_one=1)
@select("tag_one", "tag_two")
@jot.instrument("tag_one", tag_two=2)
async def fn_one_suspension_2():
    jot.info("running", ord=1)
    await asyncio.sleep(0.1)
    jot.info("running", ord=2)
    return "done"
