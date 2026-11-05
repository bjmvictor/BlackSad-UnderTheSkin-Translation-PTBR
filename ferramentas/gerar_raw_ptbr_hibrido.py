"""Gera Raw PT-BR híbrido: English normal e empréstimo pontual do slot Español."""
from __future__ import annotations

import argparse
import csv
import struct
from collections import defaultdict
from pathlib import Path

from gerar_raw_uabea_ptbr import get_script
from gerar_raw_ptbr_slot_fixo import HEADER, LANGUAGE_IDS, _entry


def tables(data: bytes | bytearray):
    """Lê as tabelas de oito idiomas, inclusive quando o English não é ASCII."""
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
            language_id, text_start, text_end = entry
            entries.append((cursor, language_id, text_start, text_end))
            cursor = text_end
        if len(entries) != len(LANGUAGE_IDS):
            continue
        try:
            source = bytes(data[entries[0][2] : entries[0][3]]).decode("utf-8")
        except UnicodeDecodeError:
            source = ""
        yield source, entries


def raw_script(blob: bytes) -> tuple[int, int, bytes]:
    name_length = struct.unpack_from("<I", blob, 0)[0]
    start = 4 + name_length
    start += (4 - start % 4) % 4
    length = struct.unpack_from("<I", blob, start)[0]
    script = blob[start + 4 : start + 4 + length]
    if len(script) != length:
        raise ValueError("TextAsset .dat inválido")
    return start, length, script


def mapping(catalog: Path) -> dict[str, str]:
    grouped: defaultdict[str, set[str]] = defaultdict(set)
    with catalog.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("pt_br"):
                grouped[row["en"]].add(row["pt_br"])
    return {source: next(iter(values)) for source, values in grouped.items() if len(values) == 1}


def fit(text: str, size: int) -> tuple[bytes, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= size:
        return encoded + b" " * (size - len(encoded)), True
    clipped = encoded[:size]
    while clipped:
        try:
            clipped.decode("utf-8")
            break
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return clipped + b" " * (size - len(clipped)), False


def generate(raw: Path, catalog: Path, arab_bundle: Path, target: Path, source_filter: set[str], override: str) -> None:
    blob = raw.read_bytes()
    start, old_length, original = raw_script(blob)
    base = bytearray(get_script(arab_bundle))
    original_tables = list(tables(original))
    base_tables = list(tables(base))
    if len(original_tables) != len(base_tables):
        raise ValueError("Estruturas original e referência não coincidem")

    translations = mapping(catalog)
    fixed = fallback = 0
    for (source, _), (_, base_entries) in zip(original_tables, base_tables):
        english_start, english_end = base_entries[0][2:]
        value = translations.get(source, source)
        written, ok = fit(value, english_end - english_start)
        base[english_start:english_end] = written
        if ok:
            fixed += translations.get(source, source) != source
        else:
            fallback += 1

    swapped = 0
    encoded_override = override.encode("utf-8")
    for (source, _), (_, base_entries) in zip(original_tables, base_tables):
        if source not in source_filter:
            continue
        english, spanish = base_entries[0], base_entries[1]
        spanish_capacity = spanish[3] - spanish[2]
        if len(encoded_override) > spanish_capacity:
            raise ValueError(f"'{source}' não cabe no slot Español ({len(encoded_override)} > {spanish_capacity} bytes)")
        base[spanish[2] : spanish[3]] = encoded_override + b" " * (spanish_capacity - len(encoded_override))
        struct.pack_into("<I", base, english[0], LANGUAGE_IDS[1])
        struct.pack_into("<I", base, spanish[0], LANGUAGE_IDS[0])
        swapped += 1
    if not swapped:
        raise ValueError("Nenhuma ocorrência do texto solicitado foi encontrada")

    padding = b"\0" * ((4 - len(base) % 4) % 4)
    target.write_bytes(blob[:start] + struct.pack("<I", len(base)) + base + padding + blob[start + 4 + old_length :])
    print(f"Hibrido gerado: {target}; PT-BR fixo em {fixed}; ingles preservado por limite em {fallback}; emprestimos Espanol->English em {swapped}; bytes {target.stat().st_size}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera Raw híbrido para teste via UABEA.")
    parser.add_argument("raw", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("arab_bundle", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--only-source", action="append", required=True)
    parser.add_argument("--text", required=True)
    args = parser.parse_args()
    generate(args.raw, args.catalog, args.arab_bundle, args.target, set(args.only_source), args.text)
