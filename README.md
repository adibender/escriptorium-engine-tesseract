# escriptorium-engine-tesseract

Tesseract as an eScriptorium engine. Installing this package is the entire integration — the
`escriptorium.engines` entry point in `pyproject.toml` is what makes the engine appear.

## Install

Needs the tesseract binary and at least one language file:

```sh
apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-frk
pip install -e .
```

Or build the provided image, which layers both onto eScriptorium's:

```sh
docker build -t escriptorium-tesseract:latest .
```

## Use

A "model" for this engine is a `.traineddata` language file. Upload one through eScriptorium's normal
model upload — it will be attributed to tesseract automatically, because kraken cannot read the file
and tesseract can.

## What it does and does not do

- segments (its own layout analysis) and recognises
- reports **bounding boxes**, converted to baselines using the document's line-offset preference
- reports confidence per *word*, so it returns no character-level data: `graphemes` is `None`, not
  an empty tuple. Those mean different things.
- cannot train. `can_train=False` is declared, so eScriptorium hides training for tesseract models.

Recognition crops the bounding box of each line's mask. On slanted or curved lines that drags in
slivers of the neighbours — inherent to handing a rectangle-oriented engine a baseline-oriented
segmentation, and the reason Fraktur newspapers segmented by kraken can read worse through tesseract
than tesseract's own segmentation would.

## Tests

```sh
python manage.py test escriptorium_engine_tesseract   # from an eScriptorium checkout
```

The suite is mostly eScriptorium's own `engines.conformance.EngineConformanceMixin`: the contract
lives there, so this package proves itself against it rather than against our reading of it.

## Known rough edge

The package imports `engines.base` from eScriptorium, which is not itself pip-installable, so it can
only be installed *into* an eScriptorium environment. Upstream should eventually publish the
interface as a tiny separate distribution so engines can declare a real dependency on it.
