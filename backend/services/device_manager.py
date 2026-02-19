"""
Gestión de dispositivos Android.
"""

import subprocess
import logging
from typing import List, Optional
from backend.api.models.device import DeviceInfo

logger = logging.getLogger(__name__)


class DeviceManager:
    """Gestiona la conexión y listado de dispositivos Android."""
    
    @staticmethod
    def list_devices() -> List[DeviceInfo]:
        """
        Lista los dispositivos Android conectados.
        
        Returns:
            Lista de dispositivos disponibles
        """
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # Saltar header
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    
                    # Solo incluir dispositivos online
                    if status == "device":
                        device_info = DeviceInfo(
                            device_id=device_id,
                            device_name=device_id,
                            status="online"
                        )
                        devices.append(device_info)
            
            logger.info(f"DeviceManager: Encontrados {len(devices)} dispositivos")
            return devices
            
        except subprocess.TimeoutExpired:
            logger.error("DeviceManager: Timeout ejecutando 'adb devices'")
            return []
        except FileNotFoundError:
            logger.error("DeviceManager: ADB no encontrado en PATH")
            return []
        except Exception as e:
            logger.error(f"DeviceManager: Error listando dispositivos: {e}")
            return []
    
    @staticmethod
    def get_device_info(device_id: str) -> Optional[DeviceInfo]:
        """
        Obtiene información detallada de un dispositivo.
        
        Args:
            device_id: ID del dispositivo
            
        Returns:
            Información del dispositivo o None si no se encuentra
        """
        devices = DeviceManager.list_devices()
        for device in devices:
            if device.device_id == device_id:
                return device
        return None
