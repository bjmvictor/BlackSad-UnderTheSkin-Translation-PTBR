"""Gera um TextAsset PT-BR de tamanho fixo para um slot de idioma existente."""
from __future__ import annotations

import csv
import struct
import sys
from collections import defaultdict
from pathlib import Path

from gerar_raw_uabea_ptbr import get_script

LANGUAGES = ("en", "es", "zh", "fr", "de", "it", "nl", "ru")
LANGUAGE_IDS = (10, 34, 40, 14, 15, 21, 9, 30)
HEADER = struct.pack("<II", len(LANGUAGES), LANGUAGE_IDS[0])


def _entry(data: bytes | bytearray, offset: int) -> tuple[int, int, int] | None:
    if offset + 8 > len(data):
        return None
    language_id, length = struct.unpack_from("<II", data, offset)
    end = offset + 8 + length
    if length > 65536 or end > len(data):
        return None
    return language_id, offset + 8, end


def slot_records(data: bytes | bytearray, slot: str):
    """Retorna texto English e início/fim do slot solicitado em cada tabela."""
    if slot not in LANGUAGES:
        raise ValueError(f"Slot de idioma inválido: {slot}")
    slot_index = LANGUAGES.index(slot)
    at = 0
    while True:
        header = data.find(HEADER, at)
        if header < 0:
            return
        at = header + 1
        cursor = header + 4
        entries = []
        for expected_id in LANGUAGE_IDS:
            entry = _entry(data, cursor)
            if entry is None or entry[0] != expected_id:
                break
            entries.append(entry)
            cursor = entry[2]
        if len(entries) != len(LANGUAGES):
            continue
        en_start, en_end = entries[0][1:]
        try:
            source = bytes(data[en_start:en_end]).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not source or not source.isascii() or any(ord(char) < 32 or ord(char) > 126 for char in source):
            continue
        _, start, end = entries[slot_index]
        yield source, start, end


def slot_byte_limits(bundle: Path, slot: str) -> dict[str, int]:
    limits: dict[str, int] = {}
    for source, start, end in slot_records(get_script(bundle), slot):
        limits[source] = min(limits.get(source, end - start), end - start)
    return limits


def raw_script(blob: bytes) -> tuple[int, int, bytes]:
    name_length = struct.unpack_from("<I", blob, 0)[0]
    start = 4 + name_length
    start += (4 - start % 4) % 4
    length = struct.unpack_from("<I", blob, start)[0]
    script = blob[start + 4 : start + 4 + length]
    if len(script) != length:
        raise ValueError("TextAsset .dat inválido")
    return start, length, script


def translation_mapping(catalog: Path) -> dict[str, str]:
    grouped: defaultdict[str, set[str]] = defaultdict(set)
    with catalog.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("pt_br"):
                grouped[row["en"]].add(row["pt_br"])
    return {source: next(iter(values)) for source, values in grouped.items() if len(values) == 1}


def generate(raw_path: Path, catalog: Path, slot: str, target: Path) -> None:
    blob = raw_path.read_bytes()
    start, length, original_script = raw_script(blob)
    script = bytearray(original_script)
    mapping = translation_mapping(catalog)
    translated = fallback = 0
    for source, text_start, text_end in slot_records(script, slot):
        value = mapping.get(source, source)
        encoded = value.encode("utf-8")
        capacity = text_end - text_start
        if len(encoded) > capacity:
            fallback += 1
            continue
        script[text_start:text_end] = encoded + b" " * (capacity - len(encoded))
        translated += value != source
    target.write_bytes(blob[: start + 4] + script + blob[start + 4 + length :])
    print(f"Gerado: {target}; slot {slot}; PT-BR integral em {translated}; idioma original preservado por limite em {fallback}; bytes {target.stat().st_size}")


if __name__ == "__main__":
    generate(*(Path(value) if index != 2 else value for index, value in enumerate(sys.argv[1:])))
