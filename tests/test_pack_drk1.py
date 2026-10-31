import importlib.util
import pathlib
import struct
import unittest

root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack_drk1", root / "tools/pack_drk1.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestDRK1Packer(unittest.TestCase):
    def setUp(self):
        self.mesh = (b"DRM1" + struct.pack("<HH", 6, 2) +
                     b"\\0" * 36 + struct.pack("<HHH", 0, 1, 2) +
                     struct.pack("<HHH", 3, 4, 5))
        self.bones = [
            {"pivot": [0, 0, 0], "parent": -1},
            {"pivot": [4096, 0, 0], "parent": 0},
        ]
        self.influences = [[0, 0, 255]] * 3 + [
            [1, 1, 255], [1, 1, 255], [0, 1, 128]]
        self.frames = [
            [[0, 0, 0, 0], [0, 0, 0, 0]],
            [[0, 0, 0, 64], [0, 64, 0, 64]],
        ]

    def test_binary_layout_matches_runtime(self):
        result = module.pack(self.mesh, self.bones, self.influences, self.frames, 4)
        self.assertEqual(len(result), 60)
        self.assertEqual(result[:10], b"DRK1\\x06\\x00\\x02\\x02\\x04\\x00")
        self.assertEqual(result[16:18], bytes([255, 0]))
        self.assertEqual(result[18:26], struct.pack("<hhhBB", 4096, 0, 0, 0, 0))
        self.assertEqual(result[41:44], bytes([0, 1, 128]))
        self.assertEqual(result[52:60], bytes([0, 0, 0, 64, 0, 64, 0, 64]))

    def test_demo_wave_only_changes_child_bone(self):
        poses = module.demo_tail_wag(3)
        self.assertEqual(len(poses), 4)
        self.assertEqual([x[1][3] for x in poses], [0, 32, 0, -32])
        self.assertTrue(all(x[0] == [0, 0, 0, 0] for x in poses))
        with self.assertRaises(ValueError):
            module.demo_tail_wag(1)

    def test_strict_bounds(self):
        invalid = [
            ([], self.influences, self.frames, 4),
            ([{"pivot": [0, 0, 0], "parent": 0}], self.influences,
             [[[0, 0, 0, 0]], [[0, 0, 0, 0]]], 4),
            (self.bones[:1] + [{"pivot": [4096, 0, 0], "parent": 1}],
             self.influences, self.frames, 4),
            ([{"pivot": [32768, 0, 0], "parent": -1}], self.influences,
             self.frames, 4),
            (self.bones, self.influences[:5], self.frames, 4),
            (self.bones, self.influences[:5] + [[0, 2, 128]], self.frames, 4),
            (self.bones, self.influences[:5] + [[0, 1, True]], self.frames, 4),
            (self.bones, self.influences, self.frames[:1], 4),
            (self.bones, self.influences, self.frames * 5, 4),
            (self.bones, self.influences,
             [self.frames[0], self.frames[1][:1]], 4),
            (self.bones, self.influences,
             [self.frames[0], [[0, 0, 0, 128], [0, 0, 0, 0]]], 4),
            (self.bones, self.influences, self.frames, 0),
            (self.bones, self.influences, self.frames, 61),
        ]
        for args in invalid:
            with self.subTest(str(args)[:50]), self.assertRaises(ValueError):
                module.pack(self.mesh, *args)
        for bad in (b"bad", self.mesh[:-1], self.mesh + b"x"):
            with self.assertRaises(ValueError):
                module.pack(bad, self.bones, self.influences, self.frames, 4)


if __name__ == "__main__":
    unittest.main()
