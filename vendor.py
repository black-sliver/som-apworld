# pypi / wheels have python version, abi, and one or more "platform tags"
# each tag is a system, an optional version and an architecture
# the full filename is {name}-{version}-{pyver}-{'.'.join(tags)}.whl
# since we don't have "platform tags" in AP, we look for tags that we think will work and hope for the best
import hashlib

import requests
from pathlib import Path
from typing import Any, NamedTuple

import platformdirs

# noinspection DuplicatedCode
include_py = {
    "cp311": ["cp311"],
    "cp312": ["cp312"],
    "cp313": ["cp313"],
    "cp314": ["cp314"],  # ["cp314", "cp314t"] in the future
}
include_plat = {
    "darwin": ["macosx"],
    "linux-gnu": ["manylinux"],  # only versioned, don't care about older ones
    "win": ["win"],
}
include_arch = {
    "darwin": ["universal2"],
    "linux-gnu": ["x86_64", "aarch64"],
    "win": ["amd64", "arm64"],
}

requirements_name: str
requirements_hash: str
requirements_mods: tuple[str, ...]


assert include_plat.keys() == include_arch.keys()


class Download(NamedTuple):
    py: str
    abi: tuple[str, ...]
    os: str
    arch: str
    url: str
    digest: dict[str, str]


def is_safe_name(s: str) -> bool:
    return not any(c in s for c in "./\\:$\"'`%")


def want_platform(platform: str) -> bool:
    return any(
        any(platform.startswith(f"{plat}_") for plat in include_plat[os_])
        and any(platform.endswith(f"_{arch}") for arch in include_arch[os_])
        for os_ in include_plat
    )


def get_os_and_arch(platform: str) -> tuple[str, str] | None:
    for os_ in include_plat:
        if not any(platform.startswith(f"{plat}_") for plat in include_plat[os_]):
            continue
        for arch in include_arch[os_]:
            if platform.endswith(f"_{arch}"):
                return os_, arch
    return None


def is_file_identical(a: Path, b: Path, as_text: bool, missing_result: bool | None = None) -> bool:
    import filecmp

    if missing_result is not None and not a.exists() or not b.exists():
        return missing_result
    if filecmp.cmp(a, b):
        return True
    if as_text:
        pass
    with a.open("rb") as fa:
        with b.open("rb") as fb:
            if fa.read().replace(b"\r\n", b"\n") == fb.read().replace(b"\r\n", b"\n"):
                return True
    return False


def load_pypi_json(requirement_name: str) -> dict[str, Any]:
    import json
    from datetime import datetime, timedelta, timezone

    # sanity check
    if not is_safe_name(requirement_name):
        raise ValueError("Invalid requirement_name")

    cache_file = platformdirs.user_cache_path("Archipelago") / "downloads" / "pypi-json" / f"{requirement_name}.json"
    try:
        age = datetime.now(tz=timezone.utc) - datetime.fromtimestamp(cache_file.stat().st_mtime, tz=timezone.utc)
        if age < timedelta(seconds=-5):
            print("Cache mtime is in the future. Not trusting it.")
            raise ValueError("Cache invalid")
        if age < timedelta(hours=1):
            with open(cache_file, "r") as f:
                return json.load(f)
        raise ValueError("Cache outdated")
    except (FileNotFoundError, ValueError):
        res = requests.get(f"https://pypi.python.org/pypi/{requirement_name}/json").json()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(res, f)
        return res


def load_wheel(url: str, digest: dict[str, str]) -> bytes:
    from base64 import urlsafe_b64encode

    wheel_data: bytes

    if not digest or any(not k or not isinstance(k, str) for k in digest):
        raise TypeError("hashes argument must be in the form {algo: hex_digest} and can't be empty")
    if not url.startswith("https://"):
        raise ValueError("url must start with https://")

    def check_hash() -> None:
        for algo, val in digest.items():
            if hashlib.new(algo, wheel_data).hexdigest() != val:
                raise ValueError(f"{algo} hash mismatch for download {url}")

    url_hash = urlsafe_b64encode(hashlib.sha256(url.encode()).digest()).rstrip(b"=").decode()
    cache_file = platformdirs.user_cache_path("Archipelago") / "downloads" / f"{url_hash}.whl"
    try:
        with open(cache_file, "rb") as f:
            wheel_data = f.read()
        check_hash()
    except (FileNotFoundError, ValueError):
        wheel_data = requests.get(url).content
        check_hash()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "wb") as f:
            f.write(wheel_data)
    return wheel_data


# noinspection DuplicatedCode
def _install(root: str) -> None:
    import platform
    import sys
    import sysconfig

    import platformdirs

    py_impl = platform.python_implementation()
    if py_impl not in ("CPython",):
        raise ValueError(f'Unsupported python "{py_impl}" for installation of {requirements_name} packages')
    py_impl_short = {"CPython": "cp"}[py_impl]  # There is also "py" for pure Python, but we don't care for now
    py_ver = py_impl_short + sysconfig.get_config_var("py_version_nodot")
    nodot_plat = sysconfig.get_config_var("py_version_nodot_plat").split("-", 1)[0]
    py_abi_number = nodot_plat if nodot_plat else sysconfig.get_config_var("SOABI").split("-", 2)[1]
    py_abi = py_impl_short + py_abi_number
    py_arch = sysconfig.get_platform().split("-")[-1]  # macOS always gives "universal2", which is hopefully fine
    multiarch = sysconfig.get_config_var("MULTIARCH")  # darwin for macOS
    py_os = multiarch.replace(py_arch + "-", "") if multiarch else sysconfig.get_platform().split("-")[0]
    # alternatively try to extract from SOABI or guess from platform.libc_ver(); NOTE: we want linux-gnu vs. linux-musl

    if py_os not in include_plat or py_os not in include_arch or py_arch not in include_arch[py_os]:
        raise ValueError(f"Unsupported platform {py_os}-{py_arch} for installation of {requirements_name} packages")

    # detect if out assumption of extension naming is correct so we can filter what to extract
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    suffix_filter: str
    if py_os == "win" and ext_suffix == f".{py_abi}-win_{py_arch}.pyd":
        suffix_filter = "*.*-win_*.pyd"
    elif py_os == "darwin" and ext_suffix == f".{py_impl.lower()}-{py_abi_number}-darwin.so":
        suffix_filter = "*.*-*-darwin.so"
    elif py_os == "linux-gnu" and ext_suffix == f".{py_impl.lower()}-{py_abi_number}-{py_arch}-linux-gnu.so":
        suffix_filter = "*.*-*-*-linux-gnu.so"
    else:
        suffix_filter = ""

    # NOTE: we expect that files for different ABI have non-conflicting names on all supported platforms
    print(f"Installing vendored packages for {requirements_name} for {py_ver}-{py_abi} on {py_os}-{py_arch}")
    # TODO: logging?
    base_install_path = platformdirs.user_cache_path("Archipelago") / "vendored" / requirements_name / requirements_hash
    install_path = base_install_path / f"{py_os}-{py_arch}"
    identifier_path = base_install_path / f"{py_os}-{py_arch}-{py_ver}-{py_abi}.installed"
    if not install_path.is_dir() or not identifier_path.is_file():
        import importlib.resources
        from shutil import copyfileobj

        if not suffix_filter:
            print("Can not filter files by ext_suffix. May extract more than required!")  # TODO: logging?

        # noinspection DuplicatedCode
        def extract(res: "importlib.resources.abc.Traversable", dest_folder: Path) -> None:
            dest = dest_folder / res.name
            if res.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                for sub in res.iterdir():
                    extract(sub, dest)
            elif res.name.endswith(ext_suffix) or not suffix_filter or not dest.match(suffix_filter):
                assert res.is_file()
                with res.open("rb") as source_file:
                    with dest.open("wb") as dest_file:
                        copyfileobj(source_file, dest_file)

        files = importlib.resources.files(root)
        assert files.is_dir()
        for mod_name in requirements_mods:
            any_dir = files / mod_name / "any" / "any"
            mod_dir = files / mod_name / py_os / py_arch
            assert any_dir.is_dir()
            assert mod_dir.is_dir()
            for item in any_dir.iterdir():
                extract(item, install_path)
            for item in mod_dir.iterdir():
                extract(item, install_path)

        with open(identifier_path, "wb"):
            pass

    sys.path.insert(0, str(install_path))


def embed(requirements_file: str | Path = "requirements.txt") -> tuple[str, str, tuple[str, ...]]:
    import os
    import shutil
    from io import BytesIO
    from zipfile import ZipFile
    from base64 import urlsafe_b64encode
    from packaging.requirements import Requirement
    from packaging.utils import parse_wheel_filename

    def is_valid_version_name(s: str) -> bool:
        invalid_chars = "/\\:$\"'"
        return not any(c in s for c in invalid_chars)

    # sanity check inputs
    # output would be invalid if any of the lists were empty
    if not include_py or not all(v for v in include_py.values()):
        raise ValueError("Missing abi definition")
    if not include_plat or not all(v for v in include_plat.values()):
        raise ValueError("Missing platform definition")
    if not include_arch or not all(v for v in include_arch.values()):
        raise ValueError("Missing arch definition")
    if not all(is_safe_name(k) for k in include_py):
        raise ValueError("Invalid python version requested")
    if not all(is_safe_name(s) for v in include_py.values() for s in v):
        raise ValueError("Invalid python tag requested")
    if not all(is_safe_name(k) for k in include_plat) or not all(is_safe_name(k) for k in include_arch):
        raise ValueError("Invalid os identifier requested")
    if not all(is_safe_name(s) for v in include_plat.values() for s in v):
        raise ValueError("Invalid platform requested")
    if not all(is_safe_name(s) for v in include_arch.values() for s in v):
        raise ValueError("Invalid arch requested")

    # sadly, packaging.requirements can't parse a full requirements.txt file by itself
    with open(requirements_file) as f:
        data = f.read().replace("\\\n", " ")
    new_requirements_name = str(Path(os.path.abspath(requirements_file)).parent.name)
    new_requirements_hash = urlsafe_b64encode(hashlib.sha256(data.encode()).digest()).rstrip(b"=").decode()[:12]
    new_requirements_mods: list[str] = []
    # NOTE: we don't support #egg here for now
    lines = filter(None, (line.split("#", 1)[0].rstrip() for line in data.split("\n")))
    del data
    # delete old __init__.py if it exists
    vendored_folder = Path(requirements_file).parent / "vendored"
    init_file_path = vendored_folder / "__init__.py"
    if init_file_path.is_file():
        init_file_path.unlink()
    if init_file_path.exists():
        raise Exception(f"{init_file_path} exists but is not a file")
    # handle requirements
    for line in lines:
        parts = line.split("--hash=")
        requirement_str = parts[0].rstrip()
        hashes = set(map(str.rstrip, parts[1:]))
        hash_algos = set(s.split(":")[0] for s in hashes)
        requirement = Requirement(requirement_str)
        if requirement.url:
            raise NotImplementedError("URL in requirement not implemented")
        if requirement.marker:
            raise NotImplementedError("Marker in requirement not implemented")
        assert is_safe_name(requirement.name), "Unexpected characters in package name"  # parsing should have failed
        print(requirement)
        new_requirements_mods.append(requirement.name)
        package = load_pypi_json(requirement.name)
        assert isinstance(package, dict)
        releases = package["releases"]
        assert isinstance(releases, dict)
        for version in reversed(releases.keys()):  # from newest to oldest
            assert is_valid_version_name(version), "Unexpected version on pypi"  # the `in` below should also fail
            if version in requirement.specifier:
                yanked = False
                downloads: list[Download] = []
                assert isinstance(releases[version], list)
                for i, asset in enumerate(releases[version]):
                    if not asset["python_version"] in include_py:
                        continue  # this will also skip sdist
                    _, _, _, tags = parse_wheel_filename(asset["filename"])
                    if not any(
                        tag.interpreter in include_py
                        and tag.abi in include_py[tag.interpreter]
                        and want_platform(tag.platform)
                        for tag in tags
                    ):
                        continue
                    if hashes and not any(f"{algo}:{val}" in hashes for algo, val in asset["digests"].items()):
                        raise Exception(f"Would use {asset['filename']} of {version} but hash does not match")
                    os_, arch = next(filter(None, (get_os_and_arch(tag.platform) for tag in tags)))
                    yanked = yanked or bool(asset["yanked"])
                    if not str(asset["url"]).startswith("https://"):
                        raise Exception(f"Insecure or invalid download for {asset['filename']}")
                    downloads.append(
                        Download(
                            asset["python_version"],
                            tuple((tag.abi for tag in tags)),
                            os_,
                            arch,
                            asset["url"],
                            {
                                k: v
                                for k, v in asset["digests"].items()
                                if k in hash_algos or (not hash_algos and k == "sha256")
                            },
                        )
                    )
                if yanked:
                    if requirement.specifier == f"=={version}":
                        # if it's ==, we use the version even if it's yanked
                        print(f"Using yanked version {version}")
                    else:
                        # otherwise don't use a yanked version
                        print(f"Ignoring yanked version {version}")
                        continue
                provided_libs = set(
                    ((download.py, abi, download.os, download.arch) for download in downloads for abi in download.abi)
                )
                for py_ver in include_py:
                    for py_abi in include_py[py_ver]:
                        for os_ in include_plat:
                            for arch in include_arch[os_]:
                                if not (py_ver, py_abi, os_, arch) in provided_libs:
                                    raise KeyError(
                                        f"Did not find a download for {py_ver}-{py_abi}-{os_}-{arch} in {version}"
                                    )
                pkg_folder = vendored_folder / requirement.name
                skip_download = False  # for testing, assume files were already downloaded
                if not skip_download:
                    shutil.rmtree(pkg_folder, ignore_errors=True)
                for download in [] if skip_download else downloads:
                    print(f"  {download.url.replace('https://files.pythonhosted.org/', '', 1)}")
                    dest_folder = pkg_folder / download.os / download.arch
                    wheel_data = load_wheel(download.url, download.digest)
                    zf = ZipFile(BytesIO(wheel_data))
                    try:
                        os.makedirs(dest_folder, exist_ok=True)
                        ignore_ends = (".dist-info/RECORD", ".dist-info/WHEEL")
                        members = [zi for zi in zf.infolist() if not any(zi.filename.endswith(s) for s in ignore_ends)]
                        zf.extractall(dest_folder, members)
                        # TODO: check if files are identical when overwriting and warn otherwise
                    finally:
                        zf.close()
                    os.makedirs(dest_folder, exist_ok=True)
                # NOTE: we always create any/any to simplify installation
                # TODO: for pure python packages would could put them directly into vendored/{package.name}
                any_any_folder = pkg_folder / "any" / "any"
                os.makedirs(any_any_folder, exist_ok=True)
                # merge common parts that can go into any/any
                pairs = [(os_, arch) for os_, archs in include_arch.items() for arch in archs]
                if len(pairs) > 1:
                    one_folder = pkg_folder / pairs[0][0] / pairs[0][1]
                    for path in one_folder.rglob("*"):
                        if path.is_file():
                            rel = path.relative_to(one_folder)
                            for other in pairs[1:]:
                                other_path = pkg_folder / other[0] / other[1] / rel
                                probably_text = path.parent.name == "licenses" and path.parent.parent.name.endswith(
                                    ".dist-info"
                                )
                                if not is_file_identical(
                                    path,
                                    other_path,
                                    probably_text,
                                    missing_result=False,
                                ):
                                    break
                            else:
                                print(f"  Moving {rel} to any/any")
                                dest_path = any_any_folder / rel
                                dest_path.parent.mkdir(parents=True, exist_ok=True)
                                path.rename(dest_path)
                                for other in pairs[1:]:
                                    other_path = pkg_folder / other[0] / other[1] / rel
                                    other_path.unlink()
                # delete empty folders from os/arch folders
                for pair in pairs:
                    pair_folder = pkg_folder / pair[0] / pair[1]
                    for path in pair_folder.rglob("*"):
                        # for each folder, we check if it has any files (non-folders) and delete otherwise
                        if path.is_dir() and all(subpath.is_dir() for subpath in path.rglob("*")):
                            print(f"  Deleting empty {path}")
                            shutil.rmtree(path)
                break
        else:
            raise Exception(f"No candidate found for {requirement}")

    if not new_requirements_mods:
        raise Exception("No requirements specified")

    with init_file_path.open("w") as f:
        import inspect

        f.write("# This file is auto-generated! DO NOT MODIFY BY HAND!\n\n")
        # write imports
        f.write("from pathlib import Path\n\n")
        # write meta data
        f.write(f'requirements_name = "{new_requirements_name}"\n')
        f.write(f'requirements_hash = "{new_requirements_hash}"\n')
        f.write(f'requirements_mods = ("' + '", "'.join(new_requirements_mods))
        if len(new_requirements_mods) == 1:
            f.write('",)\n')
        else:
            f.write('")\n')
        f.write("# noinspection DuplicatedCode\n")
        f.write("include_py = {\n")
        f.write(",\n".join((f'    "{ver}": ["' + '", "'.join(abi) + '"]' for ver, abi in include_py.items())))
        f.write(",\n}\n")
        f.write("include_plat = {\n")
        f.write(",\n".join((f'    "{os_}": ["' + '", "'.join(plat) + '"]' for os_, plat in include_plat.items())))
        f.write(",\n}\n")
        f.write("include_arch = {\n")
        f.write(",\n".join((f'    "{os_}": ["' + '", "'.join(arch) + '"]' for os_, arch in include_arch.items())))
        f.write(",\n}\n")
        f.write("\n\n")
        # write _install implementation
        f.write("# noinspection DuplicatedCode\n")
        install_def = inspect.getsource(_install)
        assert install_def
        f.write(install_def)
        f.write("\n")
        # write install wrapper (the thing you call)
        f.write(
            """
def install() -> None:
    _install(__name__)
"""
        )

    return new_requirements_name, new_requirements_hash, tuple(new_requirements_mods)


if __name__ == "__main__":
    from sys import argv, stderr

    if len(argv) == 2:
        embed(argv[1])
    elif len(argv) == 1:
        embed()
    else:
        print(f"Usage: {argv[0]} [requirements_file]", file=stderr)
        exit(1)
