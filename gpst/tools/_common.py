


import logging
from pathlib import Path


def verify_in_path(in_path: Path) -> bool:
    if not in_path.exists():
        logging.error(f"Input file '{in_path}' does not exist.")
        return False
    
    if in_path.suffix.lower() not in ('.fit', '.gpx'):
        logging.error(f"Input file '{in_path}' is not a FIT or GPX file.")
        return False

    return True


def verify_out_path(out_path: Path, accept: bool) -> bool:
    if out_path.suffix.lower() != '.gpx':
        logging.error(f"Output file '{out_path}' is not a GPX file.")
        return False

    if out_path.exists():
        logging.warning(f"Output file '{out_path}' already exists and will be overwritten.")

        if not accept:
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
