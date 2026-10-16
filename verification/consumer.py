"""Create a fresh consumer that resolves only published registry dependencies."""

import pathlib
import shutil
import sys
import tomllib

root = pathlib.Path(__file__).resolve().parent.parent
with (root / "Cargo.toml").open("rb") as handle:
    version = tomllib.load(handle)["workspace"]["package"]["version"]
destination = pathlib.Path(sys.argv[1])
(destination / "src").mkdir(parents=True)
shutil.copyfile(root / "verification/src/main.rs", destination / "src/main.rs")
(destination / "Cargo.toml").write_text(
    '[package]\nname = "duckdb-registry-consumer"\nversion = "0.0.0"\n'
    'edition = "2024"\nrust-version = "1.90"\n[workspace]\n[dependencies]\n'
    f'duckdb = {{ package = "uqa-duckdb", version = "={version}" }}\n'
    'tempfile = "3.1"\n'
)
