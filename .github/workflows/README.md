# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated CI/CD processes.

## Available Workflows

### 🔍 Ruff Code Quality (`ruff.yml`)

Automated code quality checks using Ruff linter and formatter.

**Triggers:**
- Push to `main` or `develop` branches (when Python files change)
- Pull requests to `main` or `develop` branches (when Python files change)
- Changes to `pyproject.toml` or the workflow file itself

**What it does:**
1. Checks out the code
2. Sets up Python 3.11
3. Installs Ruff
4. Runs linter (`ruff check`) with GitHub annotations
5. Verifies code formatting (`ruff format --check`)

**Status Badge:**
```markdown
![Ruff](https://github.com/YOUR_USERNAME/powerdraw_notifier/actions/workflows/ruff.yml/badge.svg)
```

### 📦 Windows Build (`windows-build.yml`)

Automated Windows executable packaging using PyInstaller.

**Triggers:**
- Push to `main` branch
- Version tags matching `v*` (e.g., `v1.0.0`)
- Pull requests to `main` branch
- Manual workflow dispatch from GitHub UI

**What it does:**
1. Checks out the code
2. Sets up Python 3.11 with pip caching
3. Installs all dependencies
4. Generates application icons
5. Builds Windows executable with PyInstaller
6. Verifies build output
7. Creates versioned ZIP archive
8. Uploads build artifact (30-day retention)
9. **For tagged releases**: Automatically creates GitHub release with executable

**Outputs:**
- **Artifact**: `PowerMonitor-Windows-{version}.zip`
- **Retention**: 30 days
- **Release**: Automatic for version tags

**Status Badge:**
```markdown
![Windows Build](https://github.com/YOUR_USERNAME/powerdraw_notifier/actions/workflows/windows-build.yml/badge.svg)
```

## Usage

### Running Workflows Manually

1. Go to the **Actions** tab in your GitHub repository
2. Select the workflow you want to run
3. Click **Run workflow**
4. Choose the branch and click **Run workflow**

### Creating a Release

To trigger an automated build and release:

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

This will:
1. Trigger the Windows build workflow
2. Build the executable
3. Create a GitHub release
4. Attach the Windows ZIP file to the release

### Checking Workflow Status

- View workflow runs in the **Actions** tab
- Each commit/PR shows workflow status
- Click on a workflow run to see detailed logs
- Failed workflows show annotations on code

## Workflow Badges

Add these badges to your README.md to show workflow status:

```markdown
[![Ruff](https://github.com/YOUR_USERNAME/powerdraw_notifier/actions/workflows/ruff.yml/badge.svg)](https://github.com/YOUR_USERNAME/powerdraw_notifier/actions/workflows/ruff.yml)
[![Windows Build](https://github.com/YOUR_USERNAME/powerdraw_notifier/actions/workflows/windows-build.yml/badge.svg)](https://github.com/YOUR_USERNAME/powerdraw_notifier/actions/workflows/windows-build.yml)
```

Replace `YOUR_USERNAME` with your GitHub username.

## Troubleshooting

### Ruff Workflow Fails

**Issue**: Linting or formatting errors detected

**Solution**: Run locally before pushing:
```bash
ruff check --fix power_monitor/ generate_icons.py
ruff format power_monitor/ generate_icons.py
git add .
git commit -m "Fix linting issues"
```

### Windows Build Fails

**Common issues:**

1. **Missing icons**
   - Ensure `assets/icon.png` and `assets/icon_alert.png` exist
   - The workflow generates them automatically via `generate_icons.py`

2. **Dependency errors**
   - Check `requirements.txt` and `requirements-dev.txt` are up to date
   - Test locally: `pip install -r requirements.txt -r requirements-dev.txt`

3. **PyInstaller errors**
   - Review `PowerMonitor.spec` for correct paths
   - Test locally: `pyinstaller PowerMonitor.spec`

4. **Build artifact not found**
   - Check that `dist/PowerMonitor/PowerMonitor.exe` is created
   - Review PyInstaller logs in the workflow output

### Release Not Created

**Issue**: Tag pushed but no release created

**Check:**
- Tag format matches `v*` (e.g., `v1.0.0`, not `1.0.0`)
- Workflow completed successfully (check Actions tab)
- `GITHUB_TOKEN` has proper permissions (default token should work)

## Extending Workflows

### Adding macOS/Linux Builds

Create similar workflows for other platforms:
- `macos-build.yml` - Build .app bundle or executable
- `linux-build.yml` - Build Linux executable

Copy `windows-build.yml` and adjust:
- Change `runs-on: windows-latest` to `macos-latest` or `ubuntu-latest`
- Update build script call (use `.sh` instead of `.bat`)
- Adjust artifact paths and file extensions

### Adding Tests

Add a test step to `ruff.yml` or create a separate `tests.yml`:

```yaml
- name: Run tests
  run: |
    pip install pytest
    pytest tests/
```

### Adding Pre-commit Hooks

Integrate with pre-commit for local validation before pushing:

```yaml
- name: Run pre-commit
  uses: pre-commit/action@v3.0.0
```

## Security Notes

- Workflows use `GITHUB_TOKEN` which is automatically provided
- Artifact retention: 30 days (configurable in workflow)
- No secrets required for basic workflows
- PyInstaller builds are public artifacts (anyone can download)

## Further Reading

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyInstaller Documentation](https://pyinstaller.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
