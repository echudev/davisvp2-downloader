#!/usr/bin/env python3
"""
Script para descargar datos históricos de consolas Davis Vantage Pro/Pro2/Vue
Basado en el protocolo de comunicación serial Rev 2.5
Permite dump completo o desde fecha específica.
"""

import serial
import struct
import time
from datetime import datetime
from typing import Optional, List
import pandas as pd


class VantageProtocol:
    """Implementación del protocolo de comunicación Davis Vantage"""
    
    # Tabla CRC según el protocolo (sin cambios)
    CRC_TABLE = [
        0x0, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
        0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
        0x1231, 0x210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
        0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
        0x2462, 0x3443, 0x420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
        0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
        0x3653, 0x2672, 0x1611, 0x630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
        0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
        0x48c4, 0x58e5, 0x6886, 0x78a7, 0x840, 0x1861, 0x2802, 0x3823,
        0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
        0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0xa50, 0x3a33, 0x2a12,
        0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
        0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0xc60, 0x1c41,
        0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
        0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0xe70,
        0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
        0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
        0x1080, 0xa1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
        0x2b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
        0x34e2, 0x24c3, 0x14a0, 0x481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
        0x26d3, 0x36f2, 0x691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
        0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x8e1, 0x3882, 0x28a3,
        0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
        0x4a75, 0x5a54, 0x6a37, 0x7a16, 0xaf1, 0x1ad0, 0x2ab3, 0x3a92,
        0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
        0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0xcc1,
        0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
        0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0xed1, 0x1ef0
    ]
    
    def __init__(self, port: str, baudrate: int = 19200):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=5.0  # Aumentado para evitar timeouts en páginas lentas
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
            response = self.ser.read(2)
            if response == b'\n\r':
                print("✓ Consola despierta")
                return True
        print("✗ Error: No se pudo despertar la consola")
        return False
    
    def send_command(self, command: str) -> Optional[bytes]:
        self.ser.write((command + '\n').encode())
        response = self.ser.read(1)
        if response == b'\x06':  # ACK
            return response
        return None
    
    def _download_page(self) -> Optional[bytes]:
        print("Esperando página de 267 bytes...")
        page = self.ser.read(267)
        received_len = len(page)
        print(f"Recibidos {received_len} bytes")
        
        if received_len != 267:
            print(f"Timeout o incompleto - bytes recibidos: {received_len}")
            if received_len > 0:
                print(f"Primeros bytes: {page.hex()[:50]}...")
            return None
        
        data = page[:-2]
        crc_received = struct.unpack('>H', page[-2:])[0]
        crc_calculated = self.calculate_crc(data)
        
        print(f"CRC recibido: 0x{crc_received:04X}, calculado: 0x{crc_calculated:04X}")
        
        if crc_received != crc_calculated:
            print("✗ CRC inválido → enviando NAK")
            self.ser.write(b'\x21')
            return None
        
        print("✓ CRC OK → enviando ACK")
        self.ser.write(b'\x06')
        time.sleep(0.2)  # Pequeño delay entre páginas
        return page
    
    def _parse_page(self, page: bytes, page_num: int, first_record: int) -> List[dict]:
        records = []
        seq_num = page[0]
        
        for i in range(5):
            offset = 1 + i * 52
            record_data = page[offset:offset + 52]
            
            if page_num == 0 and i < first_record:
                continue
            
            record = self._parse_record(record_data)
            if record is not None:
                records.append(record)
        
        return records
    
    def _parse_record(self, data: bytes) -> Optional[dict]:
        # (sin cambios, mantengo tu parser original)
        if len(data) != 52:
            return None
        
        try:
            date_stamp = struct.unpack('<H', data[0:2])[0]
            if date_stamp == 0xFFFF:
                return None
            
            day = date_stamp & 0x1F
            month = (date_stamp >> 5) & 0x0F
            year = ((date_stamp >> 9) & 0x7F) + 2000
            
            if month == 0 or month > 12 or day == 0 or day > 31:
                return None
            
            time_stamp = struct.unpack('<H', data[2:4])[0]
            hour = time_stamp // 100
            minute = time_stamp % 100
            
            if hour > 23 or minute > 59:
                return None
            
            timestamp = datetime(year, month, day, hour, minute)
            
            is_rev_a = (data[42] == 0xFF)
            
            out_temp_raw = struct.unpack('<h', data[4:6])[0]
            # ... (el resto de campos sin cambios)
            # Para no alargar, asumo que copias el resto de _parse_record tal cual lo tenías
            
            out_temp_c = round((out_temp_raw - 320) / 10.0 * 5 / 9, 2) if out_temp_raw != 32767 else None
            
            # ... construye el dict 'record' como antes ...
            
            # Retorno simplificado (completa con tus campos)
            return {
                'timestamp': timestamp,
                'out_temp': out_temp_c,
                # agrega los demás campos que tenías
            }
        except Exception:
            return None
    
    def download_after_date(self, start_date: datetime) -> List[dict]:
        return self._download_pages(start_date)
    
    def download_full_dump(self) -> List[dict]:
        # Fuerza dump completo enviando date/time = 0,0 (CRC=0)
        return self._download_pages(datetime(2000, 1, 1), full_dump=True)
    
    def _download_pages(self, start_date: datetime, full_dump: bool = False) -> List[dict]:
        if not self.wake_up():
            return []
        
        if full_dump:
            date_stamp = 0
            time_stamp = 0
            print("Descargando DUMP COMPLETO de todos los registros archivados")
        else:
            day = start_date.day
            month = start_date.month
            year = start_date.year - 2000
            date_stamp = day + month * 32 + year * 512
            time_stamp = start_date.hour * 100 + start_date.minute
            print(f"Descargando datos desde: {start_date.strftime('%Y-%m-%d %H:%M')}")
        
        if not self.send_command("DMPAFT"):
            print("✗ Error enviando DMPAFT")
            return []
        
        data = struct.pack('<HH', date_stamp, time_stamp)
        crc = self.calculate_crc(data)
        crc_bytes = struct.pack('>H', crc)
        
        self.ser.write(data + crc_bytes)
        
        ack = self.ser.read(1)
        if ack != b'\x06':
            print("✗ Error: CRC inválido o problema con la fecha")
            return []
        
        header = self.ser.read(6)
        if len(header) < 6:
            print("✗ Error leyendo header")
            return []
        
        num_pages = struct.unpack('<H', header[0:2])[0]
        first_record = struct.unpack('<H', header[2:4])[0]
        
        print(f"Páginas a descargar: {num_pages}, Primer registro en página 0: {first_record}")
        
        self.ser.write(b'\x06')  # ACK inicial para empezar
        
        records = []
        for page_num in range(num_pages):
            page_data = self._download_page()
            if page_data:
                page_records = self._parse_page(page_data, page_num, first_record)
                records.extend(page_records)
                print(f"Página {page_num + 1}/{num_pages} descargada ({len(page_records)} registros)")
            else:
                print(f"✗ Error descargando página {page_num + 1}")
                break
        
        print(f"\n✓ Descarga completa: {len(records)} registros obtenidos")
        return records
    
    def close(self):
        if self.ser.is_open:
            self.ser.close()


# aggregate_to_hourly y export_to_csv sin cambios (cópialos tal cual)


def main():
    print("=" * 60)
    print("DESCARGA DE DATOS HISTÓRICOS - VANTAGE PRO/PRO2/VUE")
    print("=" * 60)
    
    port = input("\nIngrese el puerto serial (ej: /dev/ttyUSB0): ").strip()
    
    full_dump_choice = input("\n¿Descargar DUMP COMPLETO (todos los datos archivados)? [s/n]: ").strip().lower()
    
    vantage = None
    try:
        vantage = VantageProtocol(port)
        
        if full_dump_choice in ['s', 'si', 'y', 'yes']:
            records = vantage.download_full_dump()
        else:
            print("\nIngrese la fecha/hora de inicio:")
            fecha_str = input("Formato: YYYY-MM-DD HH:MM (ej: 2024-01-01 00:00): ").strip()
            try:
                start_date = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
                records = vantage.download_after_date(start_date)
            except ValueError:
                print("✗ Formato de fecha inválido")
                return
        
        if records:
            print("\nCalculando promedios de 1 hora...")
            hourly_records = aggregate_to_hourly(records)
            
            filename = f"vantage_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            export_to_csv(hourly_records, filename)
            
            print("\n" + "=" * 60)
            print("RESUMEN DE DATOS DESCARGADOS")
            print("=" * 60)
            print(f"Registros originales (30 min): {len(records)}")
            print(f"Registros agregados (1 hora): {len(hourly_records)}")
            if hourly_records:
                print(f"Primer registro: {hourly_records[0]['timestamp']}")
                print(f"Último registro: {hourly_records[-1]['timestamp']}")
        
    except serial.SerialException as e:
        print(f"✗ Error de conexión serial: {e}")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
    finally:
        if vantage:
            vantage.close()


if __name__ == "__main__":
    main()