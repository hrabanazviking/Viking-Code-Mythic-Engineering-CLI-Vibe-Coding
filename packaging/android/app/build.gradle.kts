// Android app module (PH-22.2 foundation).
//
// Embeds mythic-vibe-cli via Chaquopy. The activity invokes
// the CLI's main() in a coroutine and streams output to a
// Compose Text composable. The runtime is the same Python +
// CLI bytes a pip install delivers — no Android-specific
// fork of the project.

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}

// PH-23.5 (additive 2026-05-05) — APK signing config. Reads
// keystore credentials from project properties + env vars so
// the keystore + passwords NEVER land in the source tree.
//
// Three sources, in priority order:
//   1. Project properties (e.g. -PmythicReleaseStorePassword=...)
//   2. Environment variables (ANDROID_KEYSTORE_PASSWORD etc.)
//   3. None — falls back to unsigned release (foundation behavior)
//
// The release-android.yml workflow uses path #2: it decodes a
// base64'd keystore from the ANDROID_KEYSTORE_BASE64 secret and
// sets the four env vars below before running assembleRelease.
//
// Operators creating a fresh keystore should follow
// `packaging/android/SIGNING.md`.
val mythicReleaseStoreFile: String? =
    (project.findProperty("mythicReleaseStoreFile") as String?)
        ?: System.getenv("ANDROID_KEYSTORE_FILE")
val mythicReleaseStorePassword: String? =
    (project.findProperty("mythicReleaseStorePassword") as String?)
        ?: System.getenv("ANDROID_KEYSTORE_PASSWORD")
val mythicReleaseKeyAlias: String? =
    (project.findProperty("mythicReleaseKeyAlias") as String?)
        ?: System.getenv("ANDROID_KEY_ALIAS")
val mythicReleaseKeyPassword: String? =
    (project.findProperty("mythicReleaseKeyPassword") as String?)
        ?: System.getenv("ANDROID_KEY_PASSWORD")

val mythicReleaseSigningAvailable: Boolean = listOf(
    mythicReleaseStoreFile,
    mythicReleaseStorePassword,
    mythicReleaseKeyAlias,
    mythicReleaseKeyPassword,
).all { !it.isNullOrEmpty() }

android {
    namespace = "dev.mythicvibe.android"
    compileSdk = 34

    defaultConfig {
        applicationId = "dev.mythicvibe.android"
        minSdk = 26              // Android 8.0+ for Compose + Chaquopy
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        // ABI filters — Chaquopy ships per-arch CPython. The
        // four ABIs below cover essentially every Android device
        // shipped since 2019. armeabi-v7a is the legacy 32-bit
        // ARM target; arm64-v8a is the modern phone default.
        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
        }
    }

    signingConfigs {
        // Foundation rule: the signing config exists at this
        // level so the release buildType below can always
        // reference it; if no keystore is configured, the
        // signingConfig is left null and the APK is unsigned.
        if (mythicReleaseSigningAvailable) {
            create("release") {
                storeFile = file(mythicReleaseStoreFile!!)
                storePassword = mythicReleaseStorePassword
                keyAlias = mythicReleaseKeyAlias
                keyPassword = mythicReleaseKeyPassword
                // Both v1 (JAR) + v2 (APK Signature Scheme v2)
                // are enabled by default in AGP 8.x. Explicitly
                // enabling v3 + v4 would require additional setup
                // (rotated keys for v3, idsig sidecars for v4) —
                // a future session can add those incrementally.
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false        // Compose + Python embedding don't play nicely with R8
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // Wire in the signing config when keystore credentials
            // are available; otherwise the release APK is unsigned
            // (matches the PH-22.2 foundation behavior so operators
            // without keystore secrets still get a working build).
            if (mythicReleaseSigningAvailable) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }
}

chaquopy {
    defaultConfig {
        version = "3.12"
        // pip install mythic-vibe-cli at APK build time so the
        // wheel + its stdlib-only deps are baked into the APK.
        // No first-run network IO required (unlike the launcher).
        pip {
            install("mythic-vibe-cli")
        }
    }
}

dependencies {
    // Compose BOM — single version pin for every Compose artifact.
    implementation(platform("androidx.compose:compose-bom:2024.09.03"))
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
