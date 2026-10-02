"""Armazenamento dos arquivos.

- local: pasta no disco (dev e protótipo).
- drive: Google Drive via service account, pastas Cliente/Ano/Mês/Tipo.

O banco guarda `storage_backend` + `storage_ref` por documento, então os dois
podem coexistir (ex.: histórico local, novos no Drive).
"""
import io
import json
import os
import re
from dataclasses import dataclass
from app.config import settings


@dataclass
class Salvo:
    backend: str
    ref: str
    link: str | None = None


def _safe(nome: str) -> str:
    nome = re.sub(r"[^\w.\- ]", "_", nome, flags=re.UNICODE).strip()
    return nome[:120] or "arquivo"


# ---------- local ----------

def _local_save(caminho_rel: str, nome: str, data: bytes) -> Salvo:
    base = os.path.abspath(settings.local_storage_dir)
    pasta = os.path.join(base, caminho_rel)
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, nome)
    # evita sobrescrever reenvio com mesmo nome
    i = 1
    raiz, ext = os.path.splitext(destino)
    while os.path.exists(destino):
        destino = f"{raiz}_{i}{ext}"
        i += 1
    with open(destino, "wb") as f:
        f.write(data)
    return Salvo(backend="local", ref=os.path.relpath(destino, base))


def _local_read(ref: str) -> bytes:
    base = os.path.abspath(settings.local_storage_dir)
    with open(os.path.join(base, ref), "rb") as f:
        return f.read()


# ---------- drive ----------

_drive = None


def _drive_service():
    global _drive
    if _drive is None:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        info = json.loads(settings.google_service_account_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive"]
        )
        _drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _drive


def _drive_folder(parent_id: str, nome: str) -> str:
    svc = _drive_service()
    q = (
        f"name = '{nome.replace(chr(39), chr(92) + chr(39))}' and '{parent_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    res = svc.files().list(q=q, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": nome, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    created = svc.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return created["id"]


def _drive_save(caminho_rel: str, nome: str, data: bytes, mime: str) -> Salvo:
    from googleapiclient.http import MediaIoBaseUpload
    svc = _drive_service()
    parent = settings.drive_root_folder_id
    for parte in caminho_rel.split("/"):
        if parte:
            parent = _drive_folder(parent, parte)
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime, resumable=False)
    created = svc.files().create(
        body={"name": nome, "parents": [parent]},
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return Salvo(backend="drive", ref=created["id"], link=created.get("webViewLink"))


def _drive_read(file_id: str) -> bytes:
    svc = _drive_service()
    return svc.files().get_media(fileId=file_id, supportsAllDrives=True).execute()


# ---------- API pública ----------

def salvar(*, cliente_nome: str, competencia: str, tipo_rotulo: str, nome_arquivo: str, data: bytes, mime: str) -> Salvo:
    ano, mes = competencia.split("-")
    caminho = f"{_safe(cliente_nome)}/{ano}/{mes}/{_safe(tipo_rotulo)}"
    nome = _safe(nome_arquivo)
    if settings.storage_backend == "drive" and settings.google_service_account_json and settings.drive_root_folder_id:
        return _drive_save(caminho, nome, data, mime)
    return _local_save(caminho, nome, data)


def ler(backend: str, ref: str) -> bytes:
    if backend == "drive":
        return _drive_read(ref)
    return _local_read(ref)
