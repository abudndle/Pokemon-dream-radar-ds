import importlib.util
import pathlib
import struct
import unittest

root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack_drt1", root / "tools/pack_drt1.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackTextureTest(unittest.TestCase):
    def setUp(self):
        self.mesh = b"DRM1" + struct.pack("<HH", 3, 1) + b"\x00" * 18 + struct.pack("<HHH", 0, 1, 2)
        self.uv = [[0, 0], [4096, 0], [0, 4096]]
        self.pixels = struct.pack("<4H", 0x8000, 0x801F, 0x83E0, 0xFFFF)

    def test_pack_matches_documented_layout(self):
        packed = module.pack(self.mesh, self.uv, self.pixels, 2, 2)
        self.assertEqual(packed[:8], b"DRT1\x02\x02\x03\x00")
        self.assertEqual(packed[8:12], b"\x00\x00\x00\x00")
        self.assertEqual(packed[20:], self.pixels)
        self.assertEqual(len(packed), 28)

    def test_bad_uv_or_pixels_rejected(self):
        for bad_uv in (self.uv[:-1], [[0, 0], [4097, 0], [0, 4096]], [[True, 0], [4096, 0], [0, 4096]]):
            with self.assertRaises(ValueError):
                module.pack(self.mesh, bad_uv, self.pixels, 2, 2)
        for bad_pixels in (self.pixels[:-1], b"\0\0" + self.pixels[2:]):
            with self.assertRaises(ValueError):
                module.pack(self.mesh, self.uv, bad_pixels, 2, 2)
        with self.assertRaises(ValueError):
            module.pack(self.mesh, self.uv, self.pixels, 65, 2)


if __name__ == "__main__":
    unittest.main()
