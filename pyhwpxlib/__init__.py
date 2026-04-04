"""pyhwpxlib - Python port of hwpxlib for HWPX file generation."""
import logging

__version__ = "0.1.0"

# Library best practice: NullHandler prevents "No handler found" warnings
# when the host application has not configured logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())
