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

## Relationship to eScriptorium

This is a plugin, not a standalone library: it imports the engine contract (`engines.base`) from
eScriptorium and installs into an eScriptorium environment, which is also the only place it can run.
That is why `pyproject.toml` declares no dependency on eScriptorium — eScriptorium is deployed as an
application, not published as a distribution.

The practical consequence is the one noted under *Tests*: the suite needs an eScriptorium checkout on
the path. If third-party engines should one day be developed and tested on their own, the way there
is to extract the interface into a small distribution that both sides depend on — a change we would
be glad to contribute rather than expect.
