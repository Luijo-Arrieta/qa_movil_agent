"""
Endpoints para gestión de dispositivos.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException
from backend.api.models.device import DeviceInfo
from backend.services.device_manager import DeviceManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[DeviceInfo])
async def list_devices():
    """
    Lista los dispositivos Android conectados.
    
    Returns:
        Lista de dispositivos disponibles
    """
    try:
        devices = DeviceManager.list_devices()
        return devices
    except Exception as e:
        logger.error(f"Error listando dispositivos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
