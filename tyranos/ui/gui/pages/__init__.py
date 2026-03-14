"""Pages package for Tyranos GUI."""

from .automate import AutomatePage
from .chat import ChatPage
from .distro_page import DistroPage
from .history import HistoryPage
from .home import HomePage
from .n8n_page import N8nPage
from .settings import SettingsPage

__all__ = [
    "AutomatePage",
    "ChatPage",
    "DistroPage",
    "HistoryPage",
    "HomePage",
    "N8nPage",
    "SettingsPage",
]
