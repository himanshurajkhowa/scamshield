"""Compare runtime outputs with approved source, without executing training."""

import subprocess
import sys
import types
import unittest
from itertools import product
from pathlib import Path

from ml.inference import analyze
from ml import urls

BASELINE = "9d6c339f0c7613e616dda5c297104e32814edfe9"
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "_scamshield_parity_baseline"


class DifferentialParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            subprocess.run(
                ["git", "cat-file", "-e", f"{BASELINE}^{{commit}}"],
                cwd=ROOT, check=True, capture_output=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise unittest.SkipTest(
                "Historical baseline unavailable; frozen-fixture tests still run."
            )
        package = types.ModuleType(PACKAGE)
        package.__path__ = []
        sys.modules[PACKAGE] = package
        cls.modules = {}
        for name in ("urls", "rules", "inference"):
            source = subprocess.check_output(
                ["git", "show", f"{BASELINE}:ml/{name}.py"],
                cwd=ROOT, text=True,
            )
            module = types.ModuleType(f"{PACKAGE}.{name}")
            module.__package__ = PACKAGE
            # The baseline loads exactly the same unchanged local model artifact.
            module.__file__ = str(ROOT / "ml" / f"{name}.py")
            sys.modules[module.__name__] = module
            exec(compile(source, module.__file__, "exec"), module.__dict__)
            cls.modules[name] = module

    @classmethod
    def tearDownClass(cls):
        cls.modules["inference"].get_model.cache_clear()
        for name in ("urls", "rules", "inference"):
            sys.modules.pop(f"{PACKAGE}.{name}", None)
        sys.modules.pop(PACKAGE, None)

    def test_regex_and_host_reference_constants_are_identical(self):
        before = self.modules["urls"]
        for name in (
            "CHALLAN_HOSTS", "REFERENCE_HOSTS", "TOKENS", "SCHEME", "BARE",
            "CONFUSABLES",
        ):
            with self.subTest(constant=name):
                self.assertEqual(getattr(urls, name), getattr(before, name))
        for name in ("URL_RE", "CLAIM_RE"):
            self.assertEqual(getattr(urls, name).pattern, getattr(before, name).pattern)
            self.assertEqual(getattr(urls, name).flags, getattr(before, name).flags)

    def test_300_url_and_message_combinations_match_all_fields(self):
        hosts = (
            "echallan.parivahan.gov.in", "echallan.parivahan.nic.in",
            "echallan.parivahan.gov.in.evil.example", "evil.example",
            "gov.in.evil.example", "parivahann.example", "192.0.2.10",
            "[2001:db8::1]", "xn--e1afmkfd.example", "example.xyz",
        )
        paths = ("/", "/pay", "/receipt%2Eapk", "/file?amount=10", "/status#receipt")
        before = self.modules["inference"].analyze
        for scheme, host, path, prefix in product(
            ("https", "http", "ftp"), hosts, paths,
            ("", "Your RTO challan payment is pending. Pay at "),
        ):
            text = f"{prefix}{scheme}://{host}{path}"
            with self.subTest(text=text):
                self.assertEqual(analyze(text), before(text))
