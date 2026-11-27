# Observe the SDK's successful route messages in this notebook kernel.
import io
import logging
from qbraid._logging import logger as _qb012_logger

_qb012_routes = io.StringIO()
_qb012_handler = logging.StreamHandler(_qb012_routes)
_qb012_logger.addHandler(_qb012_handler)
