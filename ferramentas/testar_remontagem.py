"""Valida que UnityPy remonta o bundle GameScript sem alterar seu TextAsset.

Uso: python ferramentas/testar_remontagem.py ENTRADA.saida SAIDA-teste
O resultado serve apenas para teste local; nao e distribuido nem copiado para a Steam.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import UnityPy


def raw_script(bundle: Path) -> bytes:
    environment = UnityPy.load(str(bundle))
    asset = next(
        obj.read()
        for obj in environment.objects
        if obj.type.name == "TextAsset" and obj.read().m_Name == "Script"
    )
    return asset.m_Script.encode("utf-8", "surrogateescape")


def main(source: Path, target: Path) -> None:
    expected = raw_script(source)
    environment = UnityPy.load(str(source))
    asset = next(
        obj.read()
        for obj in environment.objects
        if obj.type.name == "TextAsset" and obj.read().m_Name == "Script"
    )
    # Forca a serializacao do TextAsset sem editar o seu conteudo.
    asset.save()
    bundle = next(iter(environment.files.values()))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(bundle.save(packer="original"))

    actual = raw_script(target)
    if actual != expected:
        raise SystemExit("ERRO: a remontagem alterou os bytes do GameScript")
    print(f"OK: {len(actual)} bytes; SHA-256 {hashlib.sha256(actual).hexdigest()}")
    print(f"Bundle de teste: {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("uso: testar_remontagem.py ENTRADA SAIDA")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
