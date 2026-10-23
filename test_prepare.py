import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from prepare import prepare


class PreparationTests(unittest.TestCase):
    def test_dry_run_apply_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source, target = root / "export", root / "projects"
            stack = source / "demo"
            stack.mkdir(parents=True)
            (stack / "docker-compose.yml").write_text("services: {}\n")
            secret = b"PASSWORD='a$#b'\n"
            (stack / ".env").write_bytes(secret)
            with contextlib.redirect_stdout(io.StringIO()):
                prepare(source, target, ["demo"])
                self.assertFalse(target.exists())
                prepare(source, target, ["demo"], True)
                self.assertEqual((target / "demo/.env").read_bytes(), secret + b"\nCOMPOSE_PROJECT_NAME=demo\n")
                (target / "demo/compose.yaml").write_text("sentinel")
                prepare(source, target, ["demo"], True)
                self.assertEqual((target / "demo/compose.yaml").read_text(), "sentinel")

    def test_rejects_traversal(self):
        with self.assertRaises(ValueError):
            prepare("exports", "projects", ["../escape"])

    def test_conflicting_identity_writes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            stack = root / "exports/demo"
            stack.mkdir(parents=True)
            (stack / "docker-compose.yml").write_text("services: {}")
            (stack / ".env").write_text("COMPOSE_PROJECT_NAME=other\n")
            with self.assertRaises(ValueError):
                prepare(root / "exports", root / "projects", ["demo"], True)
            self.assertFalse((root / "projects").exists())


if __name__ == "__main__":
    unittest.main()
