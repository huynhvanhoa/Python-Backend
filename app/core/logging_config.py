import logging

from app.core.config import settings


def configure_logging() -> None:
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
        ),
    )


class RequestIdFilter(logging.Filter):
    def __init__(self, default_request_id: str = "-") -> None:
        super().__init__()
        self.default_request_id = default_request_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = self.default_request_id
        return True


def attach_request_id_filter() -> None:
    request_filter = RequestIdFilter()
    root_logger = logging.getLogger()

    if not any(
        isinstance(existing, RequestIdFilter) for existing in root_logger.filters
    ):
        root_logger.addFilter(request_filter)
