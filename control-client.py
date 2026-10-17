#!/usr/bin/env python3
"""
Cliente do canal de controle (JSON-RPC 2.0 sobre Unix socket).

Uso:
    control-client.py <socket> <method> [json-params]
    control-client.py <socket>                 # modo interativo

Exemplos:
    control-client.py /tmp/melonds-control.sock ping
    control-client.py /tmp/melonds-control.sock input.key '{"mask": 1022}'   # A
    control-client.py /tmp/melonds-control.sock input.release
    control-client.py /tmp/melonds-control.sock input.touch '{"x":128,"y":96}'
    control-client.py /tmp/melonds-control.sock screen.capture '{"screens":"both","format":"rgba8"}'
    control-client.py /tmp/melonds-control.sock screen.capture '{"screens":"top","every_ms":1000,"duration_ms":10000}'
"""
import json
import socket
import sys


def _recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def _recv_message(sock):
    hdr = b""
    while b"\r\n\r\n" not in hdr:
        c = sock.recv(1)
        if not c:
            return None
        hdr += c
    length = int([l for l in hdr.decode().split("\r\n")
                  if l.lower().startswith("content-length")][0].split(":")[1])
    msg = json.loads(_recv_exact(sock, length))

    # binary frame follows a message that announces it (result or params)
    for container in (msg.get("result"), msg.get("params")):
        if isinstance(container, dict) and "binary" in container:
            n = int.from_bytes(_recv_exact(sock, 4), "big")
            msg["_binary"] = _recv_exact(sock, n)
            break
    return msg


def call(sock, method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        req["params"] = params
    body = json.dumps(req).encode()
    sock.sendall(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    return _recv_message(sock)


def save_frame(data, width, height, fmt, base):
    """Salva um frame (BGRA/RGBA, 8bpp). PNG via PIL, senao PPM P6."""
    try:
        from PIL import Image
        raw_mode = "RGBA" if fmt == "rgba8" else "BGRA"
        img = Image.frombuffer("RGBA", (width, height), data, "raw", raw_mode, 0, 1)
        path = base + ".png"
        img.save(path)
        return path
    except Exception:
        swap = (fmt == "bgra8")
        rows = []
        for i in range(0, width * height * 4, 4):
            if swap:
                b, g, r = data[i], data[i + 1], data[i + 2]
            else:
                r, g, b = data[i], data[i + 1], data[i + 2]
            rows.append(bytes((r, g, b)))
        path = base + ".ppm"
        with open(path, "wb") as f:
            f.write(b"P6\n%d %d\n255\n" % (width, height))
            f.write(b"".join(rows))
        return path


def save_binary(msg, prefix="capture"):
    if not (isinstance(msg, dict) and "_binary" in msg):
        return
    b = msg["result"]["binary"] if "result" in msg else msg["params"]["binary"]
    w, h, fmt = b["width"], b["height"], b["format"]
    framesize = w * h * 4
    raw = msg["_binary"]
    for i in range(len(raw) // framesize):
        path = save_frame(raw[i * framesize:(i + 1) * framesize], w, h, fmt, "%s_%d" % (prefix, i))
        print("  salvo:", path)


def stream_loop(sock):
    count = 0
    while True:
        msg = _recv_message(sock)
        if msg is None:
            break
        method = msg.get("method")
        if method == "event.frame":
            count += 1
            save_binary(msg, "stream_%03d" % count)
            print("  frame", count)
        elif method == "event.stream_end":
            print("stream end, count =", msg["params"].get("count"))
            break


def run(sock, method, params):
    msg = call(sock, method, params)
    print(json.dumps({k: v for k, v in msg.items() if k != "_binary"}))
    save_binary(msg)
    result = msg.get("result") if isinstance(msg, dict) else None
    if isinstance(result, dict) and result.get("streaming"):
        stream_loop(sock)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sys.argv[1])

    if len(sys.argv) >= 3:
        params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        run(sock, sys.argv[2], params)
        return

    print('interativo. ex: input.key {"mask": 1022}   (Ctrl-D sai)')
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        run(sock, parts[0], json.loads(parts[1]) if len(parts) > 1 else None)


if __name__ == "__main__":
    main()
