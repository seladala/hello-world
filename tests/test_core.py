import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.runtime import Machine, assemble
from core.modules import DependencyError, Version, resolve, satisfies
from core.modules.graph import Component
from core.numerics import high_precision, series, streaming
from core.diagnostics.arithmetic import peano_length, to_int

ROOT = Path(__file__).resolve().parent.parent


class EndToEndTest(unittest.TestCase):
    def test_prints_hello_world(self):
        result = subprocess.run([sys.executable, "main.py"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "hello world\n")

    def test_main_is_exactly_67000_lines(self):
        with open(ROOT / "main.py", encoding="utf-8") as f:
            self.assertEqual(sum(1 for _ in f), 67_000)


class SecurityTest(unittest.TestCase):
    def _run_tampered(self, relative_path, old, new, refresh_checksums=False):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(ROOT / "main.py", tmp)
            shutil.copytree(ROOT / "core", Path(tmp) / "core", ignore=shutil.ignore_patterns("__pycache__"))
            target = Path(tmp) / relative_path
            target.write_text(target.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
            if refresh_checksums:
                subprocess.run([sys.executable, "-c",
                                "from core.security.integrity import compute_manifest, CHECKSUMS;"
                                "CHECKSUMS.write_text(''.join(f'{d}  {n}\\n' for n, d in compute_manifest().items()))"],
                               cwd=tmp, check=True)
            return subprocess.run([sys.executable, "main.py"], cwd=tmp, capture_output=True, text=True)

    def test_modified_file_is_rejected(self):
        result = self._run_tampered("core/settings.ini", "case = lower", "case = UPPER")
        self.assertEqual(result.returncode, 3)
        self.assertIn("modified: core/settings.ini", result.stderr)

    def test_forged_license_is_rejected(self):
        result = self._run_tampered("core/security/license.dat", '"Everyone"', '"Pirate"', refresh_checksums=True)
        self.assertEqual(result.returncode, 3)
        self.assertIn("license signature invalid", result.stderr)

    def test_debugger_is_detected(self):
        code = ("import runpy, sys; sys.settrace(lambda *a: None); sys.argv = ['main.py'];"
                "runpy.run_path('main.py', run_name='__main__')")
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 3)
        self.assertIn("debugger", result.stderr)


class CpuTest(unittest.TestCase):
    def test_arithmetic_and_flags(self):
        program = assemble("""
            MOVI R0, 5
            MOVI R1, 7
            ADD  R0, R1
            CMPI R0, 12
            JZ   ok
            HLT
        ok: MOVI R2, 1
            OUT  0x01, R2
            HLT
        """)
        machine = Machine()
        machine.load(program.image)
        out = []
        machine.attach_output(1, out.append)
        machine.run()
        self.assertEqual(out, [1])
        self.assertEqual(machine.registers[0], 12)


class PiTest(unittest.TestCase):
    def test_all_algorithms_agree(self):
        digits = high_precision.pi_digits(500)
        self.assertTrue(digits.startswith("31415926535897932384626433"))
        self.assertEqual(digits, series.pi_digits(500))
        self.assertEqual(digits, streaming.pi_digits(500))


class DependencyTest(unittest.TestCase):
    def test_semver(self):
        self.assertTrue(satisfies(Version("3.14.15"), ">=3.14,<4"))
        self.assertTrue(satisfies(Version("2.3.9"), "~2.3"))
        self.assertFalse(satisfies(Version("3.1.4"), ">=3.14"))

    def test_cycle_detected(self):
        a = Component("a", Version("1.0.0"), "x:y", {"b": ">=1"})
        b = Component("b", Version("1.0.0"), "x:y", {"a": ">=1"})
        with self.assertRaises(DependencyError):
            resolve({"a": a, "b": b})


class PeanoTest(unittest.TestCase):
    def test_length(self):
        self.assertEqual(to_int(peano_length("hello world")), 11)


if __name__ == "__main__":
    unittest.main()
