# escriptorium-engine-tesseract

Tesseract as an eScriptorium engine. Installing this package is the entire integration — the
`escriptorium.engines` entry point in `pyproject.toml` is what makes the engine appear.

## Install

This is a plugin: it installs *into* an eScriptorium environment.

### Expected in the environment

pip installs `pytesseract` and Pillow. Everything else has to be there already:

- eScriptorium **with the engine layer**, i.e. the `feature/engine-layer-upstream` branch of
  [gitlab.com/adibender-gitlab/escriptorium](https://gitlab.com/adibender-gitlab/escriptorium/-/tree/feature/engine-layer-upstream).
  That is where the contract this package imports (`engines.base`) lives; upstream eScriptorium does
  not read the `escriptorium.engines` entry point group yet, so the engine would install there but
  never appear. The same applies to the image you build on: use one built from that branch.
- Python ≥ 3.10.
- the **tesseract binary** (`tesseract-ocr`) on the `PATH`.
- at least one **language file** (`.traineddata`), e.g. `tesseract-ocr-eng`, `-deu`, `-frk`.
  These are also what you upload as models (see *Use*).

pip can provide neither the binary nor the language files.

### With Docker (recommended)

The provided image layers the binary, the language files and this package onto eScriptorium's own:

```sh
docker build --build-arg ESCRIPTORIUM_IMAGE=<an eScriptorium image with the engine layer> \
             -t escriptorium-tesseract:latest .
```

Then point the app containers at the image.

### With pip, from GitHub

Inside an eScriptorium environment that already has everything listed above:

```sh
pip install "git+https://github.com/adibender/escriptorium-engine-tesseract"
```

Append `@<commit>` or `@<tag>` to the URL to pin a version.

Without Docker, install the system packages first, e.g. on Debian/Ubuntu:

```sh
apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-frk
```

From a local checkout, `pip install -e .` does the same.

### Restart

**Restart every app container after installing**, including the celery workers (`web`,
`celery-main`, `celery-gpu`, `celery-intensive-inference`). Entry points are read when a process
starts, so a container that is already running never notices a newly installed engine. The same
holds after upgrading or uninstalling the package.

### Verify

`GET /api/engines/` lists `tesseract`, and *Tesseract* appears as an engine in the Segment dialog.

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
