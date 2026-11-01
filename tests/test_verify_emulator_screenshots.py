#!/usr/bin/env python3
"""Test screenshot verifier policies without manufacturing emulator evidence."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'verify_emulator_screenshots', root/'tools/verify_emulator_screenshots.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def synthetic_header(path, width=256, height=384, marker=b'frame'):
    # Minimal incomplete PNG header: the identify decoder is MOCKED because
    # this tests validation logic, NOT a claim to produce actual screenshots.
    blob = (module.PNG_SIGNATURE + struct.pack('>I', 13) + b'IHDR' +
            struct.pack('>II', width, height) + b'\x08\x02\0\0\0' +
            marker.ljust(80, b'0'))
    path.write_bytes(blob)


class TestEmulatorCaptureValidation(unittest.TestCase):
    def test_nonblank_screenshots_and_differences(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            a, b = path/'01-title.png', path/'02-after-start.png'
            synthetic_header(a, marker=b'first')
            synthetic_header(b, marker=b'second')
            response = mock.Mock(stdout='174|0.26')
            with mock.patch.object(module.subprocess, 'run', return_value=response) as call:
                result = module.verify([a, b])
            self.assertEqual(result['count'], 2)
            self.assertEqual(result['distinct_frame_hashes'], 2)
            self.assertEqual(result['verified'], 'nonblank_dual_screen_window_captures')
            self.assertFalse('gameplay_test_passed' in result)
            self.assertEqual(call.call_count, 2)
            self.assertEqual(call.call_args.args[0][0], 'identify')

    def test_blank_or_corrupt_screens_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            image = path/'screen.png'
            synthetic_header(image)
            with mock.patch.object(module.subprocess, 'run',
                                   return_value=mock.Mock(stdout='1|0.0')):
                with self.assertRaisesRegex(ValueError, 'blank'):
                    module.inspect_image(image)
            with mock.patch.object(module.subprocess, 'run',
                                   return_value=mock.Mock(stdout='100|0.001')):
                with self.assertRaisesRegex(ValueError, 'blank'):
                    module.inspect_image(image)
            synthetic_header(image, width=190, height=192)
            with self.assertRaisesRegex(ValueError, 'plausible'):
                module.inspect_image(image)
            image.write_bytes(b'not a png' + b'x'*130)
            with self.assertRaisesRegex(ValueError, 'Expected real PNG'):
                module.inspect_image(image)
            image.unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                module.inspect_image(image)

    def test_changing_dimensions_rejected_and_repeated_images_marked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a,b=root/'first.png',root/'second.png'
            synthetic_header(a)
            synthetic_header(b)
            with mock.patch.object(module.subprocess, 'run',
                                   return_value=mock.Mock(stdout='80|0.34')):
                result=module.verify([a,b])
                self.assertEqual(result['distinct_frame_hashes'],1)
                with self.assertRaisesRegex(ValueError, 'At least two'):
                    module.verify([a])
                synthetic_header(b,width=512)
                with self.assertRaisesRegex(ValueError, 'dimensions'):
                    module.verify([a,b])


if __name__ == '__main__':
    unittest.main()
