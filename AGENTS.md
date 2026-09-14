# ModelFusion / HugOS IDE Rules & Persistent Instructions

## Core Rule: Always Rebuild, Sign, and Synchronize the MSI Installer
Whenever code changes, bug fixes, or enhancements are made to ModelFusion or HugOS IDE:
1. **Recompile Release Binaries**:
   - Recompile the release CLI: `cargo build --release --bin cli`.
   - Verify `target/release/cli.exe` functionality and `--sys-info`.
2. **Rebuild & Sign MSI Package**:
   - Run the packaging pipeline: `powershell -ExecutionPolicy Bypass -File .\IDE\build_msi.ps1`.
   - Verify the build number auto-increments in `IDE/build_number.txt` and `IDE/HugOS.wxs`.
   - Ensure all binaries, DLLs, and the final `IDE/HugOS.msi` are digitally signed with `hugos-signing-cert.pfx` and timestamped via DigiCert.
3. **Commit Code & Git LFS**:
   - Stage all source code changes, tests, and the updated `IDE/HugOS.msi` (tracked via Git LFS).
   - Commit with descriptive conventional commit messages.
   - Push to `origin/main` (or via branch and PR squash-merge).
4. **Update Remote GitHub Release Assets**:
   - Create or update the versioned release tag (`v1.0.0-beta.XX`) with the latest `HugOS.msi` and `target/release/cli.exe`.
   - Update the rolling release [`v1.0.0-beta`](https://github.com/oyesanyf/ModelFusion/releases/tag/v1.0.0-beta) with `--clobber`.
5. **Cryptographic & Git Parity**:
   - Maintain 100% parity between local working directory, git `main`, Git LFS, and remote GitHub release assets (SHA-256 hashes, file sizes, and timestamps).
6. **Disk Hygiene**:
   - Run `git lfs prune --recent` before and after staging large installer files to preserve drive D: free space.
