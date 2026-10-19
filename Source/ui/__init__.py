"""Pygame UI implementation.

To build a different UI, implement a matching ``run()`` entry point in this
package (or another package) and update ``main.py``. The UI only depends on the
public API exported by ``engine``.
"""
from .app import App, run

__all__ = ['App', 'run']
