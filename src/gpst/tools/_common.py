from pathlib import Path
from ..utils.logger import logger


def verify_in_path(in_path: Path) -> bool:
    if not in_path.exists():
        logger.error(f"Input file '{in_path}' does not exist.")
        return False
    
    if in_path.suffix.lower() not in ('.fit', '.gpx'):
        logger.error(f"Input file '{in_path}' is not a FIT or GPX file.")
        return False

    return True


def verify_out_path(out_path: Path, accept: bool) -> bool:
    if out_path.suffix.lower() != '.gpx':
        logger.error(f"Output file '{out_path}' is not a GPX file.")
        return False

    if out_path.exists():
        logger.warning(f"Output file '{out_path}' already exists and will be overwritten.")

        if not accept:
            confirm = 'n'
            try:
                confirm = input("Do you want to continue? (y/N): ")
            except KeyboardInterrupt:
                print()
            finally:
                if confirm.lower() != 'y':
                    logger.info("Operation cancelled by user.")
                    return False

    return True
