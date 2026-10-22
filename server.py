#!/usr/bin/env python3
"""lm-node: HTTP 节点 + 启动时把机器信息写回仓库(证明这台机器真的活着)."""
import base64, json, os, platform, socket, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

START = time.time()

def info():
    up = -1
    try:
        up = float(open("/proc/uptime").read().split()[0])
    except Exception:
        pass
    mem = {}
    try:
        for ln in open("/proc/meminfo"):
            p = ln.split()
            if p[0] in ("MemTotal:", "MemAvailable:"):
                mem[p[0].rstrip(":")] = int(p[1]) // 1024
    except Exception:
        pass
    return {
        "ok": True,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpus": os.cpu_count(),
        "mem_total_mb": mem.get("MemTotal"),
        "mem_avail_mb": mem.get("MemAvailable"),
        "uptime_s": round(up, 1),
        "service_uptime_s": round(time.time() - START, 1),
        "cwd": os.getcwd(),
        "codespace": os.environ.get("CODESPACE_NAME"),
        "has_github_token": bool(os.environ.get("GITHUB_TOKEN")),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

def report():
    """用 Codespaces 注入的 GITHUB_TOKEN 把自检结果 commit 回仓库。"""
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        return "no-token"
    url = "https://api.github.com/repos/DAOHAN003/lm-node/contents/selfcheck.json"
    hdr = {"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
           "User-Agent": "lm-node"}
    sha = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=25) as r:
            sha = json.loads(r.read()).get("sha")
    except Exception:
        pass
    body = {"message": "selfcheck from codespace",
            "content": base64.b64encode(
                json.dumps(info(), ensure_ascii=False, indent=2).encode()).decode()}
    if sha:
        body["sha"] = sha
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={**hdr, "Content-Type": "application/json"},
                                     method="PUT")
        with urllib.request.urlopen(req, timeout=30) as r:
            return "reported %d" % r.status
    except Exception as e:
        return "report-fail: %s" % str(e)[:120]

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        b = json.dumps(info(), ensure_ascii=False, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print("report:", report(), flush=True)
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
