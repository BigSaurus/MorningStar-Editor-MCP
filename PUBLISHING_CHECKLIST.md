# MorningStar Editor MCP Publishing Checklist

Maintainer checklist for cutting a release of this standalone public repository.

## Repo shape

- `pyproject.toml`, `morningstar_mc8_mcp.py`, and `README.md` stay at the top level.
- Keep `tools/generate_mc8_mcp_tool_reference.py` in the repo so the tool reference can be regenerated
  and checked.
- Use `PUBLIC_REPO_CONTENTS.md` as the allowlist for what belongs in the repo.

## Before a release

- Review `LICENSE` and confirm PolyForm Noncommercial 1.0.0 still matches your intended sharing model.
- Confirm the GitHub URLs in the docs point at this repository.
- Review the README as a public landing page.
- Confirm the MCP config examples match the clients you want to support.

## Validation

Run these from the repository root:

```text
python -m py_compile morningstar_mc8_mcp.py tools/generate_mc8_mcp_tool_reference.py
python tools/generate_mc8_mcp_tool_reference.py --check
python -m pip wheel . --no-deps
```

## Release flow

1. Commit the package files, docs, and regenerated tool reference.
2. Push to `main`.
3. Tag a release.
4. Test `pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git` from a clean environment.

## Nice-to-have

- Add repository URLs to `pyproject.toml`.
- Add a changelog.
- Publish tagged releases instead of asking users to install from a moving branch.
