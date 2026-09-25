# Update your GitHub Pages app

This package keeps Python as the scientific core while supporting static
GitHub Pages through bundled Pyodide. No paid Python hosting service is needed.

1. Extract the ZIP and copy its contents into your `q-layer-tuner` repository's
   root. Include the `qlayer`, `dist`, `tools`, `tests`, and `.github` folders,
   plus the root files. Preserve your repository's `.git` directory. Remove the
   retired `dist/engine.js`, `dist/parameters.json`, and `tests/engine.test.mjs`
   if they remain from v1; v2 does not load them.
2. Check that `.github/workflows/pages.yml` is present. If your existing Pages
   workflow already deploys the site, replace it with this workflow to avoid
   two workflows publishing competing builds.
3. Commit and push to `main`. If your default branch has a different name,
   update the workflow's `on.push.branches` entry first.
4. In the repository, select **Settings → Pages → Build and deployment →
   Source → GitHub Actions**.
5. Run the **Deploy Q Layer Tuner** workflow from the Actions tab if a run has
   not started. Wait for the build and deploy jobs to finish. The deploy job
   reports the published address. For the existing repository, it is normally
   `https://xuanyizh.github.io/q-layer-tuner/`.

The workflow tests the Python core, copies it into the static distribution, and
uploads only `dist/`. All app paths are relative, so a project subdirectory works.
Node is used for UI/runtime checks, not for a second physics implementation.
Do not use a branch deployment of the repository root: the HTML entrypoint is
inside `dist/`, and the workflow is configured accordingly.

After changing any Python code, push the canonical `qlayer` files; the workflow
rebuilds the browser copy. Include the bundled `dist/vendor/pyodide` files intact.
Their licenses are included. The website must serve `.wasm` as
`application/wasm`; GitHub Pages supports Pyodide static deployment.

Official references checked for this package:
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://pyodide.org/en/0.27.7/usage/downloading-and-deploying.html

Your GitHub repository is not automatically updated by downloading this ZIP.
The app's separately hosted preview is updated independently.
