#!/usr/bin/env python3
"""lm-node for Render: 状态心跳 + 带宽测试端点。

用途:
  /            返回 JSON 状态(含启动时间/运行秒数, 用于验证是否被睡眠)
  /ping        极轻量心跳, 供 Cloudflare Worker 保活用
  /big?mb=N    返回 N MB 数据, 测带宽
"""
import json
import os
import platform
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", 8080))
START_TS = time.time()
HITS = {"total": 0}


def sysinfo():
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pid": os.getpid(),
        "start_ts": int(START_TS),
        "uptime_sec": int(time.time() - START_TS),
        "now": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hits": HITS["total"],
        "env": {k: v for k, v in os.environ.items()
                if k.startswith(("RENDER", "PORT"))},
    }
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    info["mem_total_kb"] = int(line.split()[1])
                    break
    except Exception:
        pass
    return info


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        HITS["total"] += 1

        if self.path.startswith("/ping"):
            self._send(200, b'{"pong":true}')
            return

        if self.path.startswith("/big"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            mb = min(int(qs.get("mb", ["10"])[0]), 100)
            total = mb * 1024 * 1024
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(total))
            self.end_headers()
            chunk = b"x" * 262144
            sent = 0
            try:
                while sent < total:
                    n = min(len(chunk), total - sent)
                    self.wfile.write(chunk[:n])
                    sent += n
            except Exception:
                pass
            return

        body = json.dumps({"ok": True, "node": "lm-node-render", "info": sysinfo()},
                          ensure_ascii=False, indent=2).encode()
        self._send(200, body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"[lm-node] 监听 0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
