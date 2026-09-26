"""Pytest bootstrap: make the project root importable as `backend.*`."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
