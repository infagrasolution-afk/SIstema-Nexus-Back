"""
Planificador automático de respaldos de base de datos (hora Venezuela UTC-4).
Ejecuta 3 veces al día: 08:00 AM, 01:00 PM (13:00) y 07:00 PM (19:00),
suplantando siempre el respaldo anterior en backups/apex_backup_latest.json.gz.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from scripts.backup_db import backup_database

logger = logging.getLogger("apex.backup_scheduler")
VET_TZ = timezone(timedelta(hours=-4))
TARGET_HOURS = (8, 13, 19)  # 8:00 AM, 1:00 PM, 7:00 PM VET


async def _backup_loop():
    last_executed_slot = None
    while True:
        try:
            now_vet = datetime.now(VET_TZ)
            slot_key = now_vet.strftime("%Y-%m-%d-%H")
            if now_vet.hour in TARGET_HOURS and slot_key != last_executed_slot:
                logger.info(f"Iniciando respaldo automático programado ({now_vet.strftime('%Y-%m-%d %H:%M')} VET)...")
                path = await backup_database(overwrite_latest=True)
                last_executed_slot = slot_key
                logger.info(f"Respaldo automático completado y actualizado: {path}")
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Error en respaldo automático programado: {exc}")
        await asyncio.sleep(60)


def start_backup_scheduler() -> asyncio.Task:
    return asyncio.create_task(_backup_loop())

