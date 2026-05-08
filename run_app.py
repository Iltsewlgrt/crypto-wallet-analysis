"""PyInstaller-friendly entrypoint.

Keeps a stable top-level script so we can build an .exe without relying on
`python -m app.main` module execution.
"""

from app.main import main


if __name__ == "__main__":
    main()
