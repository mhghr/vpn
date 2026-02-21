"""Handlers package with modularized registration files."""

from .common import dp

from . import callback_handlers  # noqa: F401
from . import user  # noqa: F401
from . import admin  # noqa: F401

__all__ = ["dp"]
