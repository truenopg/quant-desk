# Install

Clone with submodules (the backtest engine lives in a linked repo):

    git clone --recurse-submodules https://github.com/truenopg/quant-desk.git
    cd quant-desk
    # already cloned without the flag? -> git submodule update --init


Needs Python 3.10+ and about 4 GB of free RAM when the local model runs.
Disk: ~2.5 GB with CPU-only torch (deps ~1.2 GB, model ~1 GB on first model run). On Linux pip pulls the CUDA build of torch by default (~3 GB more); the CPU index line below avoids that.

## Linux

    sudo apt install python3 python3-venv   # or your distro's equivalent
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    # CPU-only torch is smaller; if pip pulls the CUDA build by default:
    # pip install torch --index-url https://download.pytorch.org/whl/cpu

## macOS

    brew install python@3.12                # or python.org installer
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt

## Windows

    # install Python 3.10+ from python.org (tick "Add python.exe to PATH")
    py -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    # CPU-only torch if needed:
    # pip install torch --index-url https://download.pytorch.org/whl/cpu

## Run

    python -m desk.fetch          # download daily BTC + gold data (free public APIs)
    python -m desk.cycle --seed 42        # deterministic cycle, no model
    python -m desk.model_cycle --seed 7   # cycle with the local model
                                          # (downloads ~1 GB from HuggingFace
                                          #  the first time, then cached)
    python -m desk.report                 # figures + report for the last run
    python -m unittest discover -s tests  # test suite

The model cycle runs on CPU: a few seconds per model call. No API keys,
no accounts, no cost. If you already run Ollama, `--backend ollama`
uses it instead of the in-process model.

Measured on a small cloud VM (2 cores, 1 GB RAM - below recommended):
model download 1.0 GB, one full model cycle (2 assets, 4 hypotheses)
~3-4 minutes. Your numbers will differ; these are a floor, not a promise.
