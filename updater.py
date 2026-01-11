import os
import shutil
import json
import urllib.request
import importlib.util
import zipfile


GITHUB_API = "https://api.github.com/repos/wwqthunder/SPI_gui/releases/latest"
TEMP_DIR = "_update_temp"
MAIN_DIR = "python-3.7.3"
ZIP_PATH = "source.zip"


def get_latest_version():
    req = urllib.request.Request(
        GITHUB_API,
        headers={"User-Agent": "Python-Updater"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["tag_name"]


def parse_version(tag: str):
    return tuple(int(x) for x in tag.split("."))


def local_version():
    try:
        spec = importlib.util.spec_from_file_location("version", f"{MAIN_DIR}/version.py")
        version = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(version)
        return getattr(version, "__version__", "0.0")
    except Exception:
        with open("version.py", "w", encoding="utf-8") as f:
            f.write('__version__ = "0.0"\n')
        return "0.0"


def check_update():
    return parse_version(get_latest_version()) > parse_version(local_version())


def update_main():
    try:
        req = urllib.request.Request(
            GITHUB_API,
            headers={"User-Agent": "SPI-GUI-Updater"}
        )
        with urllib.request.urlopen(req) as resp:
            release = json.loads(resp.read().decode("utf-8"))

        zip_url = release.get("zipball_url")
        if not zip_url:
            raise RuntimeError("zipball_url not found")

        if not os.path.exists(MAIN_DIR):
            os.makedirs(MAIN_DIR)

        req = urllib.request.Request(
            zip_url,
            headers={"User-Agent": "SPI-GUI-Updater"}
        )
        with urllib.request.urlopen(req) as resp, open(ZIP_PATH, "wb") as f:
            f.write(resp.read())

        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            members = zip_ref.namelist()

            root_prefix = members[0].split("/")[0] + "/"

            for member in members:
                relative_path = member.replace(root_prefix, "", 1)
                if not relative_path:
                    continue

                target_path = os.path.join(MAIN_DIR, relative_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                with zip_ref.open(member) as src, open(target_path, "wb") as dst:
                    dst.write(src.read())

        os.remove(ZIP_PATH)
        write_version(release["tag_name"])
        return True
    except Exception as e:
        return False


def write_version(new_version):
    with open(f"{MAIN_DIR}/version.py", "w", encoding="utf-8") as f:
        f.write(f'__version__ = "{new_version}"\n')


if __name__ == "__main__":
    print(update_main())
