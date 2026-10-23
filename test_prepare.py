import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from prepare import prepare, select_projects


class PreparationTests(unittest.TestCase):
    def test_bulk_selection_excludes_git_and_missing_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            for name, metadata in [("app", '{}'), ("excluded", '{}'),
                                   ("git", '{"GitConfig":{"URL":"https://example.com/repo"}}'),
                                   ("unknown", None)]:
                folder = root / name
                folder.mkdir()
                (folder / "docker-compose.yml").write_text("services: {}")
                if metadata is not None:
                    (folder / "stack_metadata.json").write_text(metadata)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                chosen = select_projects(root, all_projects=True, exclude=["excluded"])
            self.assertEqual(chosen, ["app"])
            self.assertIn("Git-backed", output.getvalue())
            self.assertIn("metadata missing", output.getvalue())
            self.assertNotIn("https://example.com", output.getvalue())
            with self.assertRaises(ValueError):
                select_projects(root, all_projects=True, exclude=["typo"])

    def test_invalid_bulk_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "app"
            folder.mkdir()
            (folder / "stack_metadata.json").write_text("not json")
            with self.assertRaises(ValueError):
                select_projects(root, all_projects=True)

    def test_exclude_requires_all(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                select_projects(root, ["app"], exclude=["app"])

    def test_explicit_git_selection_warns(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "git"
            folder.mkdir()
            (folder / "stack_metadata.json").write_text('{"GitConfig":{"URL":"secret"}}')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                chosen = select_projects(root, ["git"])
            self.assertEqual(chosen, ["git"])
            self.assertIn("WARNING", output.getvalue())
            self.assertNotIn("secret", output.getvalue())

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
