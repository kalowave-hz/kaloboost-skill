import subprocess

from kaloboost import update


def test_latest_of_picks_highest_numeric_tag():
    assert update.latest_of(["v0.3.2", "v0.10.0", "v0.4.0", "v1.0.0-rc1", "nightly"]) == "v0.10.0"
    assert update.latest_of([]) is None


def test_ls_remote_reads_tags_from_git(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
    run("tag", "v0.4.0")
    run("tag", "v0.5.0")
    monkeypatch.setattr(update, "GIT_URL", str(repo))
    assert update.fetch_latest_tag() == "v0.5.0"


def test_ls_remote_failure_is_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(update, "GIT_URL", str(tmp_path / "missing"))
    assert update.fetch_latest_tag() is None
