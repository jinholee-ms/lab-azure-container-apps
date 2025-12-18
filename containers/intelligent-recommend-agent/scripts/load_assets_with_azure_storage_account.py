from pathlib import Path
import os
import typer
from dotenv import load_dotenv

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


load_dotenv()


app = typer.Typer(help="Azure Blob Storage CLI (upload / download)")


def get_blob_service_client() -> BlobServiceClient:
    return BlobServiceClient(account_url="stgcontainershared.blob.core.windows.net", credential=DefaultAzureCredential())


def ensure_blob_container_client(client: BlobServiceClient, container_name: str):
    container = client.get_container_client(container_name)
    try:
        container.create_container()
    except ResourceExistsError:
        pass
    return container


def normalize_blob_path(path: str) -> str:
    return path.strip().lstrip("/").replace("\\", "/")


def normalize_blob_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    prefix = normalize_blob_path(prefix)
    return prefix if prefix.endswith("/") else prefix + "/"


def iter_files(path: Path):
    if path.is_file():
        yield path
    else:
        for p in path.rglob("*"):
            if p.is_file():
                yield p


@app.command()
def upload(
    container_name: str = typer.Option(..., help="Container name"),
    source: Path = typer.Option(..., exists=True, help="Local file or folder path"),
    destination: str = typer.Option(None, help="Target blob path (folder)"),
    overwrite: bool = typer.Option(False, help="Overwrite existing blobs"),
):
    """
    Upload a local file or folder to Azure Blob Storage.
    """
    if destination:
        destination = normalize_blob_prefix(destination)
    else:
        destination = normalize_blob_prefix(source.name)

    service = get_blob_service_client()
    container_client = ensure_blob_container_client(service, container_name)

    destination = normalize_blob_prefix(destination)
    if source.is_file():
        blob_name = destination + source.name
        blob_client = container_client.get_blob_client(blob_name)
        with source.open("rb") as file:
            blob_client.upload_blob(file, overwrite=overwrite)
        typer.echo(f"✅ Uploaded file → {container_name}/{blob_name}")
        return

    count = 0
    for file_path in iter_files(source):
        blob_name = destination + file_path.relative_to(source).as_posix()
        blob_client = container_client.get_blob_client(blob_name)
        with file_path.open("rb") as file:
            blob_client.upload_blob(file, overwrite=overwrite)
        count += 1
        typer.echo(f"🚀 uploaded file: {file_path.relative_to(source).as_posix()} → {container_name}/{blob_name}")
    typer.echo(f"✅ Uploaded folder: {count} files into {container_name}")


@app.command()
def download(
    container_name: str = typer.Option(..., help="Container name"),
    source: str = typer.Option(..., help="Blob path (file) or prefix(folder)"),
    destination: Path = typer.Option(..., help="Local file or folder path"),
    overwrite: bool = typer.Option(False, help="Overwrite local files"),
):
    """
    Download a blob file or folder(prefix) from Azure Blob Storage.
    """
    service = get_blob_service_client()
    container_client = ensure_blob_container_client(service, container_name)

    blob = normalize_blob_path(source)

    def download_blob_object(blob_name: str, dst: Path):
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not overwrite:
            typer.echo(f"⏭ Skip (exists): {dst}")
            return
        dst.write_bytes(
            container_client.get_blob_client(blob_name).download_blob().readall()
        )
        typer.echo(f"⬇ Downloaded → {dst}")

    # Try exact blob first
    try:
        container_client.get_blob_client(blob).get_blob_properties()
        if destination.is_dir() or str(destination).endswith(("/", "\\")):
            download_blob_object(blob, destination / Path(blob).name)
        else:
            download_blob_object(blob, destination)
        return
    except Exception:
        pass

    # Prefix (folder) download
    prefix = blob if blob.endswith("/") else blob + "/"
    destination.mkdir(parents=True, exist_ok=True)

    count = 0
    for b in container_client.list_blobs(name_starts_with=prefix):
        if b.name.endswith("/"):
            continue
        rel = b.name[len(prefix):]
        download_blob_object(b.name, destination / rel)
        count += 1
        if count % 50 == 0:
            typer.echo(f"...downloaded {count} files")

    if count == 0:
        typer.echo(f"⚠ No blobs found for prefix: {container_name}/{prefix}")
    else:
        typer.echo(f"✅ Downloaded folder → {count} files into {destination}")


if __name__ == "__main__":
    app()