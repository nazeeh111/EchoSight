# Exact raw-input reproduction

The original frozen runner requires commit `5d6423486be5fd448a4d7b42fbbaee264eb07c9c` and 74 supplemental files, including 48 preserved reference recordings. The [input inventory](audits/transfer-runtime-review/input-inventory.json) lists all 94 frozen inputs. The archive supplies 12,728,585 uncompressed bytes; the other 22 inputs are already in Git at that commit.

Optional private-repository asset: [calibration transfer evidence release](https://github.com/nazeeh111/EchoSight/releases/tag/calibration-transfer-2026-09-19).

- File: `transfer-5d64234-raw-inputs.tar.gz`
- Size: **4,445,857 bytes**
- SHA-256: **`45cc11286e8c3180da562c50b28336ac14b66ec7384f6e09d81cf5a20f138567`**

Use an account with repository access to download through GitHub or the authenticated `gh` CLI. No paid API or new backend dependency is needed. Start in a directory where `transfer-replay` does not exist:

```sh
git clone --branch backend/implementation https://github.com/nazeeh111/EchoSight.git transfer-replay
cd transfer-replay
git checkout --detach 5d6423486be5fd448a4d7b42fbbaee264eb07c9c
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p work/input-download
gh release download calibration-transfer-2026-09-19 --repo nazeeh111/EchoSight \
  --pattern transfer-5d64234-raw-inputs.tar.gz --dir work/input-download
python - <<'PY'
import hashlib
from pathlib import Path
p = Path('work/input-download/transfer-5d64234-raw-inputs.tar.gz')
assert p.stat().st_size == 4445857
assert hashlib.sha256(p.read_bytes()).hexdigest() == '45cc11286e8c3180da562c50b28336ac14b66ec7384f6e09d81cf5a20f138567'
PY
tar -xzf work/input-download/transfer-5d64234-raw-inputs.tar.gz
python work/calibration-room-transfer/run.py check
python work/calibration-room-transfer/run.py render --approved-freeze a995d28014c4c055003d34db193f5657a08d185a281d09ff1d7e667e5405da40
python work/calibration-room-transfer/run.py run --approved-freeze a995d28014c4c055003d34db193f5657a08d185a281d09ff1d7e667e5405da40
```

Stop if either checksum or `check` fails. The verified archive contains only regular files with safe relative `work/...` paths. It was extracted into a separate clean checkout and the original static check verified all 94 frozen hashes and 17 runtime modules. [Extraction receipt](audits/transfer-runtime-review/raw-extraction-verification.json), [static receipt](audits/transfer-runtime-review/raw-static-check-receipt.json). That packaging check did not repeat rendering or inference; the first full authorized execution is recorded separately in this evidence directory.

Do not invoke `freeze` or the historical `run_v2.py` as setup. The runner must remain at the stated path in a Git checkout containing the frozen commit. Rendering refuses an existing raw tree; running refuses an existing run receipt. Preserve failures and partial outputs and use a separate new checkout for any later reproduction. Expected scientific outcome: six joint room planes in each instance, 19/24 held validations, passing direct-only controls, failed transfer and promotion. Processing times are machine dependent; repeating them cannot replace the original measured times. Float tolerances and installed numerical versions must be recorded when comparing another machine.
