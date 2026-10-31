import importlib.util
import pathlib
import struct
import unittest

root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack_drb1", root / "tools/pack_drb1.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class TestDRB1Packer(unittest.TestCase):
    def setUp(self):
        self.mesh = (b"DRM1" + struct.pack("<HH", 6, 2) +
                     b"\0" * 36 + struct.pack("<HHH", 0, 1, 2) +
                     struct.pack("<HHH", 3, 4, 5))
        self.pivots = [[0, 0, 0], [4096, 0, 0]]
        self.owners = [0, 0, 0, 1, 1, 1]
        self.frames = [
            [[0, 0, 0, 0], [0, 0, 0, 0]],
            [[0, 64, 0, 0], [32, 0, 0, 64]],
        ]

    def test_format_matches_c_decoder(self):
        data = tool.pack(self.mesh, self.pivots, self.owners, self.frames, 4)
        self.assertEqual(len(data), 44)
        self.assertEqual(data[:10], b"DRB1\x06\x00\x02\x02\x04\x00")
        self.assertEqual(data[16:22], b"\x00\x10\x00\x00\x00\x00")
        self.assertEqual(data[22:28], bytes(self.owners))
        self.assertEqual(data[36:44], bytes([0, 64, 0, 0, 32, 0, 0, 64]))

    def test_demo_wags_only_group_one(self):
        f = tool.demo_wag(3)
        self.assertEqual(len(f), 4)
        self.assertEqual([frame[1][3] for frame in f], [0, 24, 0, -24])
        self.assertTrue(all(frame[0] == [0, 0, 0, 0] for frame in f))
        with self.assertRaises(ValueError):
            tool.demo_wag(1)

    def test_invalid_inputs(self):
        invalid = [
            (self.pivots[:0], self.owners, self.frames, 4),
            ([[32768, 0, 0]], [0] * 6, self.frames, 4),
            (self.pivots, self.owners[:5], self.frames, 4),
            (self.pivots, [0, 0, 0, 2, 1, 1], self.frames, 4),
            (self.pivots, [0, 0, 0, True, 1, 1], self.frames, 4),
            (self.pivots, self.owners, self.frames[:1], 4),
            (self.pivots, self.owners, self.frames * 5, 4),
            (self.pivots, self.owners, [self.frames[0], self.frames[1][:1]], 4),
            (self.pivots, self.owners, [self.frames[0], [[0, 128, 0, 0], [0, 0, 0, 0]]], 4),
            (self.pivots, self.owners, self.frames, 0),
            (self.pivots, self.owners, self.frames, 61),
        ]
        for args in invalid:
            with self.subTest(args=str(args)[:45]), self.assertRaises(ValueError):
                tool.pack(self.mesh, *args)
        for mesh in (b"invalid", self.mesh[:-1], self.mesh + b"x"):
            with self.assertRaises(ValueError):
                tool.pack(mesh, self.pivots, self.owners, self.frames, 4)


if __name__ == "__main__":
    unittest.main()
