"""Adapters that turn uploaded files into list[Post], keeping the engine independent of file formats."""

from .csv_adapter import CsvAdapter
from .instagram import InstagramExportAdapter

__all__ = ["CsvAdapter", "InstagramExportAdapter"]
