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


def test_ls_remote_never_runs_askpass(tmp_path, monkeypatch):
    """A 401 must not reach any askpass program the user's environment configured."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Deny(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="x"')
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Deny)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    marker = tmp_path / "asked"
    askpass = tmp_path / "askpass.sh"
    askpass.write_text(f"#!/bin/sh\ntouch {marker}\necho secret\n")
    askpass.chmod(0o755)
    monkeypatch.setenv("GIT_ASKPASS", str(askpass))
    monkeypatch.setenv("SSH_ASKPASS", str(askpass))
    monkeypatch.setenv("HOME", str(tmp_path))  # no stored credentials / helpers
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setattr(update, "GIT_URL", f"http://127.0.0.1:{server.server_address[1]}/r.git")
    try:
        assert update.fetch_latest_tag(timeout=10) is None
    finally:
        server.shutdown()
    assert not marker.exists()
