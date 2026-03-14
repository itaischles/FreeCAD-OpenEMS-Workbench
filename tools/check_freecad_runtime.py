from OpenEMSWorkbench import WORKBENCH_NAME, __version__


def main() -> int:
    print(f"Imported {WORKBENCH_NAME} workbench package, version {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())