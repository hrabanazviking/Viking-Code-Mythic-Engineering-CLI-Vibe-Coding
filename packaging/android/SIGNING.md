# Android APK signing — maintainer guide

PH-23.5 — how to provision the keystore + secrets the
`release-android.yml` workflow needs to produce a signed
release APK.

> **Status:** signing config wired into `app/build.gradle.kts`
> + `release-android.yml` (PH-23.5, 2026-05-05). Without the
> ANDROID_KEYSTORE_* secrets configured, the workflow falls
> back to an unsigned APK (matches PH-22.2 foundation
> behavior) so the pipeline stays useful before the maintainer
> provisions the keystore.

---

## Why APK signing matters

Android's package manager refuses to install an unsigned APK
unless the user explicitly enables "Install from unknown
sources" + "Install unknown apps" for the source app (browser,
file manager, etc.). For maintainer-side debugging via `adb
install` this is fine; for end-users downloading the APK from
a release page or sideload-friendly distribution channel
(e.g. F-Droid), an unsigned APK is functionally a non-starter.

Signing also enables APK update mechanics: Android's package
manager only allows updates from APKs signed with the **same**
key as the originally-installed version. Loss of the signing
key = loss of upgrade path for every existing user — which is
why the keystore lives in repo secrets, not in source.

---

## One-time keystore creation

```bash
# Adjust validity (years) + alias to taste. The defaults are
# AGP-recommended.
keytool -genkey -v \
    -keystore mythic-release.jks \
    -keyalg RSA \
    -keysize 4096 \
    -validity 10000 \
    -alias mythic-release-key \
    -storepass <STRONG_RANDOM_PASSWORD> \
    -keypass <STRONG_RANDOM_PASSWORD>
```

`keytool` is bundled with every JDK install. You'll be
prompted for the cert subject (Distinguished Name) — use
something durable like:

> CN=Mythic Vibe Contributors, OU=Releases, O=Mythic Vibe,
> L=(your city), ST=(your state), C=(your country)

The `validity` of 10000 days is ~27 years — APK signing keys
are forever, so generous expiry is correct.

**The `mythic-release.jks` file is now your single source of
truth for app signing. Lose it and every existing installed
copy of the app loses its upgrade path.** Back up the file +
both passwords to a secure location (password manager,
encrypted cloud backup, etc.) before proceeding.

---

## Configuring repo secrets

The `release-android.yml` workflow reads four secrets:

| Secret | Value |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | `cat mythic-release.jks \| base64 -w 0` (one line, no wrapping) |
| `ANDROID_KEYSTORE_PASSWORD` | The `-storepass` value above |
| `ANDROID_KEY_ALIAS` | `mythic-release-key` (or whatever `-alias` you chose) |
| `ANDROID_KEY_PASSWORD` | The `-keypass` value above |

Configure each at `Settings → Secrets and variables → Actions
→ New repository secret`.

The `-w 0` flag on `base64` produces a single-line output;
GitHub's secrets store accepts multi-line values too, but
single-line is the more reliable shape for the workflow's
`base64 -d` decode step.

---

## Verifying a signed APK

After the workflow runs against a tag push, download the APK
from the GitHub Release and verify:

```bash
# apksigner ships with the Android SDK build-tools.
apksigner verify --print-certs mythic-vibe-1.0.0-android.apk
```

A successful verify prints the certificate chain. The
certificate fingerprints (SHA-1, SHA-256, SHA-512) should
match the ones from your local keystore:

```bash
keytool -list -v -keystore mythic-release.jks -alias mythic-release-key
```

---

## Local signed builds (without CI)

If you want to build a signed APK on your workstation:

```bash
# Inside packaging/android/:
./gradlew assembleRelease \
    -PmythicReleaseStoreFile=/path/to/mythic-release.jks \
    -PmythicReleaseStorePassword=... \
    -PmythicReleaseKeyAlias=mythic-release-key \
    -PmythicReleaseKeyPassword=...
```

The `-P` flags map to Gradle project properties; `app/build.
gradle.kts` reads them in priority order over the environment
variables, so a workstation build doesn't conflict with the
CI env-var path.

---

## Upgrade-path policy

Per Android's signing model, **the same keystore must sign
every release**. To rotate:

1. Generate a new keystore.
2. Use `apksigner` with both the old + new keys to ship a
   "lineage-rotation" APK that tells Android to accept future
   updates signed with the new key.
3. Subsequent releases sign with the new key only.

Rotation is rare (typically only when the original key is
compromised). The lineage-rotation flow is well-documented in
the Android developer docs but out of scope for this guide —
ping the maintainer if a rotation is needed.

---

## What this signing does NOT cover

- **Sigstore signatures** over the APK bytes — that's PH-21.5,
  applied at the workflow level, separate from Android's APK
  signing scheme. Both run; both serve different purposes
  (Sigstore proves who built it; APK signing proves Android's
  install-time check passes).
- **Play Store Play App Signing** — when uploading to Play
  Store you can opt into Google managing the signing key on
  your behalf. That's a separate Play Console workflow not
  yet wired into this project; future PH-22.2.x slice.
- **F-Droid reproducible builds** — F-Droid prefers
  reproducible builds where they can re-sign from source.
  Out of scope today; future v2.x slice.
