"""roomgraph: rooms as data. Describe a room once, place a virtual camera, and get what is in frame, where, and how it
reads (left/right, depth, mirrors), so every shot of the same room stays consistent."""
from .describe import draft, report
from .scene import Obj, Room, Scene, load
from .topmap import topmap
from .view import Camera, camera_for, view

__all__ = ["Camera", "Obj", "Room", "Scene", "camera_for", "draft", "load", "report", "topmap", "view"]
__version__ = "0.1.0"
