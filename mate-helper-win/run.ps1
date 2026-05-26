#!/usr/bin/env powershell
# Mate Helper - Iniciar no Windows
$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$DIR/desktop_pet/main.py"
