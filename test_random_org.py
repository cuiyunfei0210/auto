#!/usr/bin/env python3
import io
import unittest
from unittest.mock import patch

import random_org


class ValidateRangeTests(unittest.TestCase):
    def test_accepts_valid_range(self):
        random_org.validate_range(3, 1, 10, unique=False)

    def test_rejects_min_greater_than_max(self):
        with self.assertRaises(random_org.RandomOrgError):
            random_org.validate_range(1, 10, 1, unique=False)

    def test_rejects_unique_overflow(self):
        with self.assertRaises(random_org.RandomOrgError):
            random_org.validate_range(5, 1, 3, unique=True)


class ParseNumbersTests(unittest.TestCase):
    def test_parses_newlines_and_spaces(self):
        self.assertEqual(random_org.parse_numbers("1\n2\n3\n"), [1, 2, 3])
        self.assertEqual(random_org.parse_numbers("10\t20\n"), [10, 20])


class GenerateIntegersTests(unittest.TestCase):
    @patch("random_org.remaining_quota_bits", return_value=100000)
    @patch("random_org._get", return_value="7\n8\n9\n")
    def test_integers_request(self, mock_get, _quota):
        result = random_org.generate_integers(3, 1, 20, unique=False)
        self.assertEqual(result, [7, 8, 9])
        url, params = mock_get.call_args.args
        self.assertEqual(url, random_org.INTEGERS_URL)
        self.assertEqual(params["num"], "3")
        self.assertEqual(params["min"], "1")
        self.assertEqual(params["max"], "20")
        self.assertEqual(params["rnd"], "new")

    @patch("random_org.remaining_quota_bits", return_value=100000)
    @patch("random_org._get", return_value="5\n4\n3\n2\n1\n")
    def test_unique_uses_sequence_prefix(self, mock_get, _quota):
        result = random_org.generate_integers(3, 1, 5, unique=True)
        self.assertEqual(result, [5, 4, 3])
        url, params = mock_get.call_args.args
        self.assertEqual(url, random_org.SEQUENCES_URL)
        self.assertEqual(params["min"], "1")
        self.assertEqual(params["max"], "5")

    @patch("random_org.remaining_quota_bits", return_value=-1)
    def test_exhausted_quota(self, _quota):
        with self.assertRaises(random_org.RandomOrgError):
            random_org.generate_integers(1, 1, 6, unique=False)


class CliTests(unittest.TestCase):
    @patch("random_org.generate_integers", return_value=[11, 22])
    def test_cli_flags(self, mock_generate):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = random_org.main(["--num", "2", "--min", "1", "--max", "100"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), "11\n22\n")
        mock_generate.assert_called_once_with(2, 1, 100, unique=False)

    @patch("random_org.remaining_quota_bits", return_value=4242)
    def test_cli_quota(self, _quota):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = random_org.main(["--quota"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), "4242\n")


if __name__ == "__main__":
    unittest.main()
