# ProGuard rules for the mythic-vibe Android wrapper (PH-22.2).
#
# Release builds set isMinifyEnabled = false so these rules are
# advisory — they take effect only if a future session enables
# R8/ProGuard. The reason minification stays off today: Chaquopy's
# Python embedding + Compose's reflection metadata don't play
# nicely with aggressive code shrinking.

# Keep Chaquopy's reflection entry points.
-keep class com.chaquo.python.** { *; }
-keep class com.chaquo.python.android.** { *; }

# Keep our Compose UI classes.
-keep class dev.mythicvibe.android.** { *; }
