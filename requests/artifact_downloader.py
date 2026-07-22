import hashlib
import os
import sys
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ARTIFACT_URL = "https://example.com/api/artifacts/myapp.tar.gz"
OUTPUT_FILE = Path("downloads/myapp.tar.gz")

# Optional expected SHA-256 checksum.
EXPECTED_SHA256 = ""

API_TOKEN = os.getenv("ARTIFACT_API_TOKEN")

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 60
RETRY_COUNT = 3
CHUNK_SIZE = 1024 * 1024  # 1 MB


def create_session():
    retry_policy = Retry(
        total=RETRY_COUNT,
        connect=RETRY_COUNT,
        read=RETRY_COUNT,
        status=RETRY_COUNT,
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(
        max_retries=retry_policy
    )

    session = requests.Session()

    session.headers.update(
        {
            "Accept": "application/octet-stream",
            "User-Agent": "artifact-downloader/1.0",
        }
    )

    if API_TOKEN:
        session.headers.update(
            {
                "Authorization": f"Bearer {API_TOKEN}"
            }
        )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def format_size(size_bytes):
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.2f} MB"


def download_artifact(session):
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = OUTPUT_FILE.with_suffix(
        OUTPUT_FILE.suffix + ".part"
    )

    sha256 = hashlib.sha256()
    downloaded_bytes = 0

    with session.get(
        ARTIFACT_URL,
        stream=True,
        timeout=(
            CONNECT_TIMEOUT,
            READ_TIMEOUT,
        ),
        verify=True,
    ) as response:
        response.raise_for_status()

        total_size = int(
            response.headers.get(
                "Content-Length",
                0,
            )
        )

        print(f"Downloading: {ARTIFACT_URL}")

        if total_size:
            print(
                f"Expected size: "
                f"{format_size(total_size)}"
            )

        with temporary_file.open("wb") as file:
            for chunk in response.iter_content(
                chunk_size=CHUNK_SIZE
            ):
                if not chunk:
                    continue

                file.write(chunk)
                sha256.update(chunk)

                downloaded_bytes += len(chunk)

                if total_size:
                    progress = (
                        downloaded_bytes
                        / total_size
                    ) * 100

                    print(
                        f"\rProgress: {progress:.1f}% "
                        f"({format_size(downloaded_bytes)})",
                        end="",
                        flush=True,
                    )

    print()

    actual_checksum = sha256.hexdigest()

    return (
        temporary_file,
        downloaded_bytes,
        actual_checksum,
    )


def verify_checksum(actual_checksum):
    if not EXPECTED_SHA256:
        print(
            "Checksum verification skipped because "
            "EXPECTED_SHA256 is empty."
        )

        return True

    print(f"Expected SHA-256: {EXPECTED_SHA256}")
    print(f"Actual SHA-256:   {actual_checksum}")

    return (
        actual_checksum.lower()
        == EXPECTED_SHA256.lower()
    )


def finalize_download(
    temporary_file,
    downloaded_bytes,
    actual_checksum,
):
    if downloaded_bytes == 0:
        print("FAILED: Downloaded file is empty.")
        temporary_file.unlink(missing_ok=True)
        return False

    if not verify_checksum(actual_checksum):
        print("FAILED: Checksum does not match.")
        temporary_file.unlink(missing_ok=True)
        return False

    temporary_file.replace(OUTPUT_FILE)

    print(f"Artifact saved: {OUTPUT_FILE}")
    print(
        f"Downloaded size: "
        f"{format_size(downloaded_bytes)}"
    )
    print(f"SHA-256: {actual_checksum}")

    return True


def main():
    print("ARTIFACT DOWNLOAD TOOL")

    try:
        with create_session() as session:
            (
                temporary_file,
                downloaded_bytes,
                actual_checksum,
            ) = download_artifact(session)

        download_successful = finalize_download(
            temporary_file,
            downloaded_bytes,
            actual_checksum,
        )

        if download_successful:
            print("Artifact download PASSED.")
            sys.exit(0)

        print("Artifact download FAILED.")
        sys.exit(1)

    except requests.Timeout:
        print("FAILED: Artifact download timed out.")

    except requests.ConnectionError as error:
        print(f"FAILED: Connection error: {error}")

    except requests.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else "Unknown"
        )

        print(
            f"FAILED: Server returned "
            f"HTTP {status_code}."
        )

    except requests.RequestException as error:
        print(f"FAILED: Request error: {error}")

    except OSError as error:
        print(f"FAILED: File-system error: {error}")

    sys.exit(1)


if __name__ == "__main__":
    main()