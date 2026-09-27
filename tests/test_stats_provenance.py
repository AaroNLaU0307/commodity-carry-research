"""Pins the source of every statistics helper in src/stats.py so a silent
edit fails CI. Normalisation: inspect.getsource(), trailing whitespace
stripped from each line, lines joined with "\\n", sha256.

Changing a helper is allowed; changing it without updating its pin here,
in the same commit and with the reason in the commit message, is not. The
helpers originate in this repository (not vendored), so there is no
upstream hash to compare against."""
import hashlib
import inspect

from src import config, stats

PINNED_SHA256 = {
    "stationary_bootstrap_sharpe": "a057bc79e5281bb5a6b2f23e1335c3f27825b798c6f7ab63ef6be97711a5c992",
    "stationary_bootstrap_multi_seed": "70f4d8b3c0067e143bee4cea8be60451c2899d64c02739d2ab5d26715f06127a",
    "sample_moments": "7c243cd6916d20c774e662af48d1c1b91939a0b048aef2c0b11c2b7592e14773",
    "trial_sharpe_std": "b896957d78ad5f4ff06237bd7ea8cf27c9ec410b76830a1b36e5a0879b054718",
    "deflated_sharpe_ratio": "38d9d0e90e5c2c7aca57f53454ccb2376d189685358a4d8d59cee5d6217cd58e",
    "dsr_sharpe_threshold": "12315c7efd91cb7e96bf930c7ed89610f9aa62194cd57b671ecb461d6dd94f7e",
    "benjamini_hochberg": "9cec5b96c2c793702bc5355b65f9865adc976333737fb8a686a065b9fc90b438",
    "newey_west_tstat": "748baf8c2837b30467406445857e03f7f504d48c557aaea5b31697c1a9a75381",
    "clustered_regression": "de55c96aa4084b8666ccc72f6291db1cb38d17f2e184bda0b5bca1dd42f55ee8",
}


def _normalised_sha256(fn) -> str:
    source = "\n".join(line.rstrip() for line in inspect.getsource(fn).splitlines())
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def test_every_stats_helper_matches_its_pinned_source_hash():
    actual = {name: _normalised_sha256(getattr(stats, name)) for name in PINNED_SHA256}
    changed = {name for name in PINNED_SHA256 if actual[name] != PINNED_SHA256[name]}
    assert not changed, f"src/stats.py helper(s) changed without updating their pin: {sorted(changed)}"


def test_every_stats_helper_is_pinned():
    defined = {name for name, obj in vars(stats).items()
               if inspect.isfunction(obj) and obj.__module__ == stats.__name__}
    assert defined == set(PINNED_SHA256)


def test_provenance_header_states_origin_bh_level_and_ci_method():
    header = stats.__doc__
    assert "written in this repository" in header
    assert "q = 0.10" in header and config.BH_FDR_Q == 0.10
    assert "stationary bootstrap" in header and "95% percentile interval" in header
    assert "tests/test_stats_provenance.py" in header
