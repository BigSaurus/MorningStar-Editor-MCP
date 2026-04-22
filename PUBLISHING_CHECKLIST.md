# MorningStar Editor MCP Publishing Checklist

Use this checklist when turning the `MC8 Pro` folder into its own public repository.

## Repo shape

- Make this folder the repository root.
- Keep `pyproject.toml`, `morningstar_mc8_mcp.py`, and `README.md` at the top level.
- Keep `tools/generate_mc8_mcp_tool_reference.py` in the repo so the tool reference can be regenerated and checked.
- Use `PUBLIC_REPO_CONTENTS.md` as the allowlist for what belongs in the public repo.
- Use `tools/export_public_repo.ps1` to stage a clean standalone repo instead of copying the whole working folder by hand.

## Required before public release

- Review the included `LICENSE` file and confirm PolyForm Noncommercial 1.0.0 matches your intended sharing model.
- Replace placeholder GitHub URLs in the docs.
- Review the README as a public landing page, not just an internal note.
- Confirm the MCP config examples match the clients you want to support.

## Validation

Run these commands from the repo root:

```text
python -m py_compile morningstar_mc8_mcp.py tools/generate_mc8_mcp_tool_reference.py
python tools/generate_mc8_mcp_tool_reference.py --check
python -m pip wheel . --no-deps
```

## Release flow

1. Create the standalone GitHub repository.
2. Run `tools/export_public_repo.ps1 -DestinationPath <new-folder>` to stage only the public files.
3. Commit the package files, docs, and tool reference.
4. Push the repo and tag a first release.
5. Test `pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git` from a clean environment.

## Nice-to-have after the first public push

- Add repository URLs to `pyproject.toml`.
- Add a changelog.
- Publish tagged releases instead of asking users to install from a moving branch.