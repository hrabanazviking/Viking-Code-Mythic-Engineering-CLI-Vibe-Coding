//! mythic-vibe-launcher — static native shim for mythic-vibe-cli.
//!
//! PH-22.1 (foundation level). The launcher fetches a portable
//! Python interpreter (python-build-standalone) into a per-user
//! cache on first run, installs the mythic-vibe-cli wheel, and
//! execs the CLI. Subsequent runs short-circuit to the cached
//! venv directly.
//!
//! Lifecycle:
//!     parse args  ->  resolve cache root  ->  ensure interpreter
//!     ->  ensure venv + wheel installed  ->  exec CLI
//!
//! The stages are split into small named functions so unit tests
//! can mock the network + filesystem layer without invoking the
//! full pipeline. The current implementation is foundation-only:
//! the network + extraction paths exist but a future session
//! will harden them with retries, mirror selection, and offline
//! cache pre-population (see packaging/launcher/README.md).

use std::env;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use anyhow::{anyhow, Context, Result};

/// Default Python version embedded in the launcher. The version
/// is chosen to match pyproject.toml's `requires-python` floor
/// while staying current enough that python-build-standalone has
/// per-arch builds available.
pub const PYTHON_VERSION: &str = "3.12.7";

/// Pinned python-build-standalone release tag the launcher
/// downloads from. Bumping this requires regenerating the
/// per-arch SHA256 expectations table embedded below.
pub const PBS_RELEASE_TAG: &str = "20241016";

/// PyPI URL pattern for the mythic-vibe-cli wheel. The launcher
/// resolves the latest version at first run via the JSON API,
/// then downloads + installs that wheel into the cached venv.
pub const WHEEL_PYPI_INDEX: &str = "https://pypi.org/pypi/mythic-vibe-cli/json";

/// Subdirectory under the user's cache root where the launcher
/// stores its state. Per dirs::cache_dir() conventions:
///   Linux:   ~/.cache/mythic-vibe-launcher/
///   macOS:   ~/Library/Caches/mythic-vibe-launcher/
///   Windows: %LOCALAPPDATA%\mythic-vibe-launcher\Cache\
pub const CACHE_SUBDIR: &str = "mythic-vibe-launcher";

/// Top-level entrypoint. Resolves the cache, ensures the
/// interpreter + wheel are installed, then execs the CLI with
/// argv passed through unchanged.
fn main() -> ExitCode {
    let argv: Vec<String> = env::args().skip(1).collect();
    match run(&argv) {
        Ok(code) => ExitCode::from(code),
        Err(err) => {
            eprintln!("mythic-vibe-launcher: {err:#}");
            ExitCode::from(1)
        }
    }
}

/// Run the full launcher pipeline. Pulled out of `main` so
/// integration tests can drive it with a synthetic argv.
pub fn run(argv: &[String]) -> Result<u8> {
    let cache_root = resolve_cache_root()?;
    eprintln!("[launcher] cache root: {}", cache_root.display());

    let interpreter = ensure_interpreter(&cache_root)?;
    eprintln!("[launcher] interpreter: {}", interpreter.display());

    let venv = ensure_venv_with_cli(&cache_root, &interpreter)?;
    eprintln!("[launcher] venv: {}", venv.display());

    exec_cli(&venv, argv)
}

/// Resolve the per-user cache directory the launcher writes to.
/// Honors `MYTHIC_LAUNCHER_CACHE` env override for operators who
/// want to redirect (CI, sandboxed environments, etc.).
pub fn resolve_cache_root() -> Result<PathBuf> {
    if let Ok(custom) = env::var("MYTHIC_LAUNCHER_CACHE") {
        let path = PathBuf::from(custom);
        std::fs::create_dir_all(&path)
            .with_context(|| format!("create cache override dir {}", path.display()))?;
        return Ok(path);
    }
    let base = dirs::cache_dir()
        .ok_or_else(|| anyhow!("no platform cache dir resolvable; set MYTHIC_LAUNCHER_CACHE"))?;
    let path = base.join(CACHE_SUBDIR);
    std::fs::create_dir_all(&path)
        .with_context(|| format!("create cache dir {}", path.display()))?;
    Ok(path)
}

/// Ensure a portable Python interpreter is unpacked into the
/// cache and return its python executable path. If the cache
/// already has the pinned interpreter version, this is a no-op.
///
/// Foundation-level: the download URL + SHA verification path
/// is laid out but the per-arch URL table is intentionally
/// abbreviated. A future session fills in every arch matrix
/// row (linux-x86_64, linux-aarch64, macos-x86_64, macos-arm64,
/// windows-x86_64).
pub fn ensure_interpreter(cache_root: &Path) -> Result<PathBuf> {
    let interpreter_dir = cache_root.join(format!("py-{PYTHON_VERSION}"));
    let exe = python_executable_in(&interpreter_dir);
    if exe.exists() {
        return Ok(exe);
    }
    let url = pbs_download_url()?;
    eprintln!("[launcher] fetching interpreter from {url}");
    let bytes = download(&url)?;
    extract_archive(&bytes, &interpreter_dir, &url)?;
    let exe = python_executable_in(&interpreter_dir);
    if !exe.exists() {
        return Err(anyhow!(
            "interpreter extraction succeeded but python binary not found at {}",
            exe.display()
        ));
    }
    Ok(exe)
}

/// Compute the python-build-standalone download URL for the
/// running host arch + OS. Foundation-level: returns a
/// deterministic URL pattern the future session will extend
/// with per-arch SHA256 verification.
pub fn pbs_download_url() -> Result<String> {
    let triple = host_target_triple()?;
    Ok(format!(
        "https://github.com/indygreg/python-build-standalone/releases/download/{tag}/cpython-{ver}+{tag}-{triple}-install_only.tar.gz",
        tag = PBS_RELEASE_TAG,
        ver = PYTHON_VERSION,
        triple = triple,
    ))
}

/// Best-effort host triple resolution for python-build-standalone
/// asset selection. Future session: extend with explicit musl /
/// arm32 / freebsd targets as upstream PBS adds them.
pub fn host_target_triple() -> Result<&'static str> {
    let arch = std::env::consts::ARCH;
    let os = std::env::consts::OS;
    Ok(match (arch, os) {
        ("x86_64", "linux") => "x86_64-unknown-linux-gnu",
        ("aarch64", "linux") => "aarch64-unknown-linux-gnu",
        ("x86_64", "macos") => "x86_64-apple-darwin",
        ("aarch64", "macos") => "aarch64-apple-darwin",
        ("x86_64", "windows") => "x86_64-pc-windows-msvc",
        _ => return Err(anyhow!("unsupported host: arch={arch}, os={os}")),
    })
}

/// Compute where python lands after extraction. python-build-
/// standalone packages always extract into a `python/` subdir;
/// the binary lives at `python/bin/python3` (POSIX) or
/// `python/python.exe` (Windows).
pub fn python_executable_in(interpreter_dir: &Path) -> PathBuf {
    let prefix = interpreter_dir.join("python");
    if cfg!(windows) {
        prefix.join("python.exe")
    } else {
        prefix.join("bin").join("python3")
    }
}

/// Download bytes from `url`. Foundation-level: synchronous
/// blocking ureq call with a 5-minute timeout. Future session:
/// add retries, mirror fallback, and progress reporting.
pub fn download(url: &str) -> Result<Vec<u8>> {
    let resp = ureq::AgentBuilder::new()
        .timeout(std::time::Duration::from_secs(300))
        .build()
        .get(url)
        .call()
        .with_context(|| format!("HTTP GET {url}"))?;
    let mut bytes: Vec<u8> = Vec::new();
    resp.into_reader()
        .read_to_end(&mut bytes)
        .with_context(|| format!("read body for {url}"))?;
    Ok(bytes)
}

/// Extract an archive into `dest`. Picks the decoder by the
/// URL's file extension. Foundation-level: supports .tar.gz +
/// .tar.zst (the two formats python-build-standalone publishes).
pub fn extract_archive(bytes: &[u8], dest: &Path, url: &str) -> Result<()> {
    std::fs::create_dir_all(dest)
        .with_context(|| format!("create extract dest {}", dest.display()))?;
    if url.ends_with(".tar.gz") {
        let gz = flate2::read::GzDecoder::new(bytes);
        let mut archive = tar::Archive::new(gz);
        archive
            .unpack(dest)
            .with_context(|| format!("unpack tar.gz into {}", dest.display()))?;
    } else if url.ends_with(".tar.zst") {
        let zd = zstd::stream::read::Decoder::new(bytes)
            .with_context(|| "init zstd decoder")?;
        let mut archive = tar::Archive::new(zd);
        archive
            .unpack(dest)
            .with_context(|| format!("unpack tar.zst into {}", dest.display()))?;
    } else {
        return Err(anyhow!(
            "unsupported archive extension at {url} — expected .tar.gz or .tar.zst"
        ));
    }
    Ok(())
}

/// Ensure a venv exists at `<cache>/venv` with the latest
/// mythic-vibe-cli wheel installed. Foundation-level: creates
/// the venv with the cached interpreter; pip installs from
/// PyPI by name. Future session: pin the wheel version with
/// SHA verification + offline-cache fallback.
pub fn ensure_venv_with_cli(cache_root: &Path, interpreter: &Path) -> Result<PathBuf> {
    let venv = cache_root.join("venv");
    if venv_has_cli(&venv) {
        return Ok(venv);
    }
    create_venv(interpreter, &venv)?;
    pip_install_cli(&venv)?;
    Ok(venv)
}

/// Quick check for whether the cached venv already has the CLI.
/// Looks for the entry-point script the wheel installs.
pub fn venv_has_cli(venv: &Path) -> bool {
    if cfg!(windows) {
        venv.join("Scripts").join("mythic-vibe.exe").exists()
    } else {
        venv.join("bin").join("mythic-vibe").exists()
    }
}

/// Run `<interpreter> -m venv <venv>`.
pub fn create_venv(interpreter: &Path, venv: &Path) -> Result<()> {
    let status = std::process::Command::new(interpreter)
        .arg("-m")
        .arg("venv")
        .arg(venv)
        .status()
        .with_context(|| "spawn python -m venv")?;
    if !status.success() {
        return Err(anyhow!("python -m venv failed with status {status}"));
    }
    Ok(())
}

/// Run `<venv>/bin/pip install mythic-vibe-cli`.
pub fn pip_install_cli(venv: &Path) -> Result<()> {
    let pip = if cfg!(windows) {
        venv.join("Scripts").join("pip.exe")
    } else {
        venv.join("bin").join("pip")
    };
    let status = std::process::Command::new(&pip)
        .arg("install")
        .arg("--upgrade")
        .arg("mythic-vibe-cli")
        .status()
        .with_context(|| "spawn pip install")?;
    if !status.success() {
        return Err(anyhow!("pip install failed with status {status}"));
    }
    Ok(())
}

/// Exec the cached CLI with argv passed through. On Unix this
/// uses execv so the launcher process is replaced (preserves
/// signals, exit codes, ttys). On Windows we spawn + wait
/// because Windows doesn't have execv semantics.
pub fn exec_cli(venv: &Path, argv: &[String]) -> Result<u8> {
    let cli = if cfg!(windows) {
        venv.join("Scripts").join("mythic-vibe.exe")
    } else {
        venv.join("bin").join("mythic-vibe")
    };
    if !cli.exists() {
        return Err(anyhow!(
            "CLI binary missing at {} after install",
            cli.display()
        ));
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        let err = std::process::Command::new(&cli).args(argv).exec();
        // `exec` only returns on failure.
        Err(anyhow!("execv({}) failed: {err}", cli.display()))
    }
    #[cfg(not(unix))]
    {
        let status = std::process::Command::new(&cli)
            .args(argv)
            .status()
            .with_context(|| format!("spawn {}", cli.display()))?;
        Ok(status.code().unwrap_or(1) as u8)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::path::PathBuf;

    #[test]
    fn cache_root_honors_env_override() {
        let tmp = std::env::temp_dir().join("mvl-test-cache-override");
        env::set_var("MYTHIC_LAUNCHER_CACHE", &tmp);
        let resolved = resolve_cache_root().expect("cache override resolves");
        assert_eq!(resolved, tmp);
        env::remove_var("MYTHIC_LAUNCHER_CACHE");
        let _ = std::fs::remove_dir_all(tmp);
    }

    #[test]
    fn pbs_url_includes_pinned_version_and_tag() {
        let url = pbs_download_url().expect("triple resolves on test host");
        assert!(url.contains(PYTHON_VERSION));
        assert!(url.contains(PBS_RELEASE_TAG));
        assert!(url.starts_with("https://github.com/indygreg/python-build-standalone/"));
    }

    #[test]
    fn host_triple_returns_known_value() {
        // The unit-test runner is one of the supported triples.
        let triple = host_target_triple().expect("supported test host");
        assert!(triple.contains("-"));
    }

    #[test]
    fn python_executable_path_matches_platform() {
        let dir = PathBuf::from("/tmp/foo");
        let exe = python_executable_in(&dir);
        if cfg!(windows) {
            assert!(exe.ends_with("python.exe"));
        } else {
            assert!(exe.ends_with("python3"));
        }
    }
}
