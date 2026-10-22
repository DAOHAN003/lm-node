#!/usr/bin/env python3
"""最小 HTTP 节点: 报系统信息 + 心跳, 证明这台机器活着。"""
import json, os, platform, socket, subprocess, time
from http.server import BaseHTTPRequestHandler, HTTPServer

START = time.time()

def info():
    try:
        up = float(open("/proc/uptime").read().split()[0])
    except Exception:
        up = -1
    try:
        mem = {}
        for ln in open("/proc/meminfo"):
            k, v = ln.split(":")[0], ln.split()[1]
            if k in ("MemTotal", "MemAvailable"):
                mem[k] = int(v) // 1024
    except Exception:
        mem = {}
    return {
        "ok": True,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpus": os.cpu_count(),
        "mem_total_mb": mem.get("MemTotal"),
        "mem_avail_mb": mem.get("MemAvailable"),
        "uptime_s": round(up, 1),
        "proc_uptime_s": round(time.time() - START, 1),
        "cwd": os.getcwd(),
        "env_codespace": os.environ.get("CODESPACE_NAME"),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(info(), ensure_ascii=False, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
