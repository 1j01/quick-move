#!/bin/bash

# This script is intended to be used with the zhoufeng.pyqt-integration VS Code extension,
# when Qt Designer is installed as a Flatpak application.

# Usage:
# Copy the path to this script and paste it into the "pyqt-integration.qtdesigner.path" setting.

# Check if Flatpak is installed
if ! command -v flatpak &> /dev/null; then
    echo "Flatpak is not installed. Please install Flatpak and Qt Designer first."
    exit 1
fi

# Define the path to the Qt Designer Flatpak application
APP_ID="io.qt.Designer"

# Check if the Flatpak application is installed
if ! flatpak list | grep -q "$APP_ID"; then
    echo "Qt Designer Flatpak application is not installed. Please install it."
    exit 1
fi

# Check if a file was provided as an argument
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_ui_file>"
    exit 1
fi

# Launch Qt Designer with the provided file
flatpak run --branch=stable --arch=x86_64 --command=designer --file-forwarding "$APP_ID" @@ "$1" @@
