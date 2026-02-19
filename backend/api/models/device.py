"""
Models para dispositivos.
"""

from typing import Optional
from pydantic import BaseModel


class DeviceInfo(BaseModel):
    """Información de un dispositivo Android."""
    device_id: str
    device_name: str
    status: str  # online, offline, unauthorized
    platform: str = "Android"
    version: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
