# Publish checklist

How this work-in-progress repository becomes the public repository
`siddharthkumarx/scrapeplanner`. **Never make `scrapeplanner-wip` public**: its
history holds earlier runs and private notes. The public repository starts
from a clean `main` with a single initial commit.

## 1. Prepare a clean tree (locally)

```bash
git clone https://github.com/siddharthkumarx/scrapeplanner-wip scrapeplanner-src
cd scrapeplanner-src
git checkout <the finished branch>
```

- [ ] `rm -rf docs/private/` (the maintainer's own explainer).
- [ ] `git mv CLAUDE.md docs/maintainers.md`, then fix the links to it
      (`grep -rn "CLAUDE.md" .`).
- [ ] Remove this repository's working notes that only make sense here:
      `docs/readme-plan.md`, `docs/build-progress.md` (or keep it as history;
      decide once).
- [ ] Keep `checks/results/001-smoke` and the current results run only
      (`docs/results.md` names it). Delete any other run directory.
- [ ] `grep -rn "scrapeplanner-wip" .` returns nothing that a reader would follow.
- [ ] `./scripts/check.sh` passes; `uv run --group visual pytest -m visual` passes.

## 2. Create the public repository

- [ ] On GitHub create `siddharthkumarx/scrapeplanner`, **empty** (no README,
      no license: they come from the tree).
- [ ] Fresh history:

```bash
rm -rf .git
git init -b main
git config user.name "Siddharth Kumar"
git config user.email 273157498+siddharthkumarx@users.noreply.github.com
git config core.hooksPath .githooks
git add -A
git commit -m "Initial public release of scrapeplanner"
git remote add origin https://github.com/siddharthkumarx/scrapeplanner.git
git push -u origin main
```

- [ ] Settings as in `docs/repo-settings.md`: About text, website, topics,
      social preview (`assets/social-preview.png`).
- [ ] Settings → Code security: enable private vulnerability reporting,
      secret scanning and Dependabot alerts.
- [ ] Settings → Branches: protect `main` (require the `ci` checks, no force
      pushes).
- [ ] Actions → `ci` is green on `main`. The CI badge in the README now resolves.

## 3. Check every link

- [ ] Open the README on GitHub, desktop and phone width; every image shows,
      the animated SVGs play, and with "reduce motion" on they show the final frame.
- [ ] Click every link in README.md, CONTRIBUTING.md, SECURITY.md,
      docs/*.md (relative links, issue templates, the security advisory link).
- [ ] `docs/results.md` links point at files that exist in the public tree.

## 4. PyPI (only when the maintainer says "publish")

- [ ] Re-check that the name `scrapeplanner` is still free on PyPI (D-001).
- [ ] On PyPI: *Your account → Publishing → Add a pending publisher*:
      owner `siddharthkumarx`, repository `scrapeplanner`, workflow
      `release.yml`, environment `pypi`. Same on TestPyPI with environment
      `testpypi` for a dry run.
- [ ] GitHub → Settings → Environments: create `pypi` (and `testpypi`);
      require the maintainer's approval for `pypi`.
- [ ] Dry run: Actions → release → Run workflow with "Upload to TestPyPI";
      `pipx install --index-url https://test.pypi.org/simple/ scrapeplanner`.
- [ ] In `.github/workflows/release.yml` change the `pypi` job's `if: false`
      to `if: startsWith(github.ref, 'refs/tags/v')`.
- [ ] Set `__version__` (e.g. `0.1.0`), move the CHANGELOG entries under that
      version, commit, tag `v0.1.0`, push the tag. The workflow builds, tests
      and publishes through Trusted Publishing; no token is stored anywhere.
- [ ] Add the PyPI version and Python versions badges to the README and the
      `pipx install scrapeplanner` line loses its "after the first release" note.
