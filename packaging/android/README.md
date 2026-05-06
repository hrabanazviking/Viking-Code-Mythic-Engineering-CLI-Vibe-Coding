# mythic-vibe-android

PH-22.2 — native Android app wrapping `mythic-vibe-cli` via [Chaquopy](https://chaquo.com/chaquopy/).

## What it is

A single-activity Compose app that embeds CPython 3.12 + the `mythic-vibe-cli` wheel into the APK at build time. The user types a CLI command into a text field, taps **Run**, the activity invokes the embedded Python on a background coroutine, and streams output to a Compose Text composable.

Complementary to the existing [Termux install path](../../docs/INSTALL.md#termux-android) — Termux requires the operator install Termux + run `pip install` themselves; this app delivers the same CLI as a one-tap install from a release APK or future F-Droid / Play Store distribution.

## Why Chaquopy over BeeWare

Both Chaquopy and BeeWare embed Python in Android apps. Chaquopy was chosen because:

1. **Mature.** Chaquopy has shipped per-Python-version since 3.8 with a strict Gradle-plugin model. BeeWare's Briefcase is younger and the Android target is still labeled "experimental".
2. **Plain Gradle.** Chaquopy is a Gradle plugin — operators with Android Studio see a familiar build. BeeWare's Briefcase wraps Gradle in a Python CLI that's friendlier for Python-first developers but harder to integrate into a standard Android CI pipeline.
3. **Pip-driven dep install.** Chaquopy's `chaquopy { defaultConfig { pip { install("mythic-vibe-cli") } } }` block runs `pip install` at APK build time, baking the wheel + transitive deps into the APK. No first-run network IO needed.

BeeWare remains an option if Chaquopy's commercial license becomes a concern (Chaquopy is commercial-but-free for open-source projects).

## Build instructions

```bash
# Inside packaging/android/:
./gradlew assembleDebug              # debug APK at app/build/outputs/apk/debug/
./gradlew assembleRelease            # release APK (unsigned by default)
./gradlew installDebug               # install on a connected device / emulator
```

The release APK is unsigned by default. For Play Store / F-Droid distribution a future session adds signing config + the release-android.yml signing step.

## Project layout

```
packaging/android/
├── settings.gradle.kts                 # Gradle project includes
├── build.gradle.kts                    # Top-level plugins (apply false)
├── gradle.properties                   # Gradle JVM / cache settings
└── app/
    ├── build.gradle.kts                # App module + Chaquopy config
    ├── proguard-rules.pro              # ProGuard advisory rules
    └── src/main/
        ├── AndroidManifest.xml         # INTERNET permission only
        ├── kotlin/dev/mythicvibe/android/
        │   └── MainActivity.kt         # Compose UI
        └── python/
            └── mythic_vibe_cli_android_runner.py
                                        # Chaquopy-side runner that
                                        # invokes mythic_vibe_cli.cli.main
                                        # and captures stdout + stderr
```

## Foundation-level scope (PH-22.2, this commit)

What works today:

- ✅ Buildable Gradle project with the Chaquopy plugin pinned at v16.
- ✅ Compose-based single-activity UI.
- ✅ Chaquopy `pip install("mythic-vibe-cli")` baked into the build.
- ✅ Python runner module captures stdout + stderr from `mythic_vibe_cli.cli.main`.
- ✅ Min-SDK 26 (Android 8.0+) covers ~99 % of in-use Android devices.
- ✅ Four ABI filters (armeabi-v7a, arm64-v8a, x86, x86_64) cover essentially every device shipped since 2019.

What was shipped after the foundation level:

- ✅ **APK signing config** (PH-23.5, 2026-05-05). `app/build.gradle.kts` declares a release `signingConfig` that reads from project properties (`mythicReleaseStoreFile`, etc.) or env vars (`ANDROID_KEYSTORE_FILE`, etc.). When all four credentials are present the release APK is signed; when any are missing the build falls back to an unsigned APK. The `release-android.yml` workflow decodes a base64'd keystore from the `ANDROID_KEYSTORE_BASE64` secret and sets the env vars before `assembleRelease`. Maintainer setup recipe lives in `packaging/android/SIGNING.md`.

What's deferred to a future session:
- ⚠️ **Streaming stdout.** The runner buffers full output and returns once the CLI exits. A line-streaming generator + Kotlin polling loop would make `mythic-vibe verify` feel responsive on long runs.
- ⚠️ **Cancellation.** Compose's coroutine cancellation should propagate into the Python runner. Today a tap on Run during a previous run is no-op'd; better UX would interrupt + restart.
- ⚠️ **Persistent session log.** Each Run replaces the previous output. A scrollable log would let operators review prior commands.
- ⚠️ **Native UI for richer flows.** File picker integration (CLI accepts `--path`), share-target intent (export check-ins), in-app provider config (env-var sheets in Settings).
- ⚠️ **F-Droid + Play Store distribution.** Each of these is its own multi-day paperwork item.

## Operator UX

```
┌─────────────────────────────────┐
│ Mythic Vibe CLI                 │
│                                 │
│ Command (e.g. --version):       │
│ ┌─────────────────────────────┐ │
│ │ doctor --json               │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌──────┐                        │
│ │ Run  │                        │
│ └──────┘                        │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ {                           │ │
│ │   "ok": true,               │ │
│ │   "errors": [],             │ │
│ │   "warnings": []            │ │
│ │ }                           │ │
│ │                             │ │
│ │ [exit code: 0]              │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

The UI is intentionally minimal at the foundation level — operators get the full CLI surface (any subcommand, any argv) via the text input. A future session adds Material 3 polish (chip-based subcommand picker, args sheet) once the streaming + cancellation primitives are in place.

## Why an Android app at all when Termux exists?

Three operator profiles:

- **CLI-comfortable Android operator.** Already uses Termux, knows pip. Stays with the Termux install path documented in `docs/INSTALL.md`.
- **Convenience-first Android operator.** Wants a tap-to-install experience. Future Play Store / F-Droid distribution targets them; today they side-load the release APK.
- **Field-deployment Android operator.** A devops engineer running `mythic-vibe doctor --json` on a kiosk Android device wired into a sensor station — wants a single APK + auto-update via Play Store.

The app + Termux are complementary, not competing. The app's strength is the one-tap install + Material UI; Termux's strength is the full Linux shell + pip flexibility.
