"""Lakebase(Postgres) への接続。

トークンは1時間で切れる使い捨てなので、プールを持たず毎回取り直す。
接続を入れ子にしない（同じリクエストの中で2本開くと自分とデッドロックする）。
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Any

from . import config

_HOST: str | None = None


def host() -> str:
    global _HOST
    if _HOST is None:
        inst = config.workspace().database.get_database_instance(name=config.LAKEBASE_INSTANCE)
        if inst.state and inst.state.value != "AVAILABLE":
            raise RuntimeError(f"Lakebase が AVAILABLE ではありません: {inst.state.value}")
        _HOST = inst.read_write_dns
    return _HOST


def user() -> str:
    if config.LAKEBASE_USER:
        return config.LAKEBASE_USER
    me = config.workspace().current_user.me()
    return me.user_name or ""


def token() -> str:
    cred = config.workspace().database.generate_database_credential(
        request_id=str(uuid.uuid4()), instance_names=[config.LAKEBASE_INSTANCE])
    return cred.token


@contextmanager
def conn():
    import psycopg
    with psycopg.connect(host=host(), port=5432, dbname=config.LAKEBASE_DB,
                         user=user(), password=token(), sslmode="require",
                         connect_timeout=15) as c:
        yield c


def fetch(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with conn() as c, c.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def execute(statements: list[tuple[str, tuple]]) -> None:
    """同じトランザクションで複数文を流す。接続は1本だけ開く。"""
    with conn() as c:
        with c.cursor() as cur:
            for sql, params in statements:
                cur.execute(sql, params)
        c.commit()
