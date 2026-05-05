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

    buildTypes {
        release {
            isMinifyEnabled = false        // Compose + Python embedding don't play nicely with R8
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
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
