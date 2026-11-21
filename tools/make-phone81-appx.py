#!/usr/bin/env python3
"""Builds an unsigned Windows Phone 8.1 APPX (no Windows tools needed).

Usage: make-phone81-appx.py <out-dir> <packaging-dir> <output.appx>

<out-dir>       Chromium build output (content_shell.exe and its resources).
<packaging-dir> chromium-wp81-port/packaging/wp81 (AppxManifest.xml, Assets/).

The package is a ZIP whose entries are stored uncompressed, plus
AppxBlockMap.xml (SHA-256 of every 64 KiB block of every file) and
[Content_Types].xml, as makeappx.exe would write them. Sign it afterwards
(osslsigncode adds AppxSignature.p7x). Uncompressed entries keep the block map
simple: blocks then have no compressed Size attribute.
"""

import base64
import hashlib
import struct
import sys
import zlib
from pathlib import Path

RESOURCES = [
    "content_shell.exe",
    "content_shell.pak",
    "icudtl.dat",
    "snapshot_blob.bin",
    "ui_resources_100_percent.pak",
]
BLOCK = 64 * 1024
CONTENT_TYPES = {
    "exe": "application/x-msdownload",
    "pak": "application/octet-stream",
    "dat": "application/octet-stream",
    "bin": "application/octet-stream",
    "png": "image/png",
}


def local_header(name, data, crc):
  encoded = name.encode("utf-8")
  return struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0x0800, 0, 0, 0x21,
                     crc, len(data), len(data), len(encoded), 0) + encoded


def central_header(name, data, crc, offset):
  encoded = name.encode("utf-8")
  return struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0x0800, 0, 0,
                     0x21, crc, len(data), len(data), len(encoded), 0, 0, 0,
                     0, 0, offset) + encoded


def main():
  out_dir, packaging, output = (Path(a) for a in sys.argv[1:4])
  entries = [(n, (out_dir / n).read_bytes()) for n in RESOURCES]
  for asset in sorted((packaging / "Assets").iterdir()):
    entries.append((f"Assets/{asset.name}", asset.read_bytes()))
  entries.append(("AppxManifest.xml",
                  (packaging / "AppxManifest.xml").read_bytes()))

  blockmap = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
              '<BlockMap xmlns="http://schemas.microsoft.com/appx/2010/blockmap"'
              ' HashMethod="http://www.w3.org/2001/04/xmlenc#sha256">']
  # The manifest goes last, like makeappx writes it.
  ordered = [e for e in entries if e[0] != "AppxManifest.xml"]
  ordered.append(next(e for e in entries if e[0] == "AppxManifest.xml"))
  for name, data in ordered:
    lfh = 30 + len(name.encode("utf-8"))
    blockmap.append(f'<File Name="{name.replace("/", chr(92))}" '
                    f'Size="{len(data)}" LfhSize="{lfh}">')
    for i in range(0, max(len(data), 1), BLOCK):
      digest = hashlib.sha256(data[i:i + BLOCK]).digest()
      if not data:
        break
      blockmap.append(
          f'<Block Hash="{base64.b64encode(digest).decode()}"/>')
    blockmap.append("</File>")
  blockmap.append("</BlockMap>")
  blockmap_xml = "\r\n".join(blockmap).encode("utf-8")

  extensions = sorted({n.rsplit(".", 1)[1].lower() for n, _ in ordered
                       if "." in n and not n.endswith(".xml")})
  types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
           'content-types">']
  for ext in extensions:
    types.append(f'<Default Extension="{ext}" '
                 f'ContentType="{CONTENT_TYPES.get(ext, "application/octet-stream")}"/>')
  types += [
      '<Override PartName="/AppxManifest.xml" '
      'ContentType="application/vnd.ms-appx.manifest+xml"/>',
      '<Override PartName="/AppxBlockMap.xml" '
      'ContentType="application/vnd.ms-appx.blockmap+xml"/>',
      "</Types>",
  ]
  types_xml = "".join(types).encode("utf-8")

  files = ordered + [("AppxBlockMap.xml", blockmap_xml),
                     ("[Content_Types].xml", types_xml)]
  with output.open("wb") as f:
    central = []
    for name, data in files:
      crc = zlib.crc32(data) & 0xFFFFFFFF
      offset = f.tell()
      f.write(local_header(name, data, crc))
      f.write(data)
      central.append(central_header(name, data, crc, offset))
    start = f.tell()
    for c in central:
      f.write(c)
    size = f.tell() - start
    f.write(struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(central),
                        len(central), size, start, 0))
  print(f"{output}: {len(files)} entries, {output.stat().st_size} bytes")


if __name__ == "__main__":
  main()
