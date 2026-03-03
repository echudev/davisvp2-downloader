#!/usr/bin/env python3
"""
Script para descargar datos históricos de consolas Davis Vantage Pro/Pro2/Vue
Versión corregida - Soporta dump completo sin problemas de timing
"""

import serial
import struct
import time
from datetime import datetime
from typing import Optional, List
import pandas as pd


class VantageProtocol:
    CRC_TABLE = [ ... ]  # ← Mantén toda tu tabla CRC tal cual (no la copio aquí para ahorrar espacio)

    def __init__(self, port: str, baudrate: int = 19200):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=10.0          # ← Aumentado
        )
        time.sleep(0.5)

    def calculate_crc(self, data: bytes) -> int:
        crc = 0
        for byte in data:
            crc = self.CRC_TABLE[(crc >> 8) ^ byte] ^ (crc << 8)
            crc &= 0xFFFF
        return crc

    def wake_up(self) -> bool:
        for attempt in range(3):
            self.ser.write(b'\n')
            time.sleep(0.5)
            if self.ser.read(2) == b'\n\r':
                print("✓ Consola despierta")
                return True
        print("✗ Error: No se pudo despertar la consola")
        return False

    def send_command(self, command: str) -> bool:
        self.ser.write((command + '\n').encode())
        return self.ser.read(1) == b'\x06'

    def _download_page(self) -> Optional[bytes]:
        page = self.ser.read(267)
        received_len = len(page)
        
        if received_len != 267:
            print(f"✗ Página incompleta: {received_len} bytes (timeout)")
            if received_len > 0:
                print(f"   Primeros bytes: {page.hex()[:40]}...")
            return None

        # Verificar CRC
        data = page[:-2]
        crc_received = struct.unpack('>H', page[-2:])[0]
        crc_calculated = self.calculate_crc(data)

        if crc_received != crc_calculated:
            print("✗ CRC inválido")
            self.ser.write(b'\x21')
            return None

        self.ser.write(b'\x06')
        time.sleep(0.15)
        return page

    def download_full_dump(self) -> List[dict]:
        """Descarga completa usando comando DMP (más estable)"""
        if not self.wake_up():
            return []

        print("Descargando DUMP COMPLETO de todos los registros...")
        
        if not self.send_command("DMP"):           # ← Cambiamos a DMP
            print("✗ Error enviando comando DMP")
            return []

        # Leer header
        header = self.ser.read(6)
        if len(header) < 6:
            print("✗ Error leyendo header")
            return []

        num_pages = struct.unpack('<H', header[0:2])[0]
        first_record = struct.unpack('<H', header[2:4])[0]
        print(f"Páginas a descargar: {num_pages} | Primer registro: {first_record}")

        # ACK inicial + PAUSA CRÍTICA para que la consola prepare la primera página
        self.ser.write(b'\x06')
        print("✓ ACK inicial enviado - esperando primera página...")
        time.sleep(1.5)                    # ← Esto resuelve el problema
        self.ser.reset_input_buffer()

        records = []
        for page_num in range(num_pages):
            page_data = self._download_page()
            if page_data:
                page_records = self._parse_page(page_data, page_num, first_record)
                records.extend(page_records)
                print(f"Página {page_num + 1}/{num_pages} → {len(page_records)} registros")
            else:
                print(f"✗ Error en página {page_num + 1} → se detiene")
                break

        print(f"\n✓ Descarga completa: {len(records)} registros obtenidos")
        return records

    # Mantén tus métodos _parse_page y _parse_record exactamente como los tenías antes
    # (copia y pega desde tu versión anterior)

    def close(self):
        if self.ser.is_open:
            self.ser.close()


# === FUNCIONES aggregate_to_hourly y export_to_csv ===
# (cópialas exactamente igual que en tu script anterior)


def main():
    print("=" * 60)
    print("DESCARGA DE DATOS HISTÓRICOS - VANTAGE PRO/PRO2/VUE")
    print("=" * 60)

    port = input("\nIngrese el puerto serial (ej: /dev/ttyUSB0): ").strip()

    print("\n¿Descargar DUMP COMPLETO? [s/n]")
    choice = input().strip().lower()

    vantage = VantageProtocol(port)
    try:
        if choice in ['s', 'si', 'y', 'yes']:
            records = vantage.download_full_dump()
        else:
            # modo con fecha (tu código anterior)
            fecha_str = input("\nFecha/hora de inicio (YYYY-MM-DD HH:MM): ").strip()
            start_date = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            records = vantage.download_after_date(start_date)   # si aún lo tienes

        if records:
            print("\nCalculando promedios de 1 hora...")
            hourly_records = aggregate_to_hourly(records)
            filename = f"vantage_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            export_to_csv(hourly_records, filename)

            print("\n" + "=" * 60)
            print("RESUMEN")
            print("=" * 60)
            print(f"Registros originales: {len(records)}")
            print(f"Registros por hora:   {len(hourly_records)}")
    finally:
        vantage.close()


if __name__ == "__main__":
    main()