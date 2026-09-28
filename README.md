# escriptorium-engine-tesseract

Tesseract as an eScriptorium engine. Installing this package is the entire integration — the
`escriptorium.engines` entry point in `pyproject.toml` is what makes the engine appear.

## Install

This is a plugin: it installs *into* an eScriptorium environment, and it needs the tesseract binary
and at least one language file alongside it — neither of which pip can provide. The provided image
layers all three onto eScriptorium's own:

```sh
# ESCRIPTORIUM_IMAGE defaults to registry.gitlab.com/scripta/escriptorium:latest
docker build -t escriptorium-tesseract:latest .
```

By hand, inside an existing eScriptorium environment, it is:

```sh
apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-frk
pip install -e .
```

Point the app containers at the image, then **restart them**. Entry points are read when a process
starts, so a container that is already running never notices a newly installed engine.

Verify: `GET /api/engines/` lists `tesseract`, and *Tesseract* appears as an engine in the Segment
dialog.

## Use

1. **Add a model.** A "model" for this engine is a `.traineddata` language file. Upload one through
   eScriptorium's normal model upload — it is attributed to tesseract automatically, because kraken
   cannot read the file and tesseract can.
2. **Segment**, choosing *Tesseract* as the engine to use its own layout analysis, or segment with
   kraken and use tesseract for recognition only.
3. **Transcribe** with the uploaded language model. The model carries its engine, so nothing else
   has to be selected.

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
