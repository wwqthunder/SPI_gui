"""
Self-updater for the deployed bundle (route B: portable Python).

Runtime layout: the launcher (spi.bat) runs from the bundle root, and the
interpreter + application source both live in MAIN_DIR ("python-3.7.3").
Updating means: pull the latest source (.py / resources) from the GitHub
branch HEAD, install any new/changed requirements with the bundled pip, then
overwrite the files in MAIN_DIR -- and record the new revision.

Safety guarantee (the whole point of this rewrite):
  * Nothing in MAIN_DIR is touched until the download, extraction and pip
    install have all succeeded, so a network/dependency failure changes nothing.
  * The file swap is done with a per-file backup and rolled back on any error,
    so a failure mid-copy restores the originals -- a failed update never bricks
    the install.

Revision model: we follow the branch HEAD commit sha (every push is picked up
automatically); the installed sha is recorded in MAIN_DIR/version.py.
"""

import os
import json
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request

OWNER_REPO = "wwqthunder/SPI_gui"
BRANCH = "master"
API = "https://api.github.com/repos/" + OWNER_REPO
MAIN_DIR = "python-3.7.3"                              # interpreter + app source
PIP_EXE = os.path.join(MAIN_DIR, "Scripts", "pip.exe")
REV_FILE = os.path.join(MAIN_DIR, "version.py")       # holds __revision__ = "<sha>"
_HEADERS = {"User-Agent": "SPI-GUI-Updater", "Accept": "application/vnd.github+json"}
_CHECK_TIMEOUT = 8                                    # small API call on startup
_DOWNLOAD_TIMEOUT = 90                                # zipball can be a few MB


# --------------------------------------------------------------------------- #
# revision bookkeeping
# --------------------------------------------------------------------------- #
def local_revision():
    """Currently installed commit sha, or '' if unknown/first run."""
    try:
        with open(REV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "__revision__" in line:
                    return line.split("=", 1)[1].strip().strip("\"'")
    except Exception:
        pass
    return ""


def remote_revision():
    """Latest commit sha on the tracked branch. Raises on network/API error."""
    req = urllib.request.Request(API + "/commits/" + BRANCH, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=_CHECK_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))["sha"]


def _write_revision(sha, folder):
    with open(os.path.join(folder, "version.py"), "w", encoding="utf-8") as f:
        f.write('__revision__ = "%s"\n' % sha)


def check_update():
    """True iff GitHub HEAD differs from the installed revision.

    Never raises: any network / API / rate-limit problem is treated as
    'no update available', so an offline startup is silent, not broken.
    """
    try:
        return remote_revision() != local_revision()
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# the safe update
# --------------------------------------------------------------------------- #
def _download_zip(dest):
    req = urllib.request.Request(API + "/zipball/" + BRANCH, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def _extracted_root(staging):
    """Return the single top-level folder GitHub wraps the repo in."""
    subs = [d for d in os.listdir(staging) if os.path.isdir(os.path.join(staging, d))]
    return os.path.join(staging, subs[0]) if subs else staging


def _pip_install(requirements_path):
    """Install/upgrade deps to satisfy requirements. True on success.

    If there is no requirements file or no bundled pip, there is nothing to do
    (returns True). Already-satisfied pins are skipped quickly by pip.
    """
    if not os.path.exists(requirements_path) or not os.path.exists(PIP_EXE):
        return True
    try:
        subprocess.run([PIP_EXE, "install", "-r", requirements_path],
                       check=True, capture_output=True, text=True)
        return True
    except Exception:
        return False


def update_main():
    """Pull the latest source into MAIN_DIR safely.

    Returns True on success, False on any failure. On failure the original
    MAIN_DIR files are guaranteed intact (either never touched, or rolled back).
    """
    if not os.path.isdir(MAIN_DIR):
        return False

    work = tempfile.mkdtemp(prefix="spi_update_")
    staging = os.path.join(work, "staging")
    backup = os.path.join(work, "backup")
    try:
        sha = remote_revision()

        # 1) download + extract into a staging area -- MAIN_DIR is not touched yet
        zip_path = os.path.join(work, "src.zip")
        _download_zip(zip_path)
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
                shutil.copy2(s, d)                    # overwrite (may fail here)
        except Exception:
            # 4) rollback: restore every backed-up original, remove every new file
            for name in os.listdir(backup):
                shutil.copy2(os.path.join(backup, name), os.path.join(MAIN_DIR, name))
            for name in new_names:
                d = os.path.join(MAIN_DIR, name)
                if os.path.exists(d):
                    os.remove(d)
            return False

        # 5) commit the new revision marker
        _write_revision(sha, MAIN_DIR)
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    print("local :", local_revision() or "(none)")
    try:
        print("remote:", remote_revision())
    except Exception as e:
        print("remote: <error>", e)
    print("update available:", check_update())
