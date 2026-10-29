import subprocess
import sys
import unittest
from pathlib import Path

from ultimate_hello.cpu import Machine, assemble
from ultimate_hello.deps import DependencyError, Version, resolve, satisfies
from ultimate_hello.deps.resolver import Component
from ultimate_hello.pi import chudnovsky, machin, spigot
from ultimate_hello.useless.peano import peano_length, to_int

ROOT = Path(__file__).resolve().parent.parent


class EndToEndTest(unittest.TestCase):
    def test_prints_hello_world(self):
        result = subprocess.run([sys.executable, "main.py"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "hello world\n")

    def test_main_is_exactly_67000_lines(self):
        with open(ROOT / "main.py", encoding="utf-8") as f:
            self.assertEqual(sum(1 for _ in f), 67_000)


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
        digits = chudnovsky.pi_digits(500)
        self.assertTrue(digits.startswith("31415926535897932384626433"))
        self.assertEqual(digits, machin.pi_digits(500))
        self.assertEqual(digits, spigot.pi_digits(500))


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
