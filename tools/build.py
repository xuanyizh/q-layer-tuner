"""Copy the canonical Python core into the static web distribution."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / 'dist' / 'python' / 'qlayer'
target.mkdir(parents=True, exist_ok=True)
for name in ('__init__.py', 'engine.py', 'calibration.py', 'parameters.json', 'bep_calibration.json'):
    shutil.copy2(ROOT / 'qlayer' / name, target / name)
(ROOT / 'dist' / '.nojekyll').write_text('# Serve the prepared website without Jekyll processing.\n')
print('Built static site with the canonical Python core.')
