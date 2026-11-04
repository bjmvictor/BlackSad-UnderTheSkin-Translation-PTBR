"""Editor local e seguro do catalogo PT-BR.

Inicie com ``python ferramentas/catalogo_editor.py`` e abra o endereco exibido.
O servidor atende apenas em 127.0.0.1 e salva alteracoes no CSV de forma
atomica, criando um backup antes de cada gravacao.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from functools import lru_cache
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    import argostranslate.translate as argos_translate
except ImportError:
    argos_translate = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "texto" / "catalogo" / "pt-BR.csv"
BACKUP_DIR = ROOT / "texto" / "backups"
GAME_BACKUP_DIR = ROOT / "backups-jogo"
WEB_DIR = Path(__file__).with_name("catalogo_editor")
GAME_BUNDLE_RELATIVE = Path("Blacksad_Data/StreamingAssets/assets_data/2172dc1d-d264-45aa-a94c-231bf3de6baa")
ORIGINAL_BUNDLE = ROOT / "teste-uabea" / "2172dc1d-d264-45aa-a94c-231bf3de6baa"
PREVIEW_BUNDLE = ROOT / "saida-teste" / "ptbr-atual" / GAME_BUNDLE_RELATIVE
UABEA_PACKAGER = ROOT / "ferramentas" / "empacotar_ptbr_uabea.ps1"
ORIGINAL_BUNDLE_SHA256 = "1e0f95e46fcae4dc8b0cc1bfe7708559c5b9061a0b4350da95af654c9e917937"
MIN_VALID_GAME_BUNDLE_BYTES = 10_000_000
KNOWN_UNSAFE_BUNDLE_HASHES = {
    "0f80b8fea5be9842f9c84f1ad7633238fe0241f3af31b6b6679190c42c17c7de",
    "9fdc03f79281ec21c38b6756fa0cddec3015c0edafed903ff94e7a7584e6545",
}
INSTALL_STATE = GAME_BACKUP_DIR / "state.json"
LANGUAGES = {
    "en": "English",
    "pt_br": "Português (Brasil)",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "nl": "Nederlands",
    "ru": "Русский",
}
STATUSES = ("pending", "machine-draft", "draft", "review", "approved")
WRITE_LOCK = threading.RLock()
PROTECTED_TOKEN = re.compile(r"<[^>\n]+>|\$[A-Za-z_][A-Za-z0-9_]*")


@lru_cache(maxsize=2)
def translation_byte_limits(target_language: str = "en") -> dict[str, int]:
    """Limites UTF-8 seguros do slot que receberá o PT-BR."""
    try:
        if target_language == "es":
            from gerar_raw_ptbr_slot_fixo import slot_byte_limits
            return slot_byte_limits(ORIGINAL_BUNDLE, "es")
        if target_language != "en":
            return {}
        from gerar_raw_uabea_ptbr import get_script, records

        original = get_script(ORIGINAL_BUNDLE)
        reference = get_script(ROOT / "referencia" / GAME_BUNDLE_RELATIVE)
        source_records = list(records(original, False))
        reference_records = list(records(reference, False))
        if len(source_records) != len(reference_records):
            return {}
        limits: dict[str, int] = {}
        for source_record, reference_record in zip(source_records, reference_records):
            source = source_record[0]
            capacity = reference_record[2] - (reference_record[1] + 4)
            limits[source] = min(limits.get(source, capacity), capacity)
        return limits
    except Exception:
        return {}


def read_rows(catalog: Path) -> tuple[list[dict[str, str]], list[str]]:
    with catalog.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("O CSV nao possui cabecalho.")
        return list(reader), reader.fieldnames


def revision(row: dict[str, str]) -> str:
    value = "\x1f".join(row.get(key, "") for key in ("id", "pt_br", "status", "notes"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def group_revision(rows: list[dict[str, str]]) -> str:
    """Versao de concorrencia que protege todas as ocorrencias do texto."""
    value = "\x1e".join(revision(row) for row in sorted(rows, key=lambda item: item["id"]))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def grouped_rows(rows: list[dict[str, str]], target_language: str = "en") -> list[dict[str, object]]:
    """Agrupa as ocorrencias fisicas pelo texto ingles sem perder seus IDs."""
    limits = translation_byte_limits(target_language)
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["en"], []).append(row)

    result = []
    for source, members in groups.items():
        members.sort(key=lambda item: int(item.get("offset", "0")))
        variations = [
            language
            for language in LANGUAGES
            if len({member.get(language, "") for member in members}) > 1
        ]
        statuses = {member.get("status", "") for member in members}
        notes = {member.get("notes", "") for member in members}
        byte_limit = limits.get(source)
        pt_br_bytes = max((len(member.get("pt_br", "").encode("utf-8")) for member in members), default=0)
        result.append({
            "source": source,
            "ids": [member["id"] for member in members],
            "offsets": [member.get("offset", "") for member in members],
            "occurrences": len(members),
            "status": next(iter(statuses)) if len(statuses) == 1 else "mixed",
            "notes": next(iter(notes)) if len(notes) == 1 else "",
            "revision": group_revision(members),
            "variations": variations,
            "values": {language: members[0].get(language, "") for language in LANGUAGES},
            "byte_limit": byte_limit,
            "pt_br_bytes": pt_br_bytes,
            "over_limit": byte_limit is not None and pt_br_bytes > byte_limit,
            "searchable": "\n".join(value for member in members for value in member.values()).casefold(),
            "search_by_language": {
                language: "\n".join(member.get(language, "") for member in members).casefold()
                for language in LANGUAGES
            },
        })
    return result


def safe_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} deve ser texto.")
    if "\x00" in value:
        raise ValueError(f"{field} nao pode conter caractere nulo.")
    if len(value.encode("utf-8")) > 65536:
        raise ValueError(f"{field} excede o limite de 65.536 bytes do jogo.")
    return value


def translate_preserving_tokens(text: str, translate: object) -> str:
    """Mantem tags e variaveis intactas enquanto traduz o texto visivel."""
    protected: list[str] = []

    def replace_token(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"ZXQPTBRTOKEN{len(protected) - 1}QXZ"

    prepared = PROTECTED_TOKEN.sub(replace_token, text)
    translated = translate(prepared)
    if not isinstance(translated, str):
        raise RuntimeError("O tradutor local devolveu um resultado invalido.")
    for index, token in enumerate(protected):
        translated = translated.replace(f"ZXQPTBRTOKEN{index}QXZ", token)
    return translated


def get_argos_translation() -> object | None:
    """Retorna o modelo EN -> PT instalado localmente, se houver."""
    if argos_translate is None:
        return None
    try:
        languages = {language.code: language for language in argos_translate.get_installed_languages()}
        english = languages.get("en")
        portuguese = languages.get("pt")
        return english.get_translation(portuguese) if english and portuguese else None
    except Exception:
        return None


def local_translate(text: str) -> str:
    """Traduz EN -> PT com Argos Translate, sem chave nem chamada de API."""
    translation = get_argos_translation()
    if translation is None:
        raise RuntimeError(
            "Tradutor local indisponivel. Instale o pacote English -> Portuguese do Argos Translate e reinicie o editor."
        )
    return translate_preserving_tokens(text, translation.translate)


def write_rows(catalog: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = BACKUP_DIR / f"pt-BR.{stamp}.csv"
    shutil.copy2(catalog, backup)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".pt-BR.", suffix=".tmp", dir=str(catalog.parent), text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_name, catalog)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return str(backup.relative_to(ROOT)).replace("\\", "/")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_game_root(value: str) -> tuple[Path, Path]:
    root = Path(value.strip()).expanduser().resolve()
    if not root.is_dir() or not (root / "Blacksad.exe").is_file():
        raise ValueError("Escolha a pasta raiz que contém Blacksad.exe.")
    target = root / GAME_BUNDLE_RELATIVE
    if not target.is_file():
        raise ValueError("A instalação não contém o bundle de texto esperado para esta build.")
    return root, target


def steam_library_roots() -> list[Path]:
    candidates = [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            candidates.append(Path(winreg.QueryValueEx(key, "SteamPath")[0]))
    except (ImportError, OSError):
        pass

    libraries: list[Path] = []
    for steam in candidates:
        library_file = steam / "steamapps" / "libraryfolders.vdf"
        if steam.is_dir():
            libraries.append(steam)
        if library_file.is_file():
            for match in re.finditer(r'"path"\s+"([^"]+)"', library_file.read_text(encoding="utf-8", errors="ignore"), re.I):
                libraries.append(Path(match.group(1).replace("\\\\", "\\")))
    return list(dict.fromkeys(path.resolve() for path in libraries if path.is_dir()))


def detected_game_roots() -> list[Path]:
    found: list[Path] = []
    for library in steam_library_roots():
        manifest = library / "steamapps" / "appmanifest_1003890.acf"
        install_dir = None
        if manifest.is_file():
            match = re.search(r'"installdir"\s+"([^"]+)"', manifest.read_text(encoding="utf-8", errors="ignore"), re.I)
            install_dir = match.group(1) if match else None
        candidates = [library / "steamapps" / "common" / install_dir] if install_dir else []
        common = library / "steamapps" / "common"
        if common.is_dir():
            candidates.extend(path for path in common.iterdir() if path.is_dir())
        for candidate in candidates:
            try:
                root, _ = validate_game_root(str(candidate))
                found.append(root)
            except ValueError:
                continue
    return list(dict.fromkeys(found))


def game_is_running() -> bool:
    if os.name != "nt":
        return False
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Blacksad.exe"], capture_output=True, text=True, check=False)
    return "Blacksad.exe" in result.stdout


def atomic_copy(source: Path, target: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    os.close(descriptor)
    try:
        shutil.copy2(source, temporary_name)
        os.replace(temporary_name, target)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def read_install_state() -> dict[str, str]:
    try:
        value = json.loads(INSTALL_STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_install_state(state: dict[str, str]) -> None:
    GAME_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".state.", suffix=".tmp", dir=str(GAME_BACKUP_DIR), text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_name, INSTALL_STATE)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def state_key(root: Path) -> str:
    return str(root).casefold()


def create_game_backup(root: Path, target: Path, reason: str) -> dict[str, str]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    directory = GAME_BACKUP_DIR / stamp
    backup_file = directory / GAME_BUNDLE_RELATIVE
    backup_file.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(target, backup_file)
    metadata = {"id": stamp, "created_at": datetime.now().isoformat(timespec="seconds"), "game_root": str(root), "reason": reason, "sha256": file_hash(backup_file)}
    (directory / "backup.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def list_game_backups(root: Path | None = None) -> list[dict[str, str]]:
    if not GAME_BACKUP_DIR.is_dir():
        return []
    result = []
    for metadata_file in GAME_BACKUP_DIR.glob("*/backup.json"):
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            backup = metadata_file.parent / GAME_BUNDLE_RELATIVE
            if metadata.get("id") != metadata_file.parent.name or not backup.is_file() or backup.stat().st_size < MIN_VALID_GAME_BUNDLE_BYTES or not isinstance(metadata.get("sha256"), str) or metadata["sha256"].casefold() in KNOWN_UNSAFE_BUNDLE_HASHES:
                continue
            if root and Path(metadata.get("game_root", "")).resolve() != root:
                continue
            result.append(metadata)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return sorted(result, key=lambda item: item["id"], reverse=True)


def selected_backup(root: Path, backup_id: str) -> Path:
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[0-9]{6}", backup_id):
        raise ValueError("Backup inválido.")
    metadata_file = GAME_BACKUP_DIR / backup_id / "backup.json"
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Backup não encontrado.") from error
    backup = metadata_file.parent / GAME_BUNDLE_RELATIVE
    if Path(metadata.get("game_root", "")).resolve() != root or not backup.is_file() or backup.stat().st_size < MIN_VALID_GAME_BUNDLE_BYTES or metadata.get("sha256", "").casefold() in KNOWN_UNSAFE_BUNDLE_HASHES or metadata.get("sha256") != file_hash(backup):
        raise ValueError("O backup não corresponde a esta instalação ou está corrompido.")
    return backup


def build_current_preview(catalog: Path) -> Path:
    if not ORIGINAL_BUNDLE.is_file() or file_hash(ORIGINAL_BUNDLE) != ORIGINAL_BUNDLE_SHA256:
        raise RuntimeError("A cópia original validada do bundle não está disponível no projeto.")
    command = [sys.executable, str(ROOT / "ferramentas" / "gerar_bundle_ptbr.py"), str(ORIGINAL_BUNDLE), str(catalog), str(PREVIEW_BUNDLE), "--allow-partial", "--resolve-conflicts"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0 or not PREVIEW_BUNDLE.is_file():
        raise RuntimeError((result.stderr or result.stdout or "Não foi possível gerar o preview PT-BR.").strip())
    return PREVIEW_BUNDLE


def build_uabea_bundle(source_bundle: Path, catalog: Path, target_language: str) -> Path:
    """Gera o bundle fora da instalacao e devolve uma copia de verificacao."""
    if not UABEA_PACKAGER.is_file():
        raise RuntimeError("O empacotador UABEA não está disponível no projeto.")
    with tempfile.TemporaryDirectory(prefix="blacksad-uabea-") as temporary:
        output_dir = Path(temporary)
        command = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(UABEA_PACKAGER), "-BundleOrigem", str(source_bundle),
            "-Catalogo", str(catalog), "-PastaSaida", str(output_dir),
            "-IdiomaDestino", target_language,
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "O UABEA não conseguiu gerar o bundle PT-BR.").strip()
            raise RuntimeError(detail)
        match = re.search(r"^Bundle gerado:\s*(.+)$", result.stdout, re.MULTILINE)
        if not match:
            raise RuntimeError("O empacotador UABEA terminou sem informar o arquivo de saída.")
        generated = Path(match.group(1).strip())
        try:
            generated.relative_to(output_dir)
        except ValueError as error:
            raise RuntimeError("O empacotador UABEA informou uma saída fora da área temporária.") from error
        if not generated.is_file() or generated.stat().st_size < MIN_VALID_GAME_BUNDLE_BYTES:
            raise RuntimeError("O bundle gerado pelo UABEA está ausente ou tem tamanho inválido.")
        preview_dir = ROOT / "saida-teste" / "uabea-ultimo"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview = preview_dir / f"{source_bundle.name}.{target_language}"
        atomic_copy(generated, preview)
        return preview


def install_bundle(root_value: str, catalog: Path, action: str, backup_id: str = "", target_language: str = "en") -> dict[str, str]:
    root, target = validate_game_root(root_value)
    if game_is_running():
        raise RuntimeError("Feche Blacksad antes de alterar os arquivos do jogo.")
    state = read_install_state()
    current_hash = file_hash(target)
    if action == "apply":
        if target_language not in {"en", "es"}:
            raise ValueError("Slot de idioma inválido.")
        source = build_uabea_bundle(target, catalog, target_language)
        reason = f"aplicar_ptbr_uabea_{target_language}"
        label = "English" if target_language == "en" else "Español"
        message = f"PT-BR gerado pelo UABEA no slot {label} e aplicado ao jogo"
    elif action == "restore_original":
        if not ORIGINAL_BUNDLE.is_file() or file_hash(ORIGINAL_BUNDLE) != ORIGINAL_BUNDLE_SHA256:
            raise RuntimeError("A cópia original validada do bundle não está disponível no projeto.")
        source = ORIGINAL_BUNDLE
        reason = "restaurar_original"
        message = "Arquivo original da build restaurado"
    elif action == "restore_backup":
        source = selected_backup(root, backup_id)
        reason = "restaurar_backup"
        message = "Backup selecionado restaurado"
    else:
        raise ValueError("Ação de instalação inválida.")
    backup = create_game_backup(root, target, reason)
    atomic_copy(source, target)
    state[state_key(root)] = file_hash(target)
    write_install_state(state)
    return {"message": message, "backup": backup["id"], "target": str(target)}


def choose_game_folder(initial: str | None) -> str:
    try:
        import tkinter
        from tkinter import filedialog
        window = tkinter.Tk()
        window.withdraw()
        window.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="Selecione a pasta que contém Blacksad.exe", initialdir=initial or str(ROOT))
        window.destroy()
        return selected
    except Exception as error:
        raise RuntimeError("Não foi possível abrir o seletor de pastas. Informe o caminho manualmente.") from error


def game_config(selected_path: str | None = None) -> dict[str, object]:
    detected = [str(path) for path in detected_game_roots()]
    selected = selected_path or (detected[0] if detected else "")
    valid = False
    target_hash = ""
    if selected:
        try:
            root, target = validate_game_root(selected)
            selected = str(root)
            valid = True
            target_hash = file_hash(target)
        except ValueError:
            pass
    root = Path(selected).resolve() if valid else None
    return {"selected": selected, "detected": detected, "valid": valid, "target_hash": target_hash, "backups": list_game_backups(root), "can_build": ORIGINAL_BUNDLE.is_file(), "can_apply": UABEA_PACKAGER.is_file()}


class CatalogHandler(SimpleHTTPRequestHandler):
    catalog: Path
    game_path: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print(f"[editor] {self.address_string()} - {format % args}")

    def send_json(self, content: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(content, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def api_error(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.send_json({"error": message}, status)

    def do_GET(self) -> None:
        request = urlparse(self.path)
        if request.path == "/api/config":
            self.send_json({
                "languages": LANGUAGES,
                "statuses": STATUSES,
                "catalog": str(self.catalog.relative_to(ROOT)).replace("\\", "/"),
                "translator": {"provider": "Argos Translate (local)", "configured": get_argos_translation() is not None},
                "game": game_config(self.game_path),
            })
            return
        if request.path == "/api/game":
            self.send_json(game_config(self.game_path))
            return
        if request.path == "/api/messages":
            self.get_messages(parse_qs(request.query))
            return
        if request.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def get_messages(self, params: dict[str, list[str]]) -> None:
        query = params.get("query", [""])[0].strip().casefold()
        status = params.get("status", [""])[0]
        over_limit = params.get("over_limit", [""])[0] == "1"
        target_language = params.get("target_language", ["en"])[0]
        if target_language not in {"en", "es"}:
            target_language = "en"
        requested = [item for item in params.get("languages", ["en,pt_br,es"])[0].split(",") if item in LANGUAGES]
        languages = list(dict.fromkeys(requested)) or ["en", "pt_br", "es"]
        requested_search = [item for item in params.get("search_languages", [","])[0].split(",") if item in LANGUAGES]
        search_languages = list(dict.fromkeys(requested_search)) or list(LANGUAGES)
        try:
            page = max(1, int(params.get("page", ["1"])[0]))
            page_size = min(100, max(10, int(params.get("page_size", ["25"])[0])))
        except ValueError:
            self.api_error("Pagina ou tamanho de pagina invalido.")
            return

        with WRITE_LOCK:
            rows, _ = read_rows(self.catalog)
        matches = []
        for group in grouped_rows(rows, target_language):
            if status and status not in {
                row.get("status", "") for row in rows if row["en"] == group["source"]
            }:
                continue
            if over_limit and not group["over_limit"]:
                continue
            if query and not any(
                query in str(group["search_by_language"].get(language, ""))
                for language in search_languages
            ):
                continue
            matches.append(group)

        start = (page - 1) * page_size
        page_rows = matches[start : start + page_size]
        self.send_json({
            "total": len(matches),
            "page": page,
            "page_size": page_size,
            "languages": languages,
            "search_languages": search_languages,
            "target_language": target_language,
            "rows": [
                {key: value for key, value in row.items() if key not in {"searchable", "search_by_language"}}
                for row in page_rows
            ],
        })

    def do_POST(self) -> None:
        request_path = urlparse(self.path).path
        if request_path.startswith("/api/game/"):
            self.game_request(request_path)
            return
        if request_path == "/api/translate":
            self.translate_text()
            return
        if request_path != "/api/messages":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length > 100_000:
                raise ValueError("Requisicao muito grande.")
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            source = safe_text(payload.get("source"), "texto-fonte")
            expected_revision = safe_text(payload.get("revision"), "revision")
            pt_br = safe_text(payload.get("pt_br"), "Tradução PT-BR")
            status = safe_text(payload.get("status"), "status")
            notes = safe_text(payload.get("notes"), "notes")
            member_ids = payload.get("ids")
            if not isinstance(member_ids, list) or not member_ids:
                raise ValueError("A lista de ocorrencias e obrigatoria.")
            member_ids = [safe_text(value, "id da ocorrência") for value in member_ids]
            if status not in STATUSES:
                raise ValueError("Status invalido.")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self.api_error(str(error))
            return

        with WRITE_LOCK:
            rows, fieldnames = read_rows(self.catalog)
            members = [row for row in rows if row.get("en") == source]
            if not members:
                self.api_error("Mensagem nao encontrada.", HTTPStatus.NOT_FOUND)
                return
            if sorted(row["id"] for row in members) != sorted(member_ids):
                self.api_error(
                    "As ocorrencias deste texto mudaram. Recarregue a pagina antes de salvar.",
                    HTTPStatus.CONFLICT,
                )
                return
            if group_revision(members) != expected_revision:
                self.api_error(
                    "Uma das ocorrencias deste texto foi alterada desde que voce a abriu. Recarregue a pagina antes de salvar.",
                    HTTPStatus.CONFLICT,
                )
                return
            for row in members:
                row["pt_br"] = pt_br
                row["status"] = status
                row["notes"] = notes
            backup = write_rows(self.catalog, rows, fieldnames)

        self.send_json({
            "ok": True,
            "backup": backup,
            "revision": group_revision(members),
            "occurrences": len(members),
            "message": f"Alteração aplicada a {len(members)} ocorrência(s) no CSV com backup criado.",
        })

    def translate_text(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length > 100_000:
                raise ValueError("Requisição muito grande.")
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            text = safe_text(payload.get("text"), "Texto em inglês")
            if not text.strip():
                raise ValueError("Não há texto em inglês para traduzir.")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self.api_error(str(error))
            return
        try:
            translated = local_translate(text)
        except RuntimeError as error:
            self.api_error(str(error), HTTPStatus.SERVICE_UNAVAILABLE)
            return
        self.send_json({"translation": translated, "provider": "Argos Translate (local)"})

    def game_request(self, request_path: str) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length > 100_000:
                raise ValueError("Requisição muito grande.")
            payload = json.loads(self.rfile.read(content_length).decode("utf-8")) if content_length else {}
            if not isinstance(payload, dict):
                raise ValueError("Requisição inválida.")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self.api_error(str(error))
            return

        try:
            if request_path == "/api/game/detect":
                self.game_path = None
                self.send_json(game_config())
                return
            if request_path == "/api/game/path":
                root, _ = validate_game_root(safe_text(payload.get("path"), "pasta do jogo"))
                self.game_path = str(root)
                self.send_json(game_config(self.game_path))
                return
            if request_path == "/api/game/browse":
                selected = choose_game_folder(self.game_path)
                if not selected:
                    self.api_error("Nenhuma pasta foi selecionada.")
                    return
                root, _ = validate_game_root(selected)
                self.game_path = str(root)
                self.send_json(game_config(self.game_path))
                return
            if request_path == "/api/game/action":
                if payload.get("confirmed") is not True:
                    raise ValueError("Confirme a operação antes de alterar os arquivos do jogo.")
                action = safe_text(payload.get("action"), "ação")
                path = safe_text(payload.get("path") or self.game_path, "pasta do jogo")
                backup_id = safe_text(payload.get("backup_id", ""), "backup")
                target_language = safe_text(payload.get("target_language", "en"), "slot de idioma")
                result = install_bundle(path, self.catalog, action, backup_id, target_language)
                self.game_path = str(validate_game_root(path)[0])
                result["game"] = game_config(self.game_path)
                self.send_json(result)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            self.api_error(str(error), HTTPStatus.CONFLICT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Editor local do catalogo PT-BR")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG, help="CSV a editar")
    parser.add_argument("--port", type=int, default=8765, help="porta local (padrao: 8765)")
    args = parser.parse_args()
    catalog = args.catalog.resolve()
    if not catalog.is_file():
        raise SystemExit(f"CSV nao encontrado: {catalog}")
    if not (1 <= args.port <= 65535):
        raise SystemExit("A porta deve estar entre 1 e 65535.")

    CatalogHandler.catalog = catalog
    server = ThreadingHTTPServer(("127.0.0.1", args.port), CatalogHandler)
    print(f"Editor local: http://127.0.0.1:{args.port}")
    print(f"Catalogo: {catalog}")
    print("Use Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEditor encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
