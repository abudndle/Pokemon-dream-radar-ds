#!/usr/bin/env python3
"""Read-only inventory of decrypted Dream Radar NCCH ExeFS/RomFS asset types.

Inspects ExeFS/banner CBMD LZ11/CGFX, ExeFS/logo LZ11/DARC, and
non-CARC RomFS signatures. Exports METADATA ONLY: never original bytes.
The validated banner CGFX assets are HOME MENU graphics, not confirmed
Pokémon gameplay meshes or skeletal animations.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from inventory_ncch_romfs import audit as romfs_inventory
from inventory_darc import parse_darc
from audit_darc_asset_kinds import classify_item

MAX_IMAGE = 512 * 1024 * 1024
MAX_CGFX = 0x80000
MAX_LOGO = 2 * 1024 * 1024


class ExefsAuditError(ValueError):
    pass


def u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise ExefsAuditError("Truncated 32-bit field")
    return struct.unpack_from("<I", data, offset)[0]


def decompress_lz11(payload, max_output=MAX_CGFX):
    """Bounded LZ11 decoder; return (decoded data, consumed bytes)."""
    if len(payload) < 4 or payload[0] != 0x11:
        raise ExefsAuditError("Not an LZ11 stream")
    target = int.from_bytes(payload[1:4], "little")
    pos = 4
    if not target:
        if pos + 4 > len(payload):
            raise ExefsAuditError("Truncated LZ11 extended size")
        target = u32(payload, pos)
        pos += 4
    if target < 1 or target > max_output:
        raise ExefsAuditError("LZ11 output outside size budget")
    result = bytearray()
    while len(result) < target:
        if pos >= len(payload):
            raise ExefsAuditError("Truncated LZ11 flags")
        flags = payload[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(result) >= target:
                break
            if flags & (1 << bit):
                if pos >= len(payload):
                    raise ExefsAuditError("Truncated LZ11 backreference")
                a = payload[pos]
                pos += 1
                nibble = a >> 4
                if nibble == 0:
                    if pos + 2 > len(payload):
                        raise ExefsAuditError("Truncated medium LZ11 token")
                    b, c = payload[pos:pos+2]
                    pos += 2
                    length = (((a & 15) << 4) | (b >> 4)) + 0x11
                    distance = (((b & 15) << 8) | c) + 1
                elif nibble == 1:
                    if pos + 3 > len(payload):
                        raise ExefsAuditError("Truncated extended LZ11 token")
                    b, c, d = payload[pos:pos+3]
                    pos += 3
                    length = (((a & 15) << 12) | (b << 4) | (c >> 4)) + 0x111
                    distance = (((c & 15) << 8) | d) + 1
                else:
                    if pos >= len(payload):
                        raise ExefsAuditError("Truncated short LZ11 token")
                    b = payload[pos]
                    pos += 1
                    length = nibble + 1
                    distance = (((a & 15) << 8) | b) + 1
                if distance > len(result) or length > target - len(result):
                    raise ExefsAuditError("Invalid LZ11 match distance or length")
                for _ in range(length):
                    result.append(result[-distance])
            else:
                if pos >= len(payload):
                    raise ExefsAuditError("Truncated LZ11 literal")
                result.append(payload[pos])
                pos += 1
    return bytes(result), pos


def check_cgfx(data):
    if len(data) < 32 or data[:4] != b"CGFX":
        raise ExefsAuditError("Expected decoded CGFX banner graphics")
    magic, bom, header, revision, length, sections = struct.unpack_from(
        "<4sHHIII", data)
    if (magic != b"CGFX" or bom != 0xfeff or header != 20 or
            revision == 0xffffffff or length != len(data) or
            sections < 1 or sections > 8 or data[20:24] != b"DATA" or
            not 8 <= u32(data, 24) <= len(data) - 20):
        raise ExefsAuditError("Invalid CGFX header or DATA section")
    # A string signature is only a diagnostic marker, not a reconstructed
    # skeleton or an independently parsed CMDL geometry structure.
    return {"decoded_bytes": len(data),
            "section_count": sections,
            "cmdl_signature_count": data.count(b"CMDL"),
            "imag_signature_count": data.count(b"IMAG")}


def inspect_cbmd(data):
    if len(data) < 0x88 or data[:4] != b"CBMD" or data[4:8] != b"\0"*4:
        raise ExefsAuditError("ExeFS banner is not a supported CBMD")
    # 0x08..0x83 includes 31 optional language/region slots.
    offsets = struct.unpack_from("<31I", data, 8)
    wav_offset = u32(data, 0x84)
    present = [(i, off) for i, off in enumerate(offsets) if off]
    unique = sorted(set(off for _, off in present))
    if (not present or len(unique) != len(present) or
            not 0x88 <= unique[0] < wav_offset <= len(data) - 0x40):
        raise ExefsAuditError("Invalid CBMD graphics offsets")
    if data[wav_offset:wav_offset+4] != b"CWAV" or \
       data[wav_offset+4:wav_offset+6] != b"\xff\xfe" or \
       u32(data, wav_offset+12) != len(data)-wav_offset:
        raise ExefsAuditError("Invalid CBMD CWAV audio section")

    entries = []
    for i, off in present:
        following = min((value for value in unique if value > off),
                        default=wav_offset)
        if following > wav_offset or off >= following:
            raise ExefsAuditError("Overlapping CBMD graphics")
        decoded, consumed = decompress_lz11(data[off:following], MAX_CGFX)
        extra = data[off+consumed:following]
        if len(extra) > 16 or any(extra):
            raise ExefsAuditError("Unexpected CBMD CGFX padding")
        kind = check_cgfx(decoded)
        entries.append({"slot": i, "compressed_bytes": consumed,
                        "padding_bytes": len(extra), **kind})
    return {"graphics_format": "CBMD",
            "cgfx_container_count": len(entries),
            "cgfx_containers": entries,
            "cmdl_markers_total": sum(x["cmdl_signature_count"] for x in entries),
            "banner_audio": {"format": "CWAV",
                             "bytes": len(data)-wav_offset},
            "scope": "Nintendo 3DS HOME MENU banner, not gameplay Pokémon"}


def inspect_logo(data):
    if len(data) < 4:
        raise ExefsAuditError("Missing ExeFS logo payload")
    decoded, consumed = decompress_lz11(data, MAX_LOGO)
    if any(data[consumed:]):
        raise ExefsAuditError("Nonzero trailing ExeFS logo padding")
    try:
        entries = parse_darc(decoded)
        counts = Counter()
        for entry in entries:
            begin, size = entry["offset"], entry["size"]
            kind, _, candidate = classify_item(entry["path"], decoded[begin:begin+size])
            if candidate:
                raise ExefsAuditError("ExeFS logo DARC has unverified 3D resource")
            counts[kind] += 1
    except ValueError as error:
        raise ExefsAuditError("Invalid ExeFS logo DARC: " + str(error)) from error
    return {"compression": "LZ11", "container": "DARC",
            "decoded_bytes": len(decoded),
            "compressed_bytes": consumed,
            "file_count": len(entries),
            "categories": dict(sorted(counts.items())),
            "scope": "ExeFS Nintendo logo UI, not gameplay Pokémon"}


def inspect_exefs(image):
    if len(image) < 0x200 or image[0x100:0x104] != b"NCCH":
        raise ExefsAuditError("Missing NCCH signature")
    if len(image) > MAX_IMAGE or u32(image, 0x104)*0x200 != len(image):
        raise ExefsAuditError("Invalid complete NCCH content size")
    start, size = u32(image, 0x1a0)*0x200, u32(image, 0x1a4)*0x200
    if start < 0x200 or size < 0x200 or start + size > len(image):
        raise ExefsAuditError("Invalid ExeFS partition bounds")
    names = set()
    sections = []
    extents = []
    for i in range(10):
        namebytes, offset, length = struct.unpack_from("<8sII", image, start+i*16)
        if namebytes == b"\0"*8:
            if offset or length:
                raise ExefsAuditError("Nonempty ExeFS descriptor with empty name")
            continue
        name = namebytes.rstrip(b"\0")
        if (not name or b"\0" in name or
                any(byte < 33 or byte > 126 for byte in name)):
            raise ExefsAuditError("Unsafe ExeFS filename")
        name = name.decode("ascii")
        if name in names or length == 0 or offset + length > size - 0x200:
            raise ExefsAuditError("Duplicate or out-of-bounds ExeFS entry")
        names.add(name)
        a, b = start + 0x200 + offset, start + 0x200 + offset + length
        if any(not (b <= prev_a or a >= prev_b) for prev_a, prev_b in extents):
            raise ExefsAuditError("Overlapping ExeFS entries")
        extents.append((a, b))
        sections.append({"name": name, "bytes": length, "relative_offset": offset})
    byname = {section["name"]: section for section in sections}
    for required in (".code", "banner", "icon", "logo"):
        if required not in byname:
            raise ExefsAuditError("Missing original ExeFS section " + required)

    def payload(name):
        item = byname[name]
        a = start+0x200+item["relative_offset"]
        return image[a:a+item["bytes"]]

    icon = payload("icon")
    if len(icon) < 0x200 or icon[:4] != b"SMDH":
        raise ExefsAuditError("Invalid ExeFS SMDH icon")
    result = {"section_count": len(sections), "sections": sections,
              "icon_format": "SMDH",
              "banner": inspect_cbmd(payload("banner")),
              "logo": inspect_logo(payload("logo")),
              "code_status": "opaque_executable_not_a_model_decode"}
    return result


def inspect_romfs_types(path, image):
    listing = romfs_inventory(path)
    start = u32(image, 0x1b0)*0x200
    types = Counter()
    for entry in listing["files"]:
        name = entry["path"]
        offset = start + entry["romfs_offset"]
        count = entry["size"]
        if count < 4 or offset < 0 or offset+count > len(image):
            raise ExefsAuditError("RomFS file extends outside NCCH")
        data = memoryview(image)[offset:offset+min(16, count)]
        suffix = name.rsplit(".", 1)[-1].lower()
        if suffix == "carc":
            # 0x40 is a candidate LZH8 header, independently verified by
            # tools/decode_ncch_lzh8.py for original CARC/DARC archives.
            if data[0] != 0x40:
                raise ExefsAuditError("Unexpected original CARC header")
            kind = "CARC_LZH8_header"
        elif suffix == "shbin":
            if bytes(data[:4]) != b"DVLB":
                raise ExefsAuditError("Invalid SHBIN/DVLB shader header")
            kind = "DVLB_shader"
        elif suffix == "bcstm":
            if (bytes(data[:6]) != b"CSTM\xff\xfe" or count < 16 or
                    int.from_bytes(data[12:16], "little") != count):
                raise ExefsAuditError("Invalid CSTM audio header/size")
            kind = "CSTM_audio"
        elif suffix == "bcsar":
            if (bytes(data[:6]) != b"CSAR\xff\xfe" or count < 16 or
                    int.from_bytes(data[12:16], "little") != count):
                raise ExefsAuditError("Invalid CSAR audio header/size")
            kind = "CSAR_audio"
        else:
            kind = "unclassified_file"
        types[kind] += 1
    return {"file_count": listing["file_count"],
            "types": dict(sorted(types.items())),
            "classified_3d_gameplay_meshes": 0,
            "scope": "Top-level RomFS signatures only; no blind executable reverse engineering"}


def audit(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_IMAGE:
        raise ExefsAuditError("Input must be a bounded private decrypted NCCH file")
    image = path.read_bytes()
    return {"format": "NCCH_EXEFS_MODEL_SOURCE_AUDIT_V1",
            "image_bytes": len(image),
            "exefs": inspect_exefs(image),
            "romfs": inspect_romfs_types(path, image),
            "verified_3ds_pokemon_skeletal_animation": False,
            "private_asset_bytes_exported": 0,
            "caveat": ("14 real CGFX 3D containers belong to ExeFS HOME MENU banner; "
                       "this DOES NOT identify or decode Pokémon encounter geometry "
                       "or original skeletal tracks. RomFS extension/header inventory "
                       "and an opaque executable scan cannot rule out native data "
                       "stored in unknown formats or runtime code.")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ncch", type=Path, help="Private decrypted 3DS NCCH file")
    p.add_argument("report", type=Path, help="Metadata-only JSON destination")
    args = p.parse_args()
    result = audit(args.ncch)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                           encoding="utf-8")
    print(f"Verified {result['exefs']['banner']['cgfx_container_count']} "
          "Home Menu CGFX banner containers; "
          f"{result['exefs']['logo']['file_count']} Nintendo-logo UI files; "
          f"{result['romfs']['file_count']} RomFS files. "
          "No genuine Pokémon skeletal data was decoded.")


if __name__ == "__main__":
    main()
