from io import StringIO
from pathlib import Path
from unittest import TestCase


class TestGenerateGen(TestCase):
    def test_up_to_date(self) -> None:
        from ..generate_gen import generate_gen  # TODO: skip if this doesn't exist

        new_f = StringIO()
        generate_gen(new_f)
        new_data = new_f.getvalue().encode("utf-8")

        current_file_path = Path(__file__).parent.parent / "gen.py"
        with open(current_file_path, "rb") as old_f:
            self.assertEqual(new_data, old_f.read())
