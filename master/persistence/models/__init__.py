"""SQLAlchemy persistence models.

The package keeps the historical ``master.persistence.models`` import path
while allowing model groups to be split into focused modules later.
"""

from .base import Base, utcnow
from .entities import *
