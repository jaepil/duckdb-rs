"""Check publishable fork identities, source preservation and registry archives."""

import argparse
import hashlib
import pathlib
import tarfile
import tomllib

root = pathlib.Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--packages", type=pathlib.Path)
args = parser.parse_args()


def document(path):
    with path.open("rb") as handle:
        return tomllib.load(handle)


workspace = document(root / "Cargo.toml")["workspace"]
version = workspace["package"]["version"]
assert version == "1.10505.1", version
assert workspace["package"]["rust-version"] == "1.90"
assert workspace["dependencies"]["libduckdb-sys"]["package"] == "uqa-libduckdb-sys"
assert workspace["dependencies"]["libduckdb-sys"]["version"] == f"={version}"
assert workspace["dependencies"]["duckdb-loadable-macros"] == {"version": "=1.10505.0"}
for directory, name in [("duckdb", "uqa-duckdb"), ("libduckdb-sys", "uqa-libduckdb-sys")]:
    source = root / "crates" / directory
    manifest = document(source / "Cargo.toml")
    assert manifest["package"]["name"] == name
    if directory == "libduckdb-sys":
        assert manifest["package"]["links"] == "duckdb"
        assert manifest["build-dependencies"]["zip"]["version"] == "9.0.3"
    if args.packages is None:
        continue
    path = args.packages / f"{name}-{version}.crate"
    prefix = f"{name}-{version}/"
    with tarfile.open(path) as archive:
        def contents(name):
            return archive.extractfile(prefix + name).read()

        for member in archive:
            assert member.name.startswith(prefix), member.name
            assert ".." not in pathlib.PurePosixPath(member.name).parts
        packaged = tomllib.loads(contents("Cargo.toml").decode())
        assert packaged["package"]["name"] == name
        assert packaged["package"]["version"] == version
        assert packaged["package"]["license"] == "MIT"
        assert contents("LICENSE") == (source / "LICENSE").read_bytes()
        for file in (source / "src").rglob("*.rs"):
            assert contents(file.relative_to(source).as_posix()) == file.read_bytes(), file
        if directory == "libduckdb-sys":
            for file in source.glob("*.rs"):
                assert contents(file.name) == file.read_bytes(), file
            assert contents("duckdb.tar.gz") == (source / "duckdb.tar.gz").read_bytes()
            assert packaged["package"]["links"] == "duckdb"
            assert packaged["build-dependencies"]["zip"]["version"] == "9.0.3"
        else:
            dependency = packaged["dependencies"]["libduckdb-sys"]
            assert dependency["package"] == "uqa-libduckdb-sys"
            assert dependency["version"] == f"={version}"
            assert "path" not in dependency and "git" not in dependency
    print(f"Verified {path.name}: {hashlib.sha256(path.read_bytes()).hexdigest()}")
print("Fork metadata and archive contents verified")
