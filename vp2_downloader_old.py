#!/usr/bin/env python3
"""
Script para descargar datos históricos de consolas Davis Vantage Pro/Pro2/Vue
Basado en el protocolo de comunicación serial Rev 2.5
"""

import serial
import struct
import time
from datetime import datetime, timedelta
from typing import Optional, List
import csv
import pandas as pd


class VantageProtocol:
    """Implementación del protocolo de comunicación Davis Vantage"""

    # Tabla CRC según el protocolo
    CRC_TABLE = [
        0x0,
        0x1021,
        0x2042,
        0x3063,
        0x4084,
        0x50A5,
        0x60C6,
        0x70E7,
        0x8108,
        0x9129,
        0xA14A,
        0xB16B,
        0xC18C,
        0xD1AD,
        0xE1CE,
        0xF1EF,
        0x1231,
        0x210,
        0x3273,
        0x2252,
        0x52B5,
        0x4294,
        0x72F7,
        0x62D6,
        0x9339,
        0x8318,
        0xB37B,
        0xA35A,
        0xD3BD,
        0xC39C,
        0xF3FF,
        0xE3DE,
        0x2462,
        0x3443,
        0x420,
        0x1401,
        0x64E6,
        0x74C7,
        0x44A4,
        0x5485,
        0xA56A,
        0xB54B,
        0x8528,
        0x9509,
        0xE5EE,
        0xF5CF,
        0xC5AC,
        0xD58D,
        0x3653,
        0x2672,
        0x1611,
        0x630,
        0x76D7,
        0x66F6,
        0x5695,
        0x46B4,
        0xB75B,
        0xA77A,
        0x9719,
        0x8738,
        0xF7DF,
        0xE7FE,
        0xD79D,
        0xC7BC,
        0x48C4,
        0x58E5,
        0x6886,
        0x78A7,
        0x840,
        0x1861,
        0x2802,
        0x3823,
        0xC9CC,
        0xD9ED,
        0xE98E,
        0xF9AF,
        0x8948,
        0x9969,
        0xA90A,
        0xB92B,
        0x5AF5,
        0x4AD4,
        0x7AB7,
        0x6A96,
        0x1A71,
        0xA50,
        0x3A33,
        0x2A12,
        0xDBFD,
        0xCBDC,
        0xFBBF,
        0xEB9E,
        0x9B79,
        0x8B58,
        0xBB3B,
        0xAB1A,
        0x6CA6,
        0x7C87,
        0x4CE4,
        0x5CC5,
        0x2C22,
        0x3C03,
        0xC60,
        0x1C41,
        0xEDAE,
        0xFD8F,
        0xCDEC,
        0xDDCD,
        0xAD2A,
        0xBD0B,
        0x8D68,
        0x9D49,
        0x7E97,
        0x6EB6,
        0x5ED5,
        0x4EF4,
        0x3E13,
        0x2E32,
        0x1E51,
        0xE70,
        0xFF9F,
        0xEFBE,
        0xDFDD,
        0xCFFC,
        0xBF1B,
        0xAF3A,
        0x9F59,
        0x8F78,
        0x9188,
        0x81A9,
        0xB1CA,
        0xA1EB,
        0xD10C,
        0xC12D,
        0xF14E,
        0xE16F,
        0x1080,
        0xA1,
        0x30C2,
        0x20E3,
        0x5004,
        0x4025,
        0x7046,
        0x6067,
        0x83B9,
        0x9398,
        0xA3FB,
        0xB3DA,
        0xC33D,
        0xD31C,
        0xE37F,
        0xF35E,
        0x2B1,
        0x1290,
        0x22F3,
        0x32D2,
        0x4235,
        0x5214,
        0x6277,
        0x7256,
        0xB5EA,
        0xA5CB,
        0x95A8,
        0x8589,
        0xF56E,
        0xE54F,
        0xD52C,
        0xC50D,
        0x34E2,
        0x24C3,
        0x14A0,
        0x481,
        0x7466,
        0x6447,
        0x5424,
        0x4405,
        0xA7DB,
        0xB7FA,
        0x8799,
        0x97B8,
        0xE75F,
        0xF77E,
        0xC71D,
        0xD73C,
        0x26D3,
        0x36F2,
        0x691,
        0x16B0,
        0x6657,
        0x7676,
        0x4615,
        0x5634,
        0xD94C,
        0xC96D,
        0xF90E,
        0xE92F,
        0x99C8,
        0x89E9,
        0xB98A,
        0xA9AB,
        0x5844,
        0x4865,
        0x7806,
        0x6827,
        0x18C0,
        0x8E1,
        0x3882,
        0x28A3,
        0xCB7D,
        0xDB5C,
        0xEB3F,
        0xFB1E,
        0x8BF9,
        0x9BD8,
        0xABBB,
        0xBB9A,
        0x4A75,
        0x5A54,
        0x6A37,
        0x7A16,
        0xAF1,
        0x1AD0,
        0x2AB3,
        0x3A92,
        0xFD2E,
        0xED0F,
        0xDD6C,
        0xCD4D,
        0xBDAA,
        0xAD8B,
        0x9DE8,
        0x8DC9,
        0x7C26,
        0x6C07,
        0x5C64,
        0x4C45,
        0x3CA2,
        0x2C83,
        0x1CE0,
        0xCC1,
        0xEF1F,
        0xFF3E,
        0xCF5D,
        0xDF7C,
        0xAF9B,
        0xBFBA,
        0x8FD9,
        0x9FF8,
        0x6E17,
        0x7E36,
        0x4E55,
        0x5E74,
        0x2E93,
        0x3EB2,
        0xED1,
        0x1EF0,
    ]

    def __init__(self, port: str, baudrate: int = 19200):
        """
        Inicializar conexión serial

        Args:
            port: Puerto serial (ej: 'COM3' en Windows, '/dev/ttyUSB0' en Linux)
            baudrate: Velocidad de comunicación (por defecto 19200)
        """
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=1.2,
        )
        time.sleep(0.5)

    def calculate_crc(self, data: bytes) -> int:
        """Calcular CRC según el protocolo Davis"""
        crc = 0
        for byte in data:
            crc = self.CRC_TABLE[(crc >> 8) ^ byte] ^ (crc << 8)
            crc &= 0xFFFF
        return crc

    def wake_up(self) -> bool:
        """Despertar la consola según el procedimiento del protocolo"""
        for attempt in range(3):
            self.ser.write(b"\n")
            time.sleep(0.5)
            response = self.ser.read(2)
            if response == b"\n\r":
                print("✓ Consola despierta")
                return True
        print("✗ Error: No se pudo despertar la consola")
        return False

    def send_command(self, command: str) -> Optional[bytes]:
        """Enviar comando y esperar ACK"""
        self.ser.write((command + "\n").encode())
        response = self.ser.read(1)
        if response == b"\x06":  # ACK
            return response
        return None

    def download_after_date(self, start_date: datetime) -> List[dict]:
        """
        Descargar datos después de una fecha específica usando DMPAFT

        Args:
            start_date: Fecha/hora de inicio

        Returns:
            Lista de registros meteorológicos
        """
        if not self.wake_up():
            return []

        # Calcular date_stamp y time_stamp según el protocolo
        day = start_date.day
        month = start_date.month
        year = start_date.year - 2000
        date_stamp = day + month * 32 + year * 512

        hour = start_date.hour
        minute = start_date.minute
        time_stamp = hour * 100 + minute

        print(f"Descargando datos desde: {start_date.strftime('%Y-%m-%d %H:%M')}")

        # Enviar comando DMPAFT
        if not self.send_command("DMPAFT"):
            print("✗ Error enviando comando DMPAFT")
            return []

        # Enviar date_stamp y time_stamp
        data = struct.pack("<HH", date_stamp, time_stamp)
        crc = self.calculate_crc(data)
        crc_bytes = struct.pack(">H", crc)  # MSB first para CRC

        self.ser.write(data + crc_bytes)

        # Leer respuesta
        ack = self.ser.read(1)
        if ack != b"\x06":
            print("✗ Error: CRC inválido o fecha no encontrada")
            return []

        # Leer número de páginas
        header = self.ser.read(6)
        if len(header) < 6:
            print("✗ Error leyendo header")
            return []

        num_pages = struct.unpack("<H", header[0:2])[0]
        first_record = struct.unpack("<H", header[2:4])[0]

        print(f"Páginas a descargar: {num_pages}, Primer registro: {first_record}")

        # Comenzar descarga
        self.ser.write(b"\x06")

        records = []
        for page_num in range(num_pages):
            page_data = self._download_page()
            if page_data:
                page_records = self._parse_page(page_data, page_num, first_record)
                records.extend(page_records)
                print(
                    f"Página {page_num + 1}/{num_pages} descargada ({len(page_records)} registros)"
                )
            else:
                print(f"✗ Error descargando página {page_num + 1}")
                break

        print(f"\n✓ Descarga completa: {len(records)} registros obtenidos")
        return records

    def _download_page(self) -> Optional[bytes]:
        """Descargar una página de 267 bytes"""
        page = self.ser.read(267)
        if len(page) != 267:
            return None

        # Verificar CRC
        data = page[:-2]
        crc_received = struct.unpack(">H", page[-2:])[0]
        crc_calculated = self.calculate_crc(data)

        if crc_received != crc_calculated:
            self.ser.write(b"\x21")  # NAK
            return None

        self.ser.write(b"\x06")  # ACK
        return page

    def _parse_page(self, page: bytes, page_num: int, first_record: int) -> List[dict]:
        """Parsear una página de 5 registros"""
        records = []
        seq_num = page[0]

        for i in range(5):
            offset = 1 + i * 52
            record_data = page[offset : offset + 52]

            # Solo procesar registros válidos
            if page_num == 0 and i < first_record:
                continue

            record = self._parse_record(record_data)
            if record is not None:
                records.append(record)

        return records

    def _parse_record(self, data: bytes) -> Optional[dict]:
        """Parsear un registro de archivo de 52 bytes (Rev A o Rev B)"""
        if len(data) != 52:
            return None

        try:
            # Date stamp (bits: year|month|day)
            date_stamp = struct.unpack("<H", data[0:2])[0]
            if date_stamp == 0xFFFF:
                return None

            day = date_stamp & 0x1F
            month = (date_stamp >> 5) & 0x0F
            year = ((date_stamp >> 9) & 0x7F) + 2000

            # Validar fecha
            if month == 0 or month > 12 or day == 0 or day > 31:
                return None

            # Time stamp (hour * 100 + minute)
            time_stamp = struct.unpack("<H", data[2:4])[0]
            hour = time_stamp // 100
            minute = time_stamp % 100

            # Validar hora
            if hour > 23 or minute > 59:
                return None

            timestamp = datetime(year, month, day, hour, minute)

            # Detectar formato: byte 42 identifica Rev A (0xFF) vs Rev B (0x00)
            # Ambos formatos comparten campos 0-29, divergen a partir de byte 30
            is_rev_a = data[42] == 0xFF

            # Campos comunes (offsets 0-29) para Rev A y Rev B
            out_temp_raw = struct.unpack("<h", data[4:6])[0]  # °F/10, dash=32767
            high_temp_raw = struct.unpack("<h", data[6:8])[0]  # °F/10, dash=-32768
            low_temp_raw = struct.unpack("<h", data[8:10])[0]  # °F/10, dash=32767
            rain_clicks = struct.unpack("<H", data[10:12])[0]  # clicks, dash=0
            high_rain_rate_clicks = struct.unpack("<H", data[12:14])[
                0
            ]  # clicks/hr, dash=0
            barometer_raw = struct.unpack("<H", data[14:16])[0]  # inHg/1000, dash=0
            solar_rad_raw = struct.unpack("<H", data[16:18])[0]  # W/m², dash=32767
            num_wind_samples = struct.unpack("<H", data[18:20])[0]  # count, dash=0
            in_temp_raw = struct.unpack("<h", data[20:22])[0]  # °F/10, dash=32767
            in_humidity_raw = data[22]  # %, dash=255
            out_humidity_raw = data[23]  # %, dash=255
            avg_wind_speed_raw = data[24]  # mph, dash=255
            high_wind_speed_raw = data[25]  # mph, dash=0
            dir_high_wind_raw = data[26]  # code 0-15, dash=255
            prevailing_dir_raw = data[27]  # code 0-15, dash=255
            avg_uv_raw = data[28]  # UV/10, dash=255
            et_raw = data[29]  # in/1000, dash=0

            # Direction names
            dir_names = [
                "N",
                "NNE",
                "NE",
                "ENE",
                "E",
                "ESE",
                "SE",
                "SSE",
                "S",
                "SSW",
                "SW",
                "WSW",
                "W",
                "WNW",
                "NW",
                "NNW",
            ]

            def dir_text(code):
                if code == 255:
                    return "s/d"
                if 0 <= code <= 15:
                    return dir_names[code]
                return None

            # Temperature conversion helper (F to C)
            def f_to_c(temp_f):
                if temp_f is None:
                    return None
                return round((temp_f - 32) * 5 / 9, 2)

            # Build base record (common fields)
            out_temp_c = f_to_c(None if out_temp_raw == 32767 else out_temp_raw / 10.0)
            # high_temp_c = f_to_c(None if high_temp_raw == -32768 else high_temp_raw / 10.0)
            # low_temp_c = f_to_c(None if low_temp_raw == 32767 else low_temp_raw / 10.0)
            in_temp_c = f_to_c(None if in_temp_raw == 32767 else in_temp_raw / 10.0)

            record = {
                "timestamp": timestamp,
                "wind_dir": dir_text(prevailing_dir_raw),
                "wind_speed_kmh": None
                if avg_wind_speed_raw == 255
                else round(avg_wind_speed_raw * 1.60934, 2),
                "out_temp": out_temp_c,  # C
                "out_hum": None if out_humidity_raw == 255 else out_humidity_raw,  # %
                #'high_out_temp_C': high_temp_c,
                #'low_out_temp_C': low_temp_c,
                #'rain_clicks': rain_clicks,
                #'high_rain_rate_clicks_per_hr': None if high_rain_rate_clicks == 0 else high_rain_rate_clicks,
                #'high_rain_rate_mm_per_hr': None if high_rain_rate_clicks == 0 else round(high_rain_rate_clicks * 0.254, 4),
                "pres_hPa": None
                if barometer_raw == 0
                else round(
                    (barometer_raw / 1000.0) * 33.8639, 2
                ),  # Convert inHg to hPa
                "UV": None if avg_uv_raw == 255 else avg_uv_raw,
                #'barometer_inHg': None if barometer_raw == 0 else round(barometer_raw / 1000.0, 3),
                #'barometer_raw': barometer_raw,
                "rain": round(rain_clicks * 0.2, 4)
                if rain_clicks != 0
                else rain_clicks,  # 1 click = 0.2 mm
                "solar_rad": None if solar_rad_raw == 32767 else solar_rad_raw,  # W/m²
                #'num_wind_samples': num_wind_samples,
                "in_temp": in_temp_c,
                "in_hum": None if in_humidity_raw == 255 else in_humidity_raw,
                "rain_clicks": rain_clicks,
                #'high_wind_speed_kmh': None if high_wind_speed_raw == 0 else round(high_wind_speed_raw * 1.60934, 2),
                #'dir_high_wind': dir_text(dir_high_wind_raw),
                #'record_type': 'Rev A' if is_rev_a else 'Rev B',
            }
            return record

        except (ValueError, struct.error) as e:
            # Error parseando este registro, saltarlo
            return None

    def close(self):
        """Cerrar conexión serial"""
        if self.ser.is_open:
            self.ser.close()


def aggregate_to_hourly(records: List[dict]) -> List[dict]:
    """
    Agrupa registros de 30 minutos en promedios de 1 hora usando Pandas.

    Args:
        records: Lista de registros con timestamps cada 30 minutos

    Returns:
        Lista de registros promediados a 1 hora
    """
    if not records:
        return []

    # Convertir a DataFrame
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Campos numéricos a promediar
    numeric_fields = [
        "out_temp",
        "out_hum",
        "pres_hPa",
        "UV",
        "solar_rad",
        "in_temp",
        "in_hum",
        "wind_speed_kmh",
    ]

    # Campos acumulativos (sumar en lugar de promediar)
    accumulative_fields = ["rain", "rain_clicks"]

    # Campos de texto a mantener (tomar el primero de cada grupo)
    text_fields = ["wind_dir"]

    # Agrupar por hora truncando el timestamp
    df["hour"] = df["timestamp"].dt.floor("h")

    # Crear diccionarios de agregación
    agg_dict = {field: "mean" for field in numeric_fields}
    for field in accumulative_fields:
        agg_dict[field] = "sum"  # Sumar valores acumulativos
    for field in text_fields:
        agg_dict[field] = "first"  # Tomar el primer valor de cada grupo

    # Agrupar y agregar
    hourly_df = df.groupby("hour", as_index=False).agg(agg_dict)

    # Renombrar la columna 'hour' a 'timestamp'
    hourly_df.rename(columns={"hour": "timestamp"}, inplace=True)

    # Redondear campos numéricos a 2 decimales y convertir a float
    for field in numeric_fields + accumulative_fields:
        hourly_df[field] = pd.to_numeric(hourly_df[field], errors="coerce").round(2)

    # Convertir de vuelta a lista de diccionarios, manteniendo tipos numéricos
    records_list = hourly_df.to_dict("records")

    # Asegurar que los valores None se mantengan como None en lugar de NaN
    for record in records_list:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
            elif key in numeric_fields + accumulative_fields:
                record[key] = float(value) if value is not None else None

    return records_list


def export_to_csv(records: List[dict], filename: str):
    """Exportar registros a CSV con tipos numéricos preservados"""
    if not records:
        print("No hay datos para exportar")
        return

    # Convertir a DataFrame para escribir con tipos correctos
    df = pd.DataFrame(records)

    # Define fieldnames in a consistent order with metric units
    fieldnames = [
        "timestamp",
        "wind_dir",
        "wind_speed_kmh",
        "out_temp",
        "out_hum",
        "pres_hPa",
        "UV",
        "rain",
        "solar_rad",
        "in_temp",
        "in_hum",
        "rain_clicks",
    ]

    # Seleccionar solo las columnas que existen
    existing_columns = [col for col in fieldnames if col in df.columns]
    df_to_export = df[existing_columns]

    # Escribir a CSV preservando tipos numéricos
    df_to_export.to_csv(filename, index=False, float_format="%.2f")

    print(f"✓ Datos exportados a: {filename}")
    if records:
        print(f"  Ejemplo primer registro:")
        print(f"    Timestamp: {records[0]['timestamp']}")
        print(f"    Out Temp: {records[0].get('out_temp')}°C")
        print(f"    Barometer: {records[0].get('pres_hPa')} hPa")
        print(f"    Prevailing Wind Dir: {records[0].get('wind_dir')}")
        print(f"    Tipo: {records[0].get('record_type')}")


def main():
    """Función principal"""
    print("=" * 60)
    print("DESCARGA DE DATOS HISTÓRICOS - VANTAGE PRO/PRO2/VUE")
    print("=" * 60)

    # Configuración del puerto
    port = input("\nIngrese el puerto serial (ej: COM3, /dev/ttyUSB0): ").strip()

    # Solicitar fecha de inicio
    print("\nIngrese la fecha/hora de inicio:")
    fecha_str = input("Formato: YYYY-MM-DD HH:MM (ej: 2024-01-01 00:00): ").strip()

    try:
        start_date = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("✗ Formato de fecha inválido")
        return

    # Conectar y descargar
    try:
        vantage = VantageProtocol(port)
        records = vantage.download_after_date(start_date)

        if records:
            # Agregar promedios de 1 hora
            print("\nCalculando promedios de 1 hora...")
            hourly_records = aggregate_to_hourly(records)

            # Exportar a CSV
            filename = f"vantage_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            export_to_csv(hourly_records, filename)

            # Mostrar resumen
            print("\n" + "=" * 60)
            print("RESUMEN DE DATOS DESCARGADOS")
            print("=" * 60)
            print(f"Registros originales (30 min): {len(records)}")
            print(f"Registros agregados (1 hora): {len(hourly_records)}")
            print(f"Primer registro: {hourly_records[0]['timestamp']}")
            print(f"Último registro: {hourly_records[-1]['timestamp']}")

        vantage.close()

    except serial.SerialException as e:
        print(f"✗ Error de conexión serial: {e}")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")


if __name__ == "__main__":
    main()
