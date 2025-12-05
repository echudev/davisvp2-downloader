# User's active file:

#!/usr/bin/env python3
"""
vp2_comm.py

Script interactivo para enviar comandos a la consola Davis VP2 por puerto serie,
leer la respuesta y mostrarla por terminal.

Requisitos:
	pip install pyserial

Uso:
	python vp2_comm.py --port COM3
	python vp2_comm.py           # lista puertos y pide elegir

El script por defecto añade un terminador '\n' a los comandos.
Usa --raw para enviar exactamente lo que el usuario escribe.
"""

from __future__ import annotations

import argparse
import sys
import time

try:
	import serial
	from serial.tools import list_ports
except Exception:
	print("Falta la librería 'pyserial'. Instálala con: python -m pip install pyserial")
	raise

DEFAULT_BAUD = 19200
DEFAULT_TIMEOUT = 1.2
DEFAULT_TERMINATOR = "\n"


def list_serial_ports() -> list[str]:
	return [p.device for p in list_ports.comports()]


def choose_port_interactively() -> str:
	ports = list_serial_ports()
	if not ports:
		print("No se encontraron puertos serie. Conecta la consola VP2 y vuelve a intentar.")
		sys.exit(1)
	print("Puertos serie encontrados:")
	for i, p in enumerate(ports, 1):
		print(f"  {i}) {p}")
	while True:
		choice = input(f"Elige puerto [1-{len(ports)}] (enter 1): ").strip()
		if choice == "":
			return ports[0]
		try:
			idx = int(choice)
			if 1 <= idx <= len(ports):
				return ports[idx - 1]
		except ValueError:
			pass
		print("Entrada inválida. Intenta de nuevo.")


def open_port(port: str, baud: int = DEFAULT_BAUD, timeout: float = DEFAULT_TIMEOUT) -> serial.Serial:
	return serial.Serial(port=port, baudrate=baud, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=timeout)


def wake_up_console(ser: serial.Serial, retries: int = 3, delay: float = 0.5) -> bool:
	"""Enviar un newline para 'despertar' la consola. Espera b"\n\r" como respuesta.
	Retorna True si detecta respuesta, False si no."""
	for attempt in range(retries):
		try:
			ser.reset_input_buffer()
			ser.reset_output_buffer()
		except Exception:
			pass
		ser.write(b"\n")
		ser.flush()
		time.sleep(delay)
		try:
			resp = ser.read(2)
		except Exception:
			resp = b""
		if resp and b"\n" in resp:
			return True
	return False


def send_command(ser: serial.Serial, cmd_bytes: bytes, timeout: float = DEFAULT_TIMEOUT) -> bytes:
	"""Envía bytes y lee la respuesta hasta timeout. Devuelve bytes recibidos (vacío si timeout)."""
	ser.reset_input_buffer()
	ser.reset_output_buffer()
	ser.write(cmd_bytes)
	ser.flush()

	response = bytearray()
	start = time.time()
	while True:
		# leer lo que esté disponible (o 1 byte si nada todavía)
		to_read = ser.in_waiting or 1
		chunk = ser.read(to_read)
		if chunk:
			response.extend(chunk)
			# si hay newline/carriage return, esperar un pelín por más datos
			if b"\n" in chunk or b"\r" in chunk:
				time.sleep(0.02)
				continue
		# timeout manual
		if time.time() - start > timeout:
			break
		# si no vino nada en este ciclo, salir (o seguir esperando hasta timeout)
		if not chunk:
			# pequeña espera para no busy-loop
			time.sleep(0.01)
			continue
	return bytes(response)


def pretty_print_response(resp: bytes, show_hex: bool = False) -> None:
	if not resp:
		print("Sin respuesta (timeout).")
		return
	if show_hex:
		hexrepr = " ".join(f"{b:02X}" for b in resp)
		print("Respuesta (hex):", hexrepr)
	try:
		decoded = resp.decode("ascii", errors="replace")
		print("Respuesta (ASCII):")
		print(decoded)
	except Exception:
		print("Respuesta (bytes):", resp)


def parse_hex_input(s: str) -> bytes:
	"""Parsea una cadena con bytes en hex, por ejemplo: '06 21' o '0x06,0x21' o '0621'."""
	s = s.replace(',', ' ').replace('\t', ' ').strip()
	parts = [p for p in s.split() if p]
	if not parts:
		return b""
	# Si solo hay una pieza y tiene longitud par > 1, interpretar como concatenado
	if len(parts) == 1 and all(c in '0123456789abcdefABCDEF' for c in parts[0]) and len(parts[0]) % 2 == 0:
		hexstr = parts[0]
		return bytes.fromhex(hexstr)
	out = bytearray()
	for p in parts:
		if p.startswith('0x') or p.startswith('0X'):
			p = p[2:]
		if len(p) == 0:
			continue
		# pad single nibble
		if len(p) == 1:
			p = '0' + p
		out.append(int(p, 16))
	return bytes(out)


def main() -> None:
	parser = argparse.ArgumentParser(description="Enviar comando a consola Davis VP2 y mostrar respuesta (interactivo).")
	parser.add_argument('--port', '-p', help='Puerto serie (ej. COM3). Si no se indica, lista y pide seleccionar.')
	parser.add_argument('--baud', '-b', type=int, default=DEFAULT_BAUD, help=f'Baudios (default: {DEFAULT_BAUD})')
	parser.add_argument('--timeout', '-t', type=float, default=DEFAULT_TIMEOUT, help=f'Timeout lectura en segundos (default: {DEFAULT_TIMEOUT})')
	parser.add_argument('--terminator', default=DEFAULT_TERMINATOR, help="Terminador agregado por defecto al comando (default: '\\n')")
	parser.add_argument('--hex', action='store_true', help='Interpretar la entrada del usuario como bytes hex y enviarlos crudos.')
	parser.add_argument('--raw', action='store_true', help='Enviar exactamente lo que el usuario escribe (sin añadir terminador).')
	parser.add_argument('--list-ports', action='store_true', help='Listar puertos serie y salir.')
	parser.add_argument('--no-wakeup', action='store_true', help='No ejecutar secuencia de wake-up antes de enviar.')
	parser.add_argument('--show-hex', action='store_true', help='Mostrar respuesta también en hex.')
	args = parser.parse_args()

	if args.list_ports:
		ports = list_serial_ports()
		if not ports:
			print('No se encontraron puertos serie.')
		else:
			print('Puertos serie:')
			for p in ports:
				print('  ', p)
		return

	port = args.port or choose_port_interactively()

	try:
		ser = open_port(port, baud=args.baud, timeout=args.timeout)
	except Exception as e:
		print(f"No se pudo abrir el puerto {port}: {e}")
		sys.exit(2)

	try:
		if not args.no_wakeup:
			woke = wake_up_console(ser)
			if not woke:
				print('Advertencia: no se detectó respuesta al wake-up (continuando de todos modos).')

		while True:
			try:
				user = input('Comando a enviar (enter para salir): ').strip()
			except (KeyboardInterrupt, EOFError):
				print('\nInterrumpido por usuario. Saliendo.')
				break
			if user == '':
				print('Salida por línea vacía.')
				break

			if args.hex:
				cmd_bytes = parse_hex_input(user)
			else:
				if args.raw:
					cmd_text = user
				else:
					cmd_text = user + args.terminator
				cmd_bytes = cmd_text.encode('ascii', errors='ignore')

			print(f"Enviando {len(cmd_bytes)} bytes to {port}...")
			try:
				resp = send_command(ser, cmd_bytes, timeout=args.timeout)
			except Exception as e:
				print('Error durante comunicación serie:', e)
				break

			pretty_print_response(resp, show_hex=args.show_hex)

	finally:
		try:
			ser.close()
		except Exception:
			pass


if __name__ == '__main__':
	main()

