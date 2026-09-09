import argparse
import json
import os
import pathlib
import sys
import tomllib
from functools import lru_cache
from subprocess import run


@lru_cache(maxsize=1)
def get_package_info(config_path: str = "pyproject.toml") -> dict:
    """
    Read the package name and version from the [project] table of pyproject.toml.

    :param config_path: Path to the pyproject.toml file
    :return: Dict with keys: name, name_dash, version
    :raises RuntimeError: if the file, [project], or required fields are missing
    """
    if not os.path.isfile(config_path):
        raise RuntimeError(f"Cannot find {config_path}")
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    project = data.get("project", {})
    name = project.get("name")
    version = project.get("version")
    if not name or not version:
        raise RuntimeError(f"'name' and 'version' must be present in [project] of {config_path}")
    return {
        "name": name.replace("-", "_"),
        "name_dash": name.replace("_", "-"),
        "version": version,
    }


#
VERSION = get_package_info()["version"]

# Package-wide name with underscore (wheel filename)
PACKAGE_NAME = get_package_info()["name"]

# Name with dash (pip name, URL, S3 bucket)
PACKAGE_NAME_DASH = get_package_info()["name_dash"]

# Home dir
HOME = pathlib.Path.home()

PROJECT_DIR = os.path.abspath(str(os.path.join(os.path.dirname(os.path.realpath(__file__)))))

PYTHON = sys.executable

PIP = [sys.executable, "-m", "pip"]


def executable_exists(executable):
    """
    :param executable: Name of the executable
    :return: True if executable exists, False otherwise
    """
    try:
        run([executable, "--version"])
        return True
    except FileNotFoundError:
        return False


def sanity_check(args):
    """
    Check if all required executables and configs are available
    """
    if not os.path.isdir(os.path.join(PROJECT_DIR, "src", PACKAGE_NAME)):
        print(f"Cannot find src/{PACKAGE_NAME}")
        sys.exit(1)
    if args.create_release and not release_version_exists(VERSION):
        print(f"No release notes found for version {VERSION}")
        sys.exit(1)
    if args.upload_s3 and not executable_exists("aws"):
        print("awscli not installed")
        sys.exit(1)
    if args.create_release and not executable_exists("gh"):
        print("GitHub CLI not installed")
        sys.exit(1)
    if args.publish_pypi and not executable_exists("twine"):
        print("twine not installed")
        sys.exit(1)
    if args.publish_pypi and not os.path.isfile(os.path.join(HOME, ".pypirc")):
        print("No ~/.pypirc file found")
        sys.exit(1)


def wheel_path():
    """
    :return: Path to the wheel file
    """
    return os.path.join(PROJECT_DIR, "dist", f"{PACKAGE_NAME}-{VERSION}-py3-none-any.whl")


def uninstall_wheel():
    """
    pip.exe uninstall -y {PACKAGE_NAME_DASH}
    """
    run([*PIP, "uninstall", "-y", PACKAGE_NAME_DASH], check=True)


def build_wheel():
    """
    python.exe -m pip install --upgrade pip
    python.exe -m pip install --upgrade build
    python.exe -m build
    """
    run([PYTHON, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    run([PYTHON, "-m", "pip", "install", "--upgrade", "build"], check=True)
    run([PYTHON, "-m", "build"], check=True)


def install_wheel():
    """
    pip.exe install ./dist/{PACKAGE_NAME}-{VERSION}-py3-none-any.whl
    """
    run([*PIP, "install", wheel_path()], check=True)


def install_wheel_devmode():
    """
    pip.exe install -e ./dist/{PACKAGE_NAME}-{VERSION}-py3-none-any.whl
    """
    run([*PIP, "install", "-e", "."], check=True)


def cleanup_old_wheels():
    """
    Remove all previous {PACKAGE_NAME}-{VERSION}-py3-none-any.whl in dist
    """
    if os.path.isdir(os.path.join(PROJECT_DIR, "dist")):
        for file in os.listdir(os.path.join(PROJECT_DIR, "dist")):
            if file.startswith(f"{PACKAGE_NAME}-"):
                os.remove(os.path.join(PROJECT_DIR, "dist", file))


def upload_s3():
    """
    Upload the package to S3
    Example:
    aws s3 cp {PACKAGE_NAME}-{VERSION}-py3-none-any.whl s3://{PACKAGE_NAME_DASH}/packages/ --acl public-read
    """
    run(["aws", "s3", "cp", wheel_path(), f"s3://{PACKAGE_NAME_DASH}/packages/", "--acl", "public-read"], check=True)


def tag_release():
    """
    Tag the release on GitHub
    Example:
    git tag -a release.{VERSION} -m "Release {VERSION}"
    git push origin --tags master
    """
    run(["git", "tag", "-a", f"release.{VERSION}", "-m", f"Release {VERSION}"], check=True)
    run(["git", "push", "origin", "--tags", "master"], check=True)


def create_release(release_file):
    """
    Create a release on GitHub
    Example:
    gh release create release.{VERSION} dist/{PACKAGE_NAME}-2.9.34-py3-none-any.whl --title {VERSION} --notes-file RELEASE.md
    """
    run(
        [
            "gh",
            "release",
            "create",
            f"release.{VERSION}",
            wheel_path(),
            "--title",
            VERSION,
            "--notes-file",
            release_file,
        ],
        check=True,
    )


def release_version_exists(version):
    """
    Check if the version with respective release notes exists in RELEASE_NOTES.json
    :param version: Version to check in format 2.9.34
    :return: True if the version exists, False otherwise
    """
    with open(os.path.join(PROJECT_DIR, "RELEASE_NOTES.json")) as release_json:
        release_notes = json.load(release_json)
    return version in release_notes["releases"]


def tmp_release_notes():
    """
    Read the last release notes in JSON format from release_notes.json and create a temporary release notes file
    :return: Path to the temporary release notes file
    """
    # read release_notes.json as dict
    release_md = "RELEASE.md"
    with open("RELEASE_NOTES.json") as release_json:
        release_notes = json.load(release_json)

    if not release_version_exists(VERSION):
        print(f"No release notes found for version {VERSION}")
        sys.exit(1)

    last_release = release_notes["releases"][VERSION]["release_notes"]
    url_template = release_notes["release"]["download_link"]
    release_url = url_template.format(version=VERSION, package_name=PACKAGE_NAME, package_name_dash=PACKAGE_NAME_DASH)
    print(f"Last release notes: {last_release}")
    print(f"Download URL template: {url_template}")
    print(f"Download URL: {release_url}")

    # create a temporary release notes file
    with open(release_md, "w") as release_tmp:
        release_tmp.write("## Release notes\n")
        for note in last_release:
            release_tmp.write(f"* {note}\n")
        release_tmp.write("## Staging Area Download URL\n")
        release_tmp.write(f"[Wheel Package {VERSION} on AWS S3]({release_url})\n")
    return os.path.abspath(release_md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Command-line params")
    parser.add_argument(
        "--mode",
        help="What to do with the package",
        choices=["build", "install", "dev", "reinstall", "uninstall"],
        default="reinstall",
        required=False,
    )
    parser.add_argument("--upload-s3", help="Upload the package to S3", action="store_true", required=False)
    parser.add_argument("--create-release", help="Create a release on GitHub", action="store_true", required=False)
    parser.add_argument(
        "--publish-pypi", help="Publish the package to PyPI server", action="store_true", default=False, required=False
    )
    args = parser.parse_args()

    print(f"Package name: {PACKAGE_NAME}")
    print(f"Package name2: {PACKAGE_NAME_DASH}")
    print(f"Version: {VERSION}")
    sanity_check(args)

    if args.mode == "build":
        build_wheel()
    elif args.mode == "install":
        cleanup_old_wheels()
        build_wheel()
        install_wheel()
    elif args.mode == "dev":
        cleanup_old_wheels()
        build_wheel()
        install_wheel_devmode()
    elif args.mode == "reinstall":
        cleanup_old_wheels()
        uninstall_wheel()
        build_wheel()
        install_wheel()
    elif args.mode == "uninstall":
        uninstall_wheel()
    else:
        print("Unknown mode")

    if args.upload_s3 and args.mode != "uninstall":
        upload_s3()

    if args.create_release and args.mode != "uninstall":
        release_file = tmp_release_notes()
        tag_release()
        create_release(release_file=release_file)
        os.remove(release_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
