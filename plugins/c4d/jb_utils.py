import sys

import c4d
from contextlib import contextmanager

def is_headless() -> bool:
    """
    Headless-режим: c4dpy или Cinema 4D Commandline.
    """
    # Для c4dpy — имя исполняемого содержит "c4dpy"
    executable = sys.argv[0].lower() if sys.argv else ""
    return "c4dpy" in executable

@contextmanager
def busy_cursor(status_text: str = ""):
    if status_text:
        c4d.StatusSetText(status_text)
    c4d.gui.SetMousePointer(c4d.MOUSE_BUSY)
    try:
        yield
    finally:
        c4d.gui.SetMousePointer(c4d.MOUSE_NORMAL)
        c4d.StatusClear()
        
def confirm(message: str) -> bool:
    if is_headless():
        return True 
    return c4d.gui.QuestionDialog(message)