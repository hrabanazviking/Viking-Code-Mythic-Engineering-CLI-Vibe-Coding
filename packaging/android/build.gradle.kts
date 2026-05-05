// Top-level Android build (PH-22.2 foundation).
//
// Plugins are declared `apply false` here so subprojects can
// pull them in without the root project's classpath getting
// polluted. Versions are pinned so a future Gradle bump is an
// explicit edit, not a silent CI break.

plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "2.0.20" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.20" apply false
    // Chaquopy embeds CPython into the APK. Pinned to the latest
    // release that supports Python 3.12 + AGP 8.5+.
    id("com.chaquo.python") version "16.0.0" apply false
}
