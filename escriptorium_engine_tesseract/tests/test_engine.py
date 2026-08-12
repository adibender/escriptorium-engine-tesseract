"""Conformance for the tesseract engine.

The point of this file: the contract lives in eScriptorium, the engine lives here, and the engine
proves itself by importing that contract rather than by us reasoning about it.
"""
import glob
import unittest
from types import SimpleNamespace

from engines.conformance import EngineConformanceMixin

from escriptorium_engine_tesseract import TesseractEngine


def _system_language_file(language="eng"):
    """Path to an installed .traineddata, or None if tesseract has no languages here."""
    for pattern in (
        f"/usr/share/tesseract-ocr/*/tessdata/{language}.traineddata",
        f"/usr/share/tessdata/{language}.traineddata",
    ):
        found = sorted(glob.glob(pattern))
        if found:
            return found[0]
    return None


class TesseractConformanceTests(EngineConformanceMixin, unittest.TestCase):
    engine_class = TesseractEngine

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = _system_language_file()
        # the engine only ever touches model.file.path, so a stand-in is enough and this test
        # needs no database
        cls.recognition_model = SimpleNamespace(file=SimpleNamespace(path=path)) if path else None
        cls.can_run_inference = bool(path)


class TesseractSpecificTests(unittest.TestCase):
    def test_language_is_taken_from_the_model_filename(self):
        model = SimpleNamespace(file=SimpleNamespace(path="/models/ab/deu.traineddata"))
        language, tessdata = TesseractEngine._language_and_tessdata(model)
        self.assertEqual(language, "deu")
        self.assertEqual(tessdata, "/models/ab")

    def test_no_model_falls_back_to_a_default_language(self):
        language, tessdata = TesseractEngine._language_and_tessdata(None)
        self.assertTrue(language)
        self.assertIsNone(tessdata)

    def test_baseline_position_follows_the_line_offset_preference(self):
        bottom = TesseractEngine._baseline_for_box(100, 20, 0, 50, topline=False)
        middle = TesseractEngine._baseline_for_box(100, 20, 0, 50, topline=None)
        top = TesseractEngine._baseline_for_box(100, 20, 0, 50, topline=True)
        self.assertEqual([point[1] for point in bottom], [120, 120])
        self.assertEqual([point[1] for point in middle], [110, 110])
        self.assertEqual([point[1] for point in top], [100, 100])

    def test_validate_model_rejects_a_kraken_model(self):
        from engines.base import ModelValidationError

        with self.assertRaises(ModelValidationError):
            TesseractEngine().validate_model("/models/ab/german_print.mlmodel")

    @unittest.skipIf(_system_language_file() is None, "no tesseract languages installed")
    def test_validate_model_accepts_an_installed_language(self):
        info = TesseractEngine().validate_model(_system_language_file())
        self.assertEqual(info.job, "recognition")
        self.assertEqual(info.architecture, "Tesseract")
