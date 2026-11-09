from sqlalchemy import inspect

from app.db import make_engine
from app.init_db import init_db


def test_creates_tables_and_is_safe_to_run_twice(tmp_path):
    url = f"sqlite:///{tmp_path / 'init.db'}"
    init_db(url)
    init_db(url)  # running it again must not fail
    assert "notes" in inspect(make_engine(url)).get_table_names()
