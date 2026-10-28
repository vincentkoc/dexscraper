# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Versions are derived from Git tags
via setuptools_scm; per-release notes are also on the
[GitHub releases page](https://github.com/vincentkoc/dexscraper/releases).

## [Unreleased]

### Added

- A `rich` extra (`pip install "dexscraper[rich]"`) for `--format rich`; the
  `dev` extra now lists `rich` directly instead of relying on it arriving
  through `twine`.

### Fixed

- `dexscraper --help` no longer exits with "incomplete format": the
  price-change help strings now escape `%`.
- Raised vulnerable dependency floors.
- Cleared ruff and mypy findings.

### Changed

- **Breaking:** Python 3.9 and 3.10 are no longer supported
  (`requires-python >=3.11`); CI tests 3.11 through 3.14. Python 3.10 reached
  end of life in October 2026.
- Live WebSocket tests are opt-in via `DEXSCRAPER_LIVE=1`.
- CI gates on `ruff check`, `ruff format --check` and `mypy`.
- Ruff is the only formatter/linter; legacy black, isort and flake8 config was
  removed and pre-commit pins match CI.
- The README documents every CLI flag and notes that the unofficial
  DexScreener screener WebSocket is no longer served.

### Removed

- The unused `typing_extensions` runtime dependency; nothing in the package
  imports it.
- The unused `dexscraper.logger` module.
- The unused numeric-cluster extraction pipeline (`_extract_numeric_clusters`,
  `_group_clusters_to_tokens`, `_build_token_profile` and the private helpers
  only they called) and the `DexScraper.value_ranges` attribute it read.
  Token extraction is unchanged.

## [1.1.0] - 2026-02-09

See the [v1.1.0 release](https://github.com/vincentkoc/dexscraper/releases/tag/v1.1.0).
Earlier versions (1.0.2, 1.0.1, 1.0.0, 0.1.2, 0.1.1, 0.1.0) are described on
the releases page.

[Unreleased]: https://github.com/vincentkoc/dexscraper/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/vincentkoc/dexscraper/releases/tag/v1.1.0
