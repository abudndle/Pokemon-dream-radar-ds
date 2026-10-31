import importlib.util
import pathlib
import struct
import unittest

root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack_dra1", root / "tools/pack_dra1.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class TestDRA1Packer(unittest.TestCase):
    def setUp(self):
        self.mesh = (b"DRM1" + struct.pack("<HH", 3, 1) +
                     b"\0" * 18 + struct.pack("<HHH", 0, 1, 2))
        self.frames = [
            [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
            [[0, 64, 0], [0, 64, 0], [0, 64, 0]],
        ]

    def test_frame_bytes_match_c_decoder(self):
        data = tool.pack(self.mesh, self.frames, 4)
        self.assertEqual(len(data), 26)
        self.assertEqual(data[:8], b"DRA1\x03\x00\x02\x04")
        self.assertEqual(data[8:17], b"\0" * 9)
        self.assertEqual(data[17:], bytes([0, 64, 0] * 3))

    def test_generated_idle_cycle(self):
        frames = tool.idle_bob(3)
        data = tool.pack(self.mesh, frames, 8)
        self.assertEqual(data[:8], b"DRA1\x03\x00\x04\x08")
        self.assertEqual(frames[0][0], [0, 0, 0])
        self.assertEqual(frames[1][0], [0, 64, 0])
        self.assertEqual(frames[3][0], [0, -64, 0])

    def test_strict_input_validation(self):
        for frames in ([], self.frames[:1], self.frames * 5,
                       [self.frames[0], self.frames[1][:2]],
                       [self.frames[0], [[0, True, 0]] * 3],
                       [self.frames[0], [[0, 128, 0]] * 3],
                       [self.frames[0], [[0, -129, 0]] * 3]):
            with self.assertRaises(ValueError):
                tool.pack(self.mesh, frames, 4)
        for ticks in (0, 61, True, -1):
            with self.assertRaises(ValueError):
                tool.pack(self.mesh, self.frames, ticks)
        for mesh in (b"INVALID", self.mesh[:-1], self.mesh + b"x"):
            with self.assertRaises(ValueError):
                tool.pack(mesh, self.frames, 4)
        large = b"DRM1" + struct.pack("<HH", 2049, 1)
        with self.assertRaises(ValueError):
            tool.vertex_count(large)


if __name__ == "__main__":
    unittest.main()
