# Update your existing GitHub Pages app

There are two packages. Choose the instructions matching your current repository.
No repository deletion is needed.

## If index.html is at the repository's top level

Use **Q_Layer_Tuner_v2.1_GitHub_Upload.zip**.

1. Extract that ZIP.
2. In the existing repository choose Code → Add file → Upload files.
3. Upload all contents of the extracted folder, including `python`, `vendor`,
   and `.nojekyll`, at the repository's top level. Upload the contents, not the
   outer folder or ZIP. Commit the changes.
4. Keep the existing working deployment settings. This layout supports either
   main + /(root) branch deployment or the Static HTML workflow publishing `.`.
5. Wait for deployment to succeed, reload the website, and check the v2.1 badge.
   Calibration now contains separate As and P measured-pair entry boxes.

## If the repository contains dist/index.html and qlayer/engine.py

Use the updated full Python source package.

1. Extract it and upload the contents of its Q_Layer_Tuner_v2.1 folder into the
   repository's top level, replacing matching files. Include the new
   `qlayer/calibration.py` and `dist/python/qlayer/calibration.py`.
2. Keep the existing working workflow that publishes `dist/`.
   The included `.github/workflows/pages.yml` builds the browser copy, runs the
   checks, and uploads `dist/`. Do not add a competing root-folder deployment.
3. With that workflow, Settings → Pages → Source should be GitHub Actions.
4. Commit/push to main and wait for the build/deploy jobs to succeed.

If GitHub Pages shows README text instead of the app, its published folder has
no index.html. Use the ready-upload layout, or fix the source workflow to publish
dist/. The source package's root README is documentation, not the website.

The Python core runs in the browser with bundled Pyodide. No Python web service,
Anaconda, Django, PyPI release, or package installation is required for hosting.
All website asset paths are relative, including the new calibration module.

Calibration JSON files downloaded through the app are user data, not code updates.
Loading them changes the current session's calibration. It does not commit files
to GitHub or change other users' calibrations.
