"""spacegraph: spaces as data. Describe a space, a street or a beach once, place a virtual camera, and get what is in
frame, where, and how it reads (left/right, depth, mirrors), so every shot of the same place stays consistent."""
from .check import check
from .describe import draft, report
from .scene import Obj, Scene, SceneError, Space, load
from .topmap import topmap
from .view import Camera, camera_for, view

__all__ = ["Camera", "Obj", "check", "Scene", "SceneError", "Space", "camera_for", "draft", "load", "report", "topmap", "view"]
__version__ = "0.3.0"
