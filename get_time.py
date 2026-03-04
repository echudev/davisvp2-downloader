#!/usr/bin/env python3
"""
Script simple para leer la fecha/hora actual de una consola Davis Vantage Pro/Pro2/Vue
usando el comando GETTIME del protocolo serie.
"""

import configparser
import os
import serial
import time
from datetime import datetime

# ── Cargar configuración desde davis.conf ──
_cfg = configparser.ConfigParser()
_cfg.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "davis.conf"))

DEFAULT_PORT = _cfg.get("serial", "DEFAULT_PORT", fallback="/dev/ttyUSB0")
DEFAULT_BAUD = _cfg.getint("serial", "DEFAULT_BAUD", fallback=19200)
DEFAULT_TIMEOUT = _cfg.getfloat("serial", "DEFAULT_TIMEOUT", fallback=1.2)


def wake_up_console(ser: serial.Serial, retries: int = 3, delay: float = 0.5) -> bool:
    """Despertar la consola según el procedimiento del protocolo Davis."""
    for attempt in range(retries):
        ser.write(b"\n")
        time.sleep(delay)
        response = ser.read(2)
        if response == b"\n\r":
            print("✓ Consola despierta")
            return True
    print("✗ Error: No se pudo despertar la consola")
    return False


def get_vantage_time(
    port: str, baudrate: int = DEFAULT_BAUD, timeout: float = DEFAULT_TIMEOUT
):
    """Conectar al puerto serie, enviar GETTIME y mostrar la fecha/hora de la consola."""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=timeout,
        )
    except serial.SerialException as e:
        print(f"✗ Error abriendo puerto serial: {e}")
        return

    try:
        time.sleep(0.5)

        if not wake_up_console(ser):
            ser.close()
            return

        # Enviar comando GETTIME
        cmd = "GETTIME\n".encode("ascii")
        ser.write(cmd)

        # Leer ACK
        ack = ser.read(1)
        if ack != b"\x06":
            print("✗ No se recibió ACK después de GETTIME")
            ser.close()
            return

        # Leer 6 bytes: segundos, minutos, hora(24h), día, mes, año (desde 1900)
        data = ser.read(6)
        if len(data) != 6:
            print("✗ Respuesta incompleta de GETTIME (se esperaban 6 bytes)")
            ser.close()
            return

        sec, minute, hour, day, month, year_offset = data
        year = 1900 + year_offset

        try:
            dt = datetime(year, month, day, hour, minute, sec)
        except ValueError:
            print(
                f"✗ Fecha/hora inválida recibida: "
                f"{day:02d}/{month:02d}/{year} {hour:02d}:{minute:02d}:{sec:02d}"
            )
            ser.close()
            return

        print("✓ Fecha/hora actual de la consola Davis:")
        print(dt.strftime("%Y-%m-%d %H:%M:%S"))

    finally:
        if ser.is_open:
            ser.close()


def main():
    print("=" * 60)
    print("LECTURA DE HORA - DAVIS VANTAGE PRO/PRO2/VUE")
    print("=" * 60)

    port = input(f"\nIngrese el puerto serial [{DEFAULT_PORT}]: ").strip()
    if not port:
        port = DEFAULT_PORT

    get_vantage_time(port)


if __name__ == "__main__":
    main()
