"""Create database tables once, before the web workers start.

Gunicorn starts several workers at the same time. If each one created the tables, they would
race and one would fail with a unique-violation. Running this single step first avoids that.
(In a larger project this is where `alembic upgrade head` would run.)
"""

import logging

from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.db import Base, make_engine

logger = logging.getLogger("init_db")


def init_db(database_url: str) -> None:
    engine = make_engine(database_url)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        init_db(get_settings().database_url)
    except OperationalError:
        logger.exception("Database not reachable")
        raise SystemExit(1) from None
    logger.info("Database tables are ready")


if __name__ == "__main__":
    main()
