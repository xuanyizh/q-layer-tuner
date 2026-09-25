"""Build and smoke-test a portable Windows x64 executable."""
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
NAME = 'Q_Layer_Tuner_v2.1_Windows_x64'


def main():
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('Build this executable on Windows using 64-bit Python 3.12.')
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'build.py')], cwd=ROOT, check=True)
    output = ROOT / 'windows-dist'
    work = ROOT / 'windows-build'
    work.mkdir(exist_ok=True)
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
        '--windowed', '--noupx', '--name', NAME,
        '--distpath', str(output), '--workpath', str(work / 'work'),
        '--specpath', str(work),
        '--add-data', f'{ROOT / "dist"}:dist',
        '--add-data', f'{ROOT / "qlayer" / "parameters.json"}:qlayer',
        '--add-data', f'{ROOT / "qlayer" / "bep_calibration.json"}:qlayer',
        str(ROOT / 'desktop.py'),
    ], cwd=ROOT, check=True)
    executable = output / f'{NAME}.exe'
    report = output / 'windows-smoke-test.json'
    # A different cwd with spaces catches accidental dependencies on the source tree.
    launch_dir = work / 'test launch directory'
    launch_dir.mkdir(exist_ok=True)
    subprocess.run([str(executable), '--self-test', str(report)], cwd=launch_dir,
                   check=True, timeout=120)
    print(report.read_text(encoding='utf-8'))
    checksum = hashlib.sha256(executable.read_bytes()).hexdigest()
    (output / 'SHA256SUMS.txt').write_text(f'{checksum}  {executable.name}\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'WINDOWS.md', output / 'READ_ME_FIRST.txt')
    shutil.copyfile(ROOT / 'THIRD_PARTY_NOTICES.md', output / 'THIRD_PARTY_NOTICES.md')
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.exists():
        shutil.copyfile(python_license, output / 'PYTHON_LICENSE.txt')
    with zipfile.ZipFile(output / f'{NAME}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in (executable.name, 'READ_ME_FIRST.txt', 'SHA256SUMS.txt',
                     'THIRD_PARTY_NOTICES.md', 'PYTHON_LICENSE.txt', 'windows-smoke-test.json'):
            path = output / name
            if path.exists():
                archive.write(path, arcname=name)
    print(f'Built and tested: {executable}')


if __name__ == '__main__':
    main()
