#!/usr/bin/env python3
"""
Dump do trace de leitura do cartucho (SPI/AUXSPI) pelo canal de controle.

Uso:
    cart-trace.py <socket> [--batch N] [--timeout MS] [--seconds S]

Exemplo:
    cart-trace.py /tmp/melonds-control.sock --batch 32 --timeout 200 --seconds 10

Inicia o trace, imprime cada leitura {addr, len, cmd} conforme chega, e para ao
fim do tempo (ou Ctrl-C). Requer o melonDS rodando com o canal de controle.
"""
import argparse
import json
import os
import socket
import sys
import time


def _recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def recv_msg(sock):
    hdr = b""
    while b"\r\n\r\n" not in hdr:
        c = sock.recv(1)
        if not c:
            return None
        hdr += c
    length = int([l for l in hdr.decode().split("\r\n")
                  if l.lower().startswith("content-length")][0].split(":")[1])
    return json.loads(_recv_exact(sock, length))


def call(sock, method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        req["params"] = params
    body = json.dumps(req).encode()
    sock.sendall(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    return recv_msg(sock)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("socket")
    ap.add_argument("--batch", type=int, default=32, help="itens por lote")
    ap.add_argument("--timeout", type=int, default=200, help="timeout do lote (ms)")
    ap.add_argument("--seconds", type=float, default=10.0, help="duração do dump")
    args = ap.parse_args()

    for _ in range(100):  # espera o socket do canal aparecer
        if os.path.exists(args.socket):
            break
        time.sleep(0.1)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(args.socket)
    sock.settimeout(2)

    r = None
    for _ in range(300):  # espera o emulador estar rodando
        r = call(sock, "cart.trace.start", {"batch": args.batch, "timeout_ms": args.timeout})
        if "error" not in r:
            break
        time.sleep(0.03)
    if r is None or "error" in r:
        print("erro ao iniciar o trace:", (r or {}).get("error"))
        sys.exit(1)
    print(">> trace ativo (batch=%d, timeout=%dms). dump por %.0fs..." %
          (args.batch, args.timeout, args.seconds))

    total = 0
    batches = 0
    t0 = time.time()
    try:
        while time.time() - t0 < args.seconds:
            try:
                m = recv_msg(sock)
            except socket.timeout:
                continue
            if m is None:
                break
            if m.get("method") == "event.cart":
                p = m["params"]
                batches += 1
                total += p["count"]
                if p.get("overflow"):
                    print("!! overflow (buffer no limite)")
                for rd in p["reads"]:
                    print("  addr=%#010x len=%-5d cmd=%#04x" % (rd["addr"], rd["len"], rd["cmd"]))
    except KeyboardInterrupt:
        pass

    print(">> parando. lotes=%d total=%d" % (batches, total))
    print(call(sock, "cart.trace.stop"))


if __name__ == "__main__":
    main()
