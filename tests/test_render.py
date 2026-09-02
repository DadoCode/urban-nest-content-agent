import unittest

import render


class TestFitTextToBox(unittest.TestCase):
    def test_short_text_fits_without_truncation(self):
        font, lines, truncated = render.fit_text_to_box(
            "Short hook.", max_width=900, max_lines=3, font_fn=render._serif, start_size=80, min_size=40
        )
        self.assertFalse(truncated)
        self.assertLessEqual(len(lines), 3)

    def test_never_exceeds_max_lines(self):
        long_text = " ".join(["word"] * 60)
        font, lines, truncated = render.fit_text_to_box(
            long_text, max_width=400, max_lines=2, font_fn=render._sans, start_size=60, min_size=20
        )
        self.assertLessEqual(len(lines), 2)

    def test_truncation_adds_ellipsis(self):
        long_text = " ".join(["unbreakableword"] * 40)
        font, lines, truncated = render.fit_text_to_box(
            long_text, max_width=300, max_lines=1, font_fn=render._sans, start_size=40, min_size=38
        )
        if truncated:
            self.assertTrue(lines[-1].endswith("…"))


if __name__ == "__main__":
    unittest.main()
