# Zeemo Clone — Android APK Project

This package contains the complete Kivy + Buildozer Android project for the Zeemo-style Auto-Caption App.

## Option 1: Build APK Automatically on GitHub (Easiest — No Linux Setup Needed)
1. Create a new repository on GitHub and upload all files from this folder (including the hidden `.github/workflows/build_apk.yml` folder).
2. Open the **Actions** tab in your GitHub repository and run **Build Android APK** (or it runs automatically on push).
3. Wait ~10–15 minutes, then download the compiled `.apk` from **Artifacts -> zeemo-clone-apk**.
4. Install the `.apk` on your Android phone.

## Option 2: Build APK on Ubuntu / Google Colab
```bash
sudo apt-get update && sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip install buildozer cython
buildozer android debug
```
The compiled `.apk` will appear in `bin/`.
