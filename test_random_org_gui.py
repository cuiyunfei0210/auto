#!/usr/bin/env python3
import unittest

from random_org_form import FormError, parse_inputs


class ParseInputsTests(unittest.TestCase):
    def test_parses_integers(self):
        self.assertEqual(parse_inputs("5", "1", "100"), (5, 1, 100))

    def test_rejects_non_integers(self):
        with self.assertRaises(FormError):
            parse_inputs("x", "1", "10")

    def test_rejects_min_greater_than_max(self):
        with self.assertRaises(FormError):
            parse_inputs("1", "10", "1")

    def test_rejects_unique_overflow(self):
        with self.assertRaises(FormError):
            parse_inputs("5", "1", "3", unique=True)


if __name__ == "__main__":
    unittest.main()
