[app]

# (str) Title of your application
title = OKO Service Tool

# (str) Package name
package.name = okotool

# (str) Package domain (needed for android/ios packaging)
package.domain = org.okosystems

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, dist, build, .git, .github, .omo, __pycache__

# (list) List of exclusions using pattern matching
source.exclude_patterns = *.spec, *.pdf, pdf_text.txt, sec6.txt, show_ctx.py, build*.py, generate_icon.py

# (str) Application versioning (method 1)
version = 2.0.0

# (list) Application requirements
# kivymd 2.x (API MDButton/MDButtonText, используемый в oko_mobile/main.py)
# pyserial — резервный канал USB OTG (/dev/ttyUSB*, /dev/ttyACM*)
requirements = python3,kivy==2.3.0,kivymd==2.0.0,materialyoucolor,pyserial

# (str) Custom source folders for requirements
# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/oko_icon.png

# (str) Icon of the application
icon.filename = %(source.dir)s/oko_icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,ARGUMENTS

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Arch to build for. Will build for armeabi-v7a by default.
# To build for multiple archs, add them here.
android.archs = arm64-v8a, armeabi-v7a

# (string) Minimum API to use. Android 5.0 (Lollipop): старые планшеты наладчиков.
android.minapi = 21

# (string) Android SDK version to use. NOTE: minimum value needed for modern
# Play publishing; device compatibility is governed by minapi above.
android.api = 33

# (string) Android NDK version to use
android.ndk = 25b

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (list) The Android permissions in the manifest. net + wifi-state for WiFi tool.
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Android logcat filters to use
#android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (str) The format used to package the app for release mode (aab or apk).
android.release_artifact = aab

# (str) The format used to package the app for debug mode (apk or aar).
android.debug_artifact = apk

# (list) Java classes to add as activities to the manifest.
#android.add_activities = com.example.ExampleActivity

# (str) OUYA Console category. Should be one of GAME or APP
#android.ouya.category = GAME

# (str) Filename of OUYA Console icon. It must be a 732x412 png image.
#android.ouya.icon.filename = %(source.dir)s/data/ouya_icon.png

# (str) XML file to include as an intent filters in <activity> tag
#android.manifest.intent_filters =

# (str) launchMode to set for the main activity
#android.manifest.launchMode = standard

# (str) screenOrientation to set for the main activity.
#android.manifest.screenOrientation = portrait

# (list) Android additional libraries to copy into libs/armeabi
#android.add_libs_armeabi = libs/android/*.so
#android.add_libs_armeabi_v7a = libs/android-v7/*.so
#android.add_libs_arm64_v8a = libs/android-v8/*.so
#android.add_libs_x86 = libs/android-x86/*.so
#android.add_libs_mips = libs/android-mips/*.so

# (list) Android additional libraries to copy into libs/armeabi
#android.add_jars = libs/android/*.jar
#android.add_aars = libs/android/*.aar

# (list) Gradle dependencies to add
#android.gradle_dependencies =

# (list) Android add gradle repositories to add
#android.gradle_repositories =

# (bool) Enable AndroidX support. Enable when 'android.gradle_dependencies'
# contains an 'androidx' package, or any package from Kotlin source.
#android.enable_androidx = False

# (string) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# (string) Python-for-android branch to use.
# v2024.01.21 зафиксирован осознанно: master собирает Python 3.14, под который
# нет колёс pyjnius (сборка падает на android_21 dry-run). Ветка 2024.01.21
# собирает Python 3.11 + NDK 25b + API 33 — проверенная связка для 1.0.
p4a.branch = v2024.01.21

# (string) Directory containing custom recipes (фикс libthorvg для NDK lib64)
p4a.local_recipes = ./p4a-recipes

# (str) FTP host to upload the distribution
#p4a.url =

# Android build notes:
# p4a v2024.01.21 generates an old jcenter() repository entry. The Android
# workflow patches it to mavenCentral() before the final Gradle packaging,
# because jcenter.bintray.com is retired.


# (str) Location of the .p4a directory. Defaults to ~/.python-for-android
#p4a.dir =

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
#build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab) storage
bin_dir = ./dist
