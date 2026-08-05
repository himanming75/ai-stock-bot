from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from deployment.windows_tasks import (
    build_default_tasks,
    export_task_xml,
)


class Tests(unittest.TestCase):
    def test_default_tasks_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks = build_default_tasks(Path(directory))
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(task.enabled is False for task in tasks))

    def test_zero_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks = build_default_tasks(Path(directory))
        self.assertTrue(all(task.restart_count == 0 for task in tasks))

    def test_xml_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = export_task_xml(root, root / "xml")
            self.assertEqual(len(values), 3)
            for value in values:
                self.assertTrue(Path(value["path"]).exists())

    def test_xml_contains_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            task = build_default_tasks(Path(directory))[0]
            xml = task.to_xml()
        self.assertIn("<Enabled>false</Enabled>", xml)

    def test_future_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            task = build_default_tasks(Path(directory))[0]
        self.assertTrue(task.start_boundary.startswith("2099-"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
