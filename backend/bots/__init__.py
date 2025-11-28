"""Bot infrastructure package."""

from backend.bots.max import MaxHub, MaxRunner
from backend.bots.telegram import TelegramHub, TelegramRunner
from backend.bots.vk import VkHub, VkRunner

__all__ = [
    "MaxHub",
    "MaxRunner",
    "TelegramHub",
    "TelegramRunner",
    "VkHub",
    "VkRunner",
]
