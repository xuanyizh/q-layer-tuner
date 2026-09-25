# Third-party runtime

The unmodified Pyodide 0.27.7 browser runtime is bundled in
`dist/vendor/pyodide/`. It was obtained from the official release distribution
at https://cdn.jsdelivr.net/pyodide/v0.27.7/full/.

Pyodide source and release: https://github.com/pyodide/pyodide/tree/0.27.7
License: Mozilla Public License 2.0, included at `dist/vendor/pyodide/LICENSE`.
The source is available at the preceding link. Runtime distribution metadata
is in its `package.json` and `pyodide-lock.json`.

The runtime embeds CPython and its standard library. CPython's license is
included as `dist/vendor/pyodide/python-PSF-LICENSE`.
CPython source: https://github.com/python/cpython

No scientific Python packages are loaded: the Q Layer core uses only the
standard library. The lockfile describes optional upstream packages; inclusion
of that metadata does not mean those packages have been installed in this app.
