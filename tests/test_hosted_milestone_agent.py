"""Synthetic-only regressions for unattended agent PR source protections."""
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hosted_milestone_agent", ROOT / "tools" / "hosted_milestone_agent.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HostedMilestoneAgentGateTests(unittest.TestCase):
    def test_permitted_source_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            p = pathlib.Path(temp)
            (p / "source").mkdir()
            (p / "source" / "demo.c").write_text("int main(void){return 0;}\n")
            (p / "README.md").write_text("synthetic test\n")
            self.assertEqual(MODULE.validate_paths(
                ["source/demo.c", "README.md"], p), [])

    def test_forbidden_private_paths_and_agent_self_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            p = pathlib.Path(temp)
            for name in (
                ".github/workflows/agent.yml",
                "private/game.c",
                "assets/pokemon.png",
                "nitrofs/texture.p3px",
                "sd-card/photo.jpg",
                "tools/hosted_milestone_agent.py",
                "tests/test_hosted_milestone_agent.py",
                "source/payload.3ds",
                "source/../secret.c",
                ".env",
            ):
                with self.subTest(path=name):
                    self.assertTrue(MODULE.validate_paths([name], p))

    def test_rejects_symlinks_large_files_and_deletions(self):
        with tempfile.TemporaryDirectory() as temp:
            p = pathlib.Path(temp)
            (p / "source").mkdir()
            (p / "source" / "big.c").write_bytes(b"x" * (MODULE.MAX_CHANGED_BYTES + 1))
            self.assertTrue(MODULE.validate_paths(["source/big.c"], p))
            self.assertTrue(MODULE.validate_paths(["source/deleted.c"], p))
            (p / "source" / "link.c").symlink_to(p / "source" / "big.c")
            self.assertTrue(MODULE.validate_paths(["source/link.c"], p))

    def test_rejects_too_many_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            p = pathlib.Path(temp)
            (p / "source").mkdir()
            names = []
            for i in range(MODULE.MAX_CHANGED_FILES + 1):
                name = "source/%d.c" % i
                (p / name).write_text("int a;\n")
                names.append(name)
            self.assertTrue(MODULE.validate_paths(names, p))


if __name__ == "__main__":
    unittest.main()
