


import logging
from pathlib import Path


def verify_out_path(out_path: Path) -> bool:
    if out_path.suffix.lower() != '.gpx':
        logging.error(f"Output file '{out_path}' is not a GPX file.")
        return False

    if out_path.exists():
        logging.warning(f"Output file '{out_path}' already exists and will be overwritten.")

        confirm = 'n'
        try:
            confirm = input("Do you want to continue? (y/N): ")
        except KeyboardInterrupt:
            print()
        finally:
            if confirm.lower() != 'y':
                logging.info("Operation cancelled by user.")
                return False
    return True
