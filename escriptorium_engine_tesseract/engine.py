"""Tesseract engine for eScriptorium.

Tesseract is deliberately the first non-kraken engine, because it agrees with kraken about almost
nothing:

- it brings its own layout analysis, so it segments as well as recognises;
- it reports **bounding boxes**, not baselines, and eScriptorium is baseline-native;
- it has no torch weights at all -- a "model" is a `.traineddata` language file;
- it reports confidence per *word*, never per character.

That last point is why `RecognitionResult.graphemes` is None here rather than an empty tuple: this
engine has no character-level data to give, which is a different statement from "this line is empty".

None of the above required a change inside eScriptorium. If it ever does, the engine layer is not
finished.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Iterator

import pytesseract
from pytesseract import Output

from engines.base import (
    SOURCE_FILE,
    BaseEngine,
    EngineError,
    EngineSpec,
    Line,
    LineInput,
    ModelInfo,
    ModelValidationError,
    RecognitionResult,
    RecognizeOptions,
    Region,
    SegmentationResult,
    SegmentOptions,
)
from engines.imaging import line_box

logger = logging.getLogger(__name__)

#: tesseract's `image_to_data` level codes
LEVEL_BLOCK = 2
LEVEL_LINE = 4

#: language used when no model is supplied (segmentation still needs one)
DEFAULT_LANGUAGE = "eng"

#: psm 7 = "treat the image as a single text line", which is what recognition is handed
SINGLE_LINE_PSM = "--psm 7"


class TesseractEngine(BaseEngine):
    spec = EngineSpec(
        name="tesseract",
        label="Tesseract",
        can_segment=True,
        can_recognize=True,
        can_train=False,          # ketos-style fine-tuning is out of scope; declaring it would lie
        model_sources=(SOURCE_FILE,),
        file_extensions=("traineddata",),
        has_default_segmenter=True,
    )

    # --- model handling

    @staticmethod
    def _language_and_tessdata(model):
        """A tesseract "model" is a language file; derive `-l` and `--tessdata-dir` from its path.

        eScriptorium slugifies uploads, so `deu.traineddata` stays `deu.traineddata` and the stem is
        usable as the language code.
        """
        if model is None or not getattr(model, "file", None):
            return DEFAULT_LANGUAGE, None
        path = model.file.path
        return os.path.splitext(os.path.basename(path))[0], os.path.dirname(path)

    @classmethod
    def _config(cls, tessdata_dir, *extra):
        parts = list(extra)
        if tessdata_dir:
            parts.append(f'--tessdata-dir "{tessdata_dir}"')
        return " ".join(parts)

    def validate_model(self, path: str) -> ModelInfo:
        if not str(path).endswith(".traineddata"):
            raise ModelValidationError("Not a tesseract .traineddata file.")
        if not os.path.exists(path):
            raise ModelValidationError("File not found.")
        # tesseract traineddata files are TessDatafile archives; the cheapest real check is asking
        # tesseract to list the languages it can see once this file is on the path
        directory = os.path.dirname(path) or "."
        language = os.path.splitext(os.path.basename(path))[0]
        try:
            available = pytesseract.get_languages(config=f'--tessdata-dir "{directory}"')
        except Exception as exc:
            raise ModelValidationError(f"tesseract could not read the tessdata directory: {exc}")
        if language not in available:
            raise ModelValidationError(
                f"tesseract does not recognise {language!r} as a language in {directory}."
            )
        return ModelInfo(job="recognition", architecture="Tesseract", seg_type="bbox")

    # --- segmentation

    def segment(self, image, *, model=None, options: SegmentOptions) -> SegmentationResult:
        language, tessdata_dir = self._language_and_tessdata(model)
        data = pytesseract.image_to_data(
            image,
            lang=language,
            config=self._config(tessdata_dir),
            output_type=Output.DICT,
        )

        regions: list[Region] = []
        lines: list[Line] = []

        for index, level in enumerate(data["level"]):
            left = data["left"][index]
            top = data["top"][index]
            width = data["width"][index]
            height = data["height"][index]
            if width <= 0 or height <= 0:
                continue

            box = [
                [left, top],
                [left + width, top],
                [left + width, top + height],
                [left, top + height],
            ]

            if level == LEVEL_BLOCK and options.steps in ("regions", "both"):
                regions.append(Region(boundary=box, typology="TextRegion"))
            elif level == LEVEL_LINE and options.steps in ("lines", "both"):
                lines.append(
                    Line(
                        baseline=self._baseline_for_box(top, height, left, width, options.topline),
                        boundary=box,
                        typology=None,
                    )
                )

        return SegmentationResult(lines=tuple(lines), regions=tuple(regions))

    @staticmethod
    def _baseline_for_box(top, height, left, width, topline):
        """Turn a box into the baseline eScriptorium expects.

        `topline` mirrors the document's line_offset preference: True puts the line along the top of
        the glyphs, None through the middle, False (the default) along the bottom.
        """
        if topline is True:
            y = top
        elif topline is None:
            y = top + height / 2
        else:
            y = top + height
        return [[left, y], [left + width, y]]

    # --- recognition

    def recognize(
        self, image, lines: Iterable[LineInput], *, model, options: RecognizeOptions
    ) -> Iterator[RecognitionResult]:
        language, tessdata_dir = self._language_and_tessdata(model)
        self._require_language(language, tessdata_dir)
        config = self._config(tessdata_dir, SINGLE_LINE_PSM)

        for line in lines:
            box = line_box(line, image.size)
            if box is None:
                continue

            crop = image.crop(box)
            try:
                text = pytesseract.image_to_string(crop, lang=language, config=config)
            except Exception:
                logger.exception("tesseract failed on line %s", line.id)
                continue

            yield RecognitionResult(
                line_id=line.id,
                text=text.strip(),
                # word-level confidence only, so there is nothing honest to report per character
                graphemes=None,
            )

    @classmethod
    def _require_language(cls, language, tessdata_dir):
        """Fail the request, not every line.

        Without this a missing language fails each line separately, every failure is skipped as an
        unreadable line, and the task reports success with an empty transcription.
        """
        try:
            available = pytesseract.get_languages(config=cls._config(tessdata_dir))
        except Exception as exc:
            raise EngineError(f"tesseract could not list its languages: {exc}") from exc
        if language not in available:
            where = f" in {tessdata_dir}" if tessdata_dir else ""
            raise EngineError(f"tesseract has no language {language!r}{where}.")
