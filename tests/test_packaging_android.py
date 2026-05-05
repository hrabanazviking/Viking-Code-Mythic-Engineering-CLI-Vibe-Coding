"""Phase 22.2 — Android wrapper scaffold structural sanity.

The actual Gradle build runs on the Android CI runner (gradle +
JDK + Android SDK not always present in the unit-test runner).
Here we lint the Gradle project shape + Kotlin / Python source
shape + workflow shape so a renamed file or dropped step gets
caught at PR time instead of release time.

Foundation-level: these tests check the scaffold's contract.
The runtime-behavior surface lives in the Python runner module
(testable from the desktop) and the Compose UI (testable via
Android instrumented tests in a future slice).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ANDROID_DIR = REPO_ROOT / "packaging" / "android"
SETTINGS_GRADLE = ANDROID_DIR / "settings.gradle.kts"
ROOT_BUILD_GRADLE = ANDROID_DIR / "build.gradle.kts"
GRADLE_PROPS = ANDROID_DIR / "gradle.properties"
APP_BUILD_GRADLE = ANDROID_DIR / "app" / "build.gradle.kts"
ANDROID_MANIFEST = (
    ANDROID_DIR / "app" / "src" / "main" / "AndroidManifest.xml"
)
MAIN_ACTIVITY = (
    ANDROID_DIR / "app" / "src" / "main" / "kotlin" /
    "dev" / "mythicvibe" / "android" / "MainActivity.kt"
)
PYTHON_RUNNER = (
    ANDROID_DIR / "app" / "src" / "main" / "python" /
    "mythic_vibe_cli_android_runner.py"
)
ANDROID_README = ANDROID_DIR / "README.md"
RELEASE_ANDROID_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "release-android.yml"
)


class AndroidGradleProjectTests(unittest.TestCase):
    def test_settings_gradle_exists_and_includes_app_module(self) -> None:
        self.assertTrue(SETTINGS_GRADLE.is_file())
        text = SETTINGS_GRADLE.read_text(encoding="utf-8")
        self.assertIn('include(":app")', text)
        self.assertIn('rootProject.name = "mythic-vibe-android"', text)

    def test_settings_gradle_includes_chaquopy_repo(self) -> None:
        # Chaquopy plugin lives in chaquo.com/maven, not in
        # google() or mavenCentral(). Without this repo entry the
        # plugin resolution fails at the first sync.
        text = SETTINGS_GRADLE.read_text(encoding="utf-8")
        self.assertIn("https://chaquo.com/maven", text)

    def test_root_build_gradle_pins_plugin_versions(self) -> None:
        self.assertTrue(ROOT_BUILD_GRADLE.is_file())
        text = ROOT_BUILD_GRADLE.read_text(encoding="utf-8")
        # The four plugins our app module depends on must be
        # declared `apply false` at root with explicit versions.
        for plugin in (
            "com.android.application",
            "org.jetbrains.kotlin.android",
            "org.jetbrains.kotlin.plugin.compose",
            "com.chaquo.python",
        ):
            self.assertIn(f'id("{plugin}")', text)
            self.assertIn("apply false", text)

    def test_gradle_properties_enables_androidx(self) -> None:
        self.assertTrue(GRADLE_PROPS.is_file())
        text = GRADLE_PROPS.read_text(encoding="utf-8")
        self.assertIn("android.useAndroidX=true", text)


class AppModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(APP_BUILD_GRADLE.is_file())
        self.text = APP_BUILD_GRADLE.read_text(encoding="utf-8")

    def test_app_module_applies_chaquopy_plugin(self) -> None:
        # Without the Chaquopy plugin the chaquopy { ... } block
        # below is silently a no-op.
        self.assertIn('id("com.chaquo.python")', self.text)

    def test_app_module_uses_compose(self) -> None:
        # The activity is Compose-based — buildFeatures.compose
        # must be true.
        self.assertIn("compose = true", self.text)

    def test_app_module_pip_installs_cli(self) -> None:
        # Chaquopy's pip block runs `pip install` at APK build
        # time so the wheel + transitive deps bake into the APK.
        # The dependency name must match pyproject.toml's
        # project.name field.
        self.assertRegex(
            self.text, r'install\(\s*"mythic-vibe-cli"\s*\)',
        )

    def test_min_sdk_covers_modern_android(self) -> None:
        # Android 8.0+ for Compose + Chaquopy compatibility.
        self.assertRegex(self.text, r"minSdk\s*=\s*26")

    def test_abi_filters_cover_modern_devices(self) -> None:
        # Four ABIs cover essentially every device shipped since
        # 2019. Missing one ships an APK that won't install on
        # the missing arch.
        for abi in ("armeabi-v7a", "arm64-v8a", "x86", "x86_64"):
            self.assertIn(f'"{abi}"', self.text)

    def test_targets_python_3_12(self) -> None:
        # Match the launcher's Python version pin so Chaquopy +
        # the launcher use the same interpreter version.
        self.assertRegex(self.text, r'version\s*=\s*"3\.12"')


class AndroidManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(ANDROID_MANIFEST.is_file())
        self.text = ANDROID_MANIFEST.read_text(encoding="utf-8")

    def test_declares_internet_permission_only(self) -> None:
        # INTERNET is required for AI-provider extras when an
        # operator configures one. No other permissions —
        # privacy-by-default. Strip XML comments before checking
        # so the rationale documentation in the comment block
        # doesn't trigger false positives.
        comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
        live_xml = comment_pattern.sub("", self.text)
        self.assertIn(
            'android:name="android.permission.INTERNET"', live_xml,
        )
        # Permissions that should NOT be declared in live XML
        # (the comment block explains why each is omitted).
        for forbidden in (
            "RECORD_AUDIO",
            "WRITE_EXTERNAL_STORAGE",
            "READ_CONTACTS",
            "ACCESS_FINE_LOCATION",
        ):
            self.assertNotIn(
                f"android.permission.{forbidden}", live_xml,
                f"manifest declares unexpected permission: {forbidden}",
            )

    def test_declares_main_activity(self) -> None:
        # Single-activity app — MainActivity must be the only
        # exported activity with the LAUNCHER intent filter.
        self.assertIn('android:name=".MainActivity"', self.text)
        self.assertIn(
            'android:name="android.intent.category.LAUNCHER"', self.text,
        )


class MainActivityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(MAIN_ACTIVITY.is_file())
        self.text = MAIN_ACTIVITY.read_text(encoding="utf-8")

    def test_starts_chaquopy_python(self) -> None:
        # Compose UI calls into Python via Chaquopy — the
        # interpreter must be started before the first call.
        self.assertIn("Python.start", self.text)

    def test_uses_compose_setcontent(self) -> None:
        # The activity is Compose-based, not XML-layout-based.
        self.assertIn("setContent", self.text)

    def test_invokes_runner_module(self) -> None:
        # The Kotlin side calls into mythic_vibe_cli_android_runner
        # via Chaquopy. Module name must match the file name in
        # app/src/main/python/.
        self.assertIn("mythic_vibe_cli_android_runner", self.text)

    def test_uses_io_dispatcher_for_cli_calls(self) -> None:
        # CLI invocations may take seconds — must run on
        # Dispatchers.IO, not the main UI thread.
        self.assertIn("Dispatchers.IO", self.text)


class AndroidPythonRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(PYTHON_RUNNER.is_file())
        self.text = PYTHON_RUNNER.read_text(encoding="utf-8")

    def test_imports_cli_main(self) -> None:
        # The runner must call the same main() the pip install
        # uses — diverging entrypoints would create per-platform
        # behavioral drift.
        self.assertIn("from mythic_vibe_cli.cli import main", self.text)

    def test_captures_stdout_and_stderr(self) -> None:
        # The Compose UI shows captured output; both streams
        # must be redirected so error messages reach the user.
        self.assertIn("contextlib.redirect_stdout", self.text)
        self.assertIn("contextlib.redirect_stderr", self.text)

    def test_handles_systemexit(self) -> None:
        # argparse errors raise SystemExit; without a try/except
        # the runner crashes with a SystemExit propagation that
        # breaks Chaquopy's JNI bridge.
        self.assertIn("SystemExit", self.text)

    def test_returns_string_not_none(self) -> None:
        # Chaquopy maps Python str -> Kotlin String. None would
        # become Kotlin null and break the Text composable.
        self.assertIn("def run_cli(", self.text)
        self.assertIn("-> str:", self.text)

    def test_runner_module_imports_cleanly(self) -> None:
        # Compile the runner standalone — catches syntax errors
        # at PR time without needing Chaquopy in the test env.
        compile(self.text, str(PYTHON_RUNNER), "exec")


class AndroidReadmeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(ANDROID_README.is_file())
        self.text = ANDROID_README.read_text(encoding="utf-8")

    def test_explains_chaquopy_choice(self) -> None:
        # Operators who think "why not BeeWare" need the answer
        # in the README.
        self.assertIn("Chaquopy", self.text)
        self.assertIn("BeeWare", self.text)

    def test_documents_min_sdk(self) -> None:
        # Operators check OS support; min-SDK 26 = Android 8.0.
        self.assertRegex(
            self.text, r"min[- ]?sdk\s*26|Android 8\.0",
        )

    def test_lists_deferred_work(self) -> None:
        # Future sessions need to know exactly what's foundation
        # vs deferred. Smoke-check the deferred subsection.
        self.assertRegex(
            self.text, r"deferred to a future session", re.IGNORECASE,
        )


class ReleaseAndroidWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(RELEASE_ANDROID_WORKFLOW.is_file())
        self.text = RELEASE_ANDROID_WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_on_version_tags(self) -> None:
        self.assertRegex(self.text, r'tags:\s*\n\s+-\s+"v\*\.\*\.\*"')

    def test_supports_workflow_dispatch_for_rehearsal(self) -> None:
        self.assertIn("workflow_dispatch", self.text)

    def test_uses_jdk_17(self) -> None:
        # AGP 8.x requires JDK 17.
        self.assertIn('java-version: "17"', self.text)

    def test_runs_assemble_release(self) -> None:
        self.assertIn("assembleRelease", self.text)

    def test_signs_with_sigstore(self) -> None:
        # PH-21.5 pattern over the APK bytes (separate concern
        # from Android's own APK signing).
        self.assertIn("sigstore/gh-action-sigstore-python", self.text)

    def test_emits_slsa_attestation(self) -> None:
        # PH-21.6 pattern.
        self.assertIn("actions/attest-build-provenance", self.text)
        self.assertIn("attestations: write", self.text)

    def test_uploads_to_github_release(self) -> None:
        self.assertIn("softprops/action-gh-release", self.text)


if __name__ == "__main__":
    unittest.main()
