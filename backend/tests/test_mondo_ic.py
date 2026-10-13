"""IC-based MONDO similarity against the bundled OBO.

Run from ``backend/``: ``python3 -m unittest discover -s tests -v``
"""

import math
import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from lib.mondo import (  # noqa: E402
    DEFAULT_IC_ROOT, IC_METHODS, build_ic_table, information_content, load_mondo_index, mondo_similarity,
)

KABUKI = "MONDO:0016512"
KABUKI_1 = "MONDO:0007843"
KABUKI_2 = "MONDO:0010465"
WILLIAMS = "MONDO:0008678"
GENETIC_MECHANISM = "MONDO:7770009"  # disease of genetic or genomic mechanism
SYNDROMIC = "MONDO:0002254"  # syndromic disease

PAIRS = [
    (WILLIAMS, WILLIAMS),
    (KABUKI, KABUKI_1),
    (KABUKI_1, WILLIAMS),
    (KABUKI_1, KABUKI_2),
    ("MONDO:0007336", "MONDO:0016064"),
    (WILLIAMS, "MONDO:0019040"),
    (WILLIAMS, "MONDO:0008608"),
    (WILLIAMS, "MONDO:0007336"),
    ("MONDO:0007525", DEFAULT_IC_ROOT),
]


class MondoIcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index, _ = load_mondo_index(os.path.join(BACKEND_DIR, "mondo", "mondo-international.obo.gz"))
        cls.table = build_ic_table(cls.index)

    def sim(self, a, b, method="seco"):
        return mondo_similarity(self.index, self.table, a, b, method)

    def test_ic_bounds(self):
        n = self.table["n_terms"]
        self.assertEqual(information_content(self.table, DEFAULT_IC_ROOT, "descendants"), 0.0)
        self.assertAlmostEqual(information_content(self.table, WILLIAMS, "descendants"), math.log(n))
        self.assertEqual(information_content(self.table, DEFAULT_IC_ROOT, "seco"), 0.0)
        self.assertAlmostEqual(information_content(self.table, WILLIAMS, "seco"), 1.0)

    def test_same_term(self):
        for method in IC_METHODS:
            result = self.sim(WILLIAMS, WILLIAMS, method)
            self.assertEqual(result["lin"], 1.0)
            self.assertEqual(result["mica"]["id"], WILLIAMS)
            self.assertEqual(result["mica"]["hops"], [0, 0])

    def test_kabuki_and_kabuki_1(self):
        result = self.sim(KABUKI, KABUKI_1)
        self.assertEqual([t["id"] for t in result["mica_ties"]], [KABUKI])
        self.assertEqual(result["resnik"], information_content(self.table, KABUKI))
        self.assertGreaterEqual(result["lin"], 0.9)
        self.assertEqual(self.sim(KABUKI_1, KABUKI)["mica"]["hops"], [1, 0])

    def test_kabuki_1_and_kabuki_2(self):
        result = self.sim(KABUKI_1, KABUKI_2)
        self.assertEqual(result["mica"]["id"], KABUKI)
        self.assertEqual(result["mica"]["hops"], [1, 1])

    def test_kabuki_1_and_williams(self):
        result = self.sim(KABUKI_1, WILLIAMS)
        expected = max((GENETIC_MECHANISM, SYNDROMIC), key=lambda t: information_content(self.table, t))
        self.assertEqual(result["mica"]["id"], expected)
        self.assertIn(expected, [t["id"] for t in result["common_ancestors"]])
        self.assertLess(result["lin"], 0.3)

    def test_symmetry(self):
        for method in IC_METHODS:
            for a, b in PAIRS:
                with self.subTest(method=method, a=a, b=b):
                    forward, backward = self.sim(a, b, method), self.sim(b, a, method)
                    for key in ("resnik", "lin"):
                        self.assertEqual(forward[key], backward[key])
                    self.assertEqual([t["id"] for t in forward["mica_ties"]], [t["id"] for t in backward["mica_ties"]])
                    self.assertEqual(forward["mica"]["hops"], backward["mica"]["hops"][::-1])

    def test_lin_range(self):
        for method in IC_METHODS:
            for a, b in PAIRS:
                with self.subTest(method=method, a=a, b=b):
                    lin = self.sim(a, b, method)["lin"]
                    self.assertIsNotNone(lin)
                    self.assertGreaterEqual(lin, 0.0)
                    self.assertLessEqual(lin, 1.0)

    def test_out_of_scope(self):
        result = self.sim("MONDO:0000001", WILLIAMS)
        self.assertEqual({k: result[k] for k in ("mica", "mica_ties", "resnik", "lin")},
                         {"mica": None, "mica_ties": [], "resnik": None, "lin": None})
        self.assertEqual([(t["id"], t["ic"], t["hops"]) for t in result["common_ancestors"]],
                         [("MONDO:0000001", None, [0, 4])])
        self.assertIsNone(information_content(self.table, "MONDO:0000001"))


if __name__ == "__main__":
    unittest.main()
