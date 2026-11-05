# Publish checklist

## Done: published in place (2026-11-05)

The private work-in-progress repository was made public and renamed to
`siddharthkumarx/scrapeplanner`; its default branch is `main`. Its history
was rewritten once with `git filter-repo` and force-pushed once, with the
maintainer's approval:

- `docs/private/` (the maintainer's own notes) removed from every commit;
- the maintainers' guide moved to `docs/maintainers.md` in every commit;
- commit signatures dropped; authors, committers, dates, messages and the
  data commits of the checks workflow kept unchanged.

Do not rewrite or force-push `main` again: clones, forks and links to
commits depend on it.

## Still to do in GitHub settings

- [ ] About, website, topics and social preview, as in `docs/repo-settings.md`.
- [ ] Settings → Code security: private vulnerability reporting (SECURITY.md
      relies on it), secret scanning, Dependabot alerts.
- [ ] Settings → Branches: protect `main` (require the `ci` checks, no force
      pushes).

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
