# Setup

Use Python 3.11 and start in the folder containing `TROJAN_CHALLENGE.ipynb`.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m jupyter lab TROJAN_CHALLENGE.ipynb
```

On Windows, activate with `.venv\Scripts\activate`. Select this environment's
kernel and run notebook cells from top to bottom. Keep `cases.json`, the helper
module and the `challenges/` directory alongside the notebook.

The requirements are copied from the existing project. No model downloads,
credentials or hardware access are needed. An ideal local simulator
is sufficient. You do not need a device noise model.

Use the supplied 8,192-shot counts for the shared evidence. Simulating large
dynamic circuits may require substantial CPU time and memory. Optional notebook
simulations are disabled initially and use a small shot count when enabled.
