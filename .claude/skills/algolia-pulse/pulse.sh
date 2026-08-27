#!/bin/bash
# Wrapper script for Algolia Pulse skill

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SKILL_DIR/algolia_pulse.py"

# Default config location
CONFIG="${ALGOLIA_PULSE_CONFIG:-$HOME/.algolia/pulse-config.json}"

# Parse arguments
DRY_RUN=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run the Python script
python3 "$SCRIPT" --config "$CONFIG" $DRY_RUN $VERBOSE
