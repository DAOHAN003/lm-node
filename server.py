#!/usr/bin/env python3
"""lm-node: HTTP 服务 + 启动自检上报。"""
import base64
import json
import os
import platform
import socket
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080


def sysinfo():
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpus": os.cpu_count(),
        "codespace": os.environ.get("CODESPACE_NAME", "?"),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    info["mem_total_kb"] = int(line.split()[1])
                    break
    except Exception:
        pass
    try:
        info["disk"] = subprocess.run(["df", "-h", "/"], capture_output=True,
                                      text=True, timeout=10).stdout.splitlines()[-1]
    except Exception:
        pass
    return info


def report(info):
    """用注入的 PAT 把自检写回仓库。"""
    tok = os.environ.get("LM_PAT")
    if not tok:
        return "no-pat"
    url = f"https://api.github.com/repos/DAOHAN003/lm-node/contents/selfcheck.json"
    hdr = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
           "User-Agent": "lm-node"}
    sha = None
    try:
        req = urllib.request.Request(url, headers=hdr)
        sha = json.loads(urllib.request.urlopen(req, timeout=20).read()).get("sha")
    except Exception:
        pass
    body = {"message": "selfcheck", "content": base64.b64encode(
        json.dumps(info, ensure_ascii=False, indent=2).encode()).decode()}
    if sha:
        body["sha"] = sha
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={**hdr, "Content-Type": "application/json"},
                                     method="PUT")
        urllib.request.urlopen(req, timeout=30)
        return "reported"
    except Exception as e:
        return "report-fail:" + str(e)[:120]


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"ok": True, "node": "lm-node", "info": sysinfo()},
                          ensure_ascii=False, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    info = sysinfo()
    print("[lm-node] 自检:", json.dumps(info, ensure_ascii=False))
    threading.Thread(target=lambda: print("[lm-node] 上报:", report(info)), daemon=True).start()
    print(f"[lm-node] 监听 0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
