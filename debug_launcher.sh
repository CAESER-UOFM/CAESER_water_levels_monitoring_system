#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../.."
source "$SCRIPT_DIR/../venv/bin/activate"
osascript -e 'tell app "Terminal" to do script "cd '"$SCRIPT_DIR/../.."' && source '"$SCRIPT_DIR/../venv/bin/activate"' && python main.py && echo \"Press Enter to exit...\" && read"'
