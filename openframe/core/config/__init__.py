"""
openframe/core/config/
=======================
Base configuration primitives for all OpenFrame adapter packages.

Every adapter config class subclasses ``BaseAdapterSettings``, which reads
field values from environment variables via Pydantic Settings.

Usage::

    from openframe.core.config import BaseAdapterSettings
"""
from __future__ import annotations

from openframe.core.config.settings import BaseAdapterSettings

__all__ = ["BaseAdapterSettings"]
