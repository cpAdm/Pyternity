import json
import re
import shutil
import tarfile
from datetime import datetime
from typing import Any
from urllib import request

from pyternity.utils import *

# PyPI JSON API reference: https://warehouse.pypa.io/api-reference/json.html
# Ideally we should use the Simple API, but we would also like to get the upload time for each version,
# which is not yet supported (https://peps.python.org/pep-0700)

PYPI_ENDPOINT = "https://pypi.org/pypi"

MAJOR_VERSION = re.compile(r"\d+[.0]+")
MINOR_VERSION = re.compile(r"\d+\.\d+")  # Also includes MAJOR_VERSIONS


class Release:
    def __init__(self, version: str, files: list[dict[str, Any]]):
        tar_file = next(file for file in files if file['packagetype'] == "sdist")

        self.version = version
        self.filename: str = tar_file['filename']
        self.requires_python: str = tar_file['requires_python']
        self.upload_time = datetime.fromisoformat(tar_file['upload_time'])
        self.url: str = tar_file['url']

    def download_files(self, project_name: str):
        out_dir = EXAMPLES_DIR / project_name.lower() / self.version
        if out_dir.exists():
            if not CLEAN_DOWNLOADS:
                return out_dir

            shutil.rmtree(out_dir)

        tmp_file = TMP_DIR / self.filename
        request.urlretrieve(self.url, tmp_file)

        with tarfile.open(tmp_file, "r") as tar:
            # TODO optimize: We only have to keep python files
            tar.extractall(out_dir)

        tmp_file.unlink()

        return out_dir

    @property
    def is_major(self) -> bool:
        return bool(MAJOR_VERSION.fullmatch(self.version))

    @property
    def is_minor(self) -> bool:
        return bool(MINOR_VERSION.fullmatch(self.version))


class PyPIProject:
    def __init__(self, project_name: str):
        with request.urlopen(f"{PYPI_ENDPOINT}/{project_name}/json") as f:
            meta_data = json.loads(f.read())

            self.name = meta_data['info']['name']
            self.releases = []

            for version, files in meta_data['releases'].items():
                try:
                    self.releases.append(Release(version, files))
                except StopIteration:
                    # Not all releases have a tar file, skip those
                    continue
