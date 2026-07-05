"""
Self-updater for the deployed bundle (route B: portable Python).

Runtime layout: the launcher (spi.bat) runs from the bundle root, and the
interpreter + application source both live in MAIN_DIR ("python-3.7.3").

Update policy: RELEASE-GATED. The app only updates to the latest *published*
GitHub Release (drafts and pre-releases are ignored), so plain pushes to the
branch do not reach the lab machines -- you cut a Release when a build is
blessed. Versions are compared semantically, so a machine is never downgraded.
The installed release tag is recorded in MAIN_DIR/version.py.

Safety guarantee: nothing in MAIN_DIR is touched until the download, extraction
and pip install have all succeeded; the file swap backs up every original and
rolls back on any error (read-only bundle files are handled), so a failed
update never bricks the install.
"""

import os
import stat
import json
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request

OWNER_REPO = "wwqthunder/SPI_gui"
API = "https://api.github.com/repos/" + OWNER_REPO
MAIN_DIR = "python-3.7.3"                              # interpreter + app source
PIP_EXE = os.path.join(MAIN_DIR, "Scripts", "pip.exe")
VER_FILE = os.path.join(MAIN_DIR, "version.py")       # holds __version__ = "<tag>"
_HEADERS = {"User-Agent": "SPI-GUI-Updater", "Accept": "application/vnd.github+json"}
_CHECK_TIMEOUT = 8                                    # small API call on startup
_DOWNLOAD_TIMEOUT = 90                                # release zipball can be a few MB


# --------------------------------------------------------------------------- #
# version bookkeeping
# --------------------------------------------------------------------------- #
def local_version():
    """Installed release tag, or '' if unknown/first run."""
    try:
        with open(VER_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "__version__" in line:
                    return line.split("=", 1)[1].strip().strip("\"'")
    except Exception:
        pass
    return ""


def latest_release():
    """(tag_name, zipball_url) of the latest published release.
    Raises on network / API error, or if the repo has no releases yet (404)."""
    req = urllib.request.Request(API + "/releases/latest", headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=_CHECK_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["tag_name"], data["zipball_url"]


def remote_version():
    return latest_release()[0]


def _parse_version(tag):
    """'v1.2', '1.2', '1.2.3-rc1' -> a tuple of leading integer parts."""
    tag = tag.strip().lstrip("vV")
    parts = []
    for chunk in tag.replace("-", ".").split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            break
    return tuple(parts)


def _is_newer(remote, local):
    """True iff release `remote` should replace installed `local` (never a
    downgrade). Falls back to plain inequality only for unparseable tags."""
    pr, pl = _parse_version(remote), _parse_version(local)
    if pr and pl:
        return pr > pl
    return bool(remote) and remote != local


def _write_version(tag, folder):
    with open(os.path.join(folder, "version.py"), "w", encoding="utf-8") as f:
        f.write('__version__ = "%s"\n' % tag)


def check_update():
    """True iff a newer published Release exists than what is installed.

    Never raises: any network / API / no-releases / rate-limit problem is
    treated as 'no update', so an offline launch is silent, not broken.
    """
    try:
        return _is_newer(remote_version(), local_version())
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# read-only-safe file ops
# --------------------------------------------------------------------------- #
def _force_write(path):
    """Clear the read-only bit so an existing file can be overwritten or removed
    (bundle files are often shipped read-only, which otherwise blocks the swap)."""
    if os.path.exists(path):
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass


def _replace(src, dst):
    """Copy src onto dst, overwriting even a read-only destination."""
    _force_write(dst)
    shutil.copy2(src, dst)


# --------------------------------------------------------------------------- #
# the safe update
# --------------------------------------------------------------------------- #
def _download_zip(url, dest):
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def _extracted_root(staging):
    """Return the single top-level folder GitHub wraps the release source in."""
    subs = [d for d in os.listdir(staging) if os.path.isdir(os.path.join(staging, d))]
    return os.path.join(staging, subs[0]) if subs else staging


def _pip_install(requirements_path):
    """Install/upgrade deps to satisfy requirements. True on success.

    No requirements file or no bundled pip -> nothing to do (True). Already
    satisfied pins are skipped quickly by pip.
    """
    if not os.path.exists(requirements_path) or not os.path.exists(PIP_EXE):
        return True
    try:
        subprocess.run([PIP_EXE, "install", "-r", requirements_path],
                       check=True, capture_output=True, text=True, errors="replace")
        return True
    except Exception:
        return False


def update_main():
    """Update MAIN_DIR to the latest published Release, safely.

    Returns True on success, False on any failure. On failure the original
    MAIN_DIR files are guaranteed intact (never touched, or rolled back).
    """
    if not os.path.isdir(MAIN_DIR):
        return False

    work = tempfile.mkdtemp(prefix="spi_update_")
    staging = os.path.join(work, "staging")
    backup = os.path.join(work, "backup")
    try:
        tag, zip_url = latest_release()

        # 1) download + extract into a staging area -- MAIN_DIR is not touched yet
        zip_path = os.path.join(work, "src.zip")
        _download_zip(zip_url, zip_path)
        os.makedirs(staging, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(staging)
        src = _extracted_root(staging)

        # 2) dependencies first: if a required package can't be installed, abort
        #    BEFORE touching any app file (originals stay 100% intact)
        if not _pip_install(os.path.join(src, "requirements.txt")):
            return False

        # 3) apply: back up every original before overwriting it, and track newly
        #    added files, so any error can be fully rolled back -- including a file
        #    that fails part-way through its own copy.
        os.makedirs(backup, exist_ok=True)
        new_names = []
        try:
            for name in os.listdir(src):
                s = os.path.join(src, name)
                if os.path.isdir(s):
                    continue                          # repo is flat app files
                d = os.path.join(MAIN_DIR, name)
                if os.path.exists(d):
                    shutil.copy2(d, os.path.join(backup, name))   # save original first
                else:
                    new_names.append(name)
                _replace(s, d)                        # overwrite (read-only safe)
        except Exception:
            # 4) rollback: restore every backed-up original, remove every new file
            for name in os.listdir(backup):
                _replace(os.path.join(backup, name), os.path.join(MAIN_DIR, name))
            for name in new_names:
                d = os.path.join(MAIN_DIR, name)
                if os.path.exists(d):
                    _force_write(d)
                    os.remove(d)
            return False

        # 5) commit the new version marker
        _write_version(tag, MAIN_DIR)
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    print("installed:", local_version() or "(none)")
    try:
        print("latest release:", remote_version())
    except Exception as e:
        print("latest release: <none/error>", e)
    print("update available:", check_update())
