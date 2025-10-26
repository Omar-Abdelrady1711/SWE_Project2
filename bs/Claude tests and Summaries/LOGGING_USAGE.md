# Logging Framework Usage Guide

## Environment Variables

### LOG_LEVEL
- `0` = Silent mode (only CRITICAL messages)
- `1` = Info mode (INFO, WARNING, ERROR, CRITICAL)  
- `2` = Debug mode (all messages including DEBUG)
- Default: `0` if not set

### LOG_FILE  
- Optional: Path to log file
- If set: Logs to both file AND console
- If not set: Logs only to console

## Usage Examples

### Command Line
```bash
# Silent mode (default)
./run URL_FILE

# Info mode  
LOG_LEVEL=1 ./run URL_FILE

# Debug mode with file logging
LOG_LEVEL=2 LOG_FILE=/tmp/acme.log ./run URL_FILE

# Test with debug logging
LOG_LEVEL=2 ./run test
```

### In Python Code
```python
from acemcli.logging_setup import setup_logging
import logging

# Set up logging (call this once at start of each command)
setup_logging()

# Get logger for your module
logger = logging.getLogger("my_module")

# Use throughout your code
logger.debug("Detailed debugging info")
logger.info("General information")  
logger.warning("Something might be wrong")
logger.error("Something is wrong")
logger.critical("Something is very wrong")
```

## Integration Points

Your logging framework integrates with:
- `./run install` command
- `./run URL_FILE` command  
- `./run test` command
- All team member modules (Luis, Sebastian, Dwijay)
- Metric calculation functions
- Error handling throughout the system

## Testing

Run the verification:
```bash
python3 verify_logging.py
```

See demonstration:
```bash  
python3 final_logging_demo.py
```
