bl_info = {
    "name": "Jiko Bridge",
    "author": "JIKO",
    "version": (1, 0),
    "blender": (4, 3, 2),
    "location": "View3D > Sidebar > Jiko Bridge",
    "description": "Jiko Bridge",
    "category": "3D View",
    "doc_url": "https://with-jiko.com",
    "tracker_url": "https://t.me/withjiko",  
}

import sys
import os

root_path = os.path.join(os.path.dirname(__file__))
if root_path not in sys.path:
    sys.path.append(root_path)

src_path = os.path.join(root_path, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from . import src

def register():
    src.register()

def unregister():
    src.unregister()

if __name__ == "__main__":
    register()
