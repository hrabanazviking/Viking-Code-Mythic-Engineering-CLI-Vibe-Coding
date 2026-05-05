// Android Gradle settings (PH-22.2 foundation).
//
// Single-module Android project. The `app` module embeds
// mythic-vibe-cli via the Chaquopy plugin and exposes the CLI
// as a native Android UI.

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        // Chaquopy plugin lives in its own Maven repo.
        maven { url = uri("https://chaquo.com/maven") }
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven { url = uri("https://chaquo.com/maven") }
    }
}

rootProject.name = "mythic-vibe-android"
include(":app")
