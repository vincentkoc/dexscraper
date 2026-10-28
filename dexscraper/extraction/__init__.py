"""Binary protocol extraction heuristics, split out of ``dexscraper.scraper``.

``DexScraper`` composes these mixins; they are internal and expect the
attributes ``DexScraper.__init__`` sets up.
"""

from .metadata import MetadataExtractionMixin
from .numeric import NumericExtractionMixin
from .records import RecordAssemblyMixin
from .symbols import SymbolExtractionMixin

__all__ = [
    "MetadataExtractionMixin",
    "NumericExtractionMixin",
    "RecordAssemblyMixin",
    "SymbolExtractionMixin",
]
