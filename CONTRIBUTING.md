# Contributing

Thanks for helping improve reddit-reader.

## Issues

Open an issue for a bug or a small, focused improvement. Include the command you ran, what you expected, and what happened. Do not include Reddit tokens or other secrets.

## Pull requests

1. Fork the repository and create a focused branch.
2. Keep the tool local, low-volume, and manual-write only. Do not add voting, bulk posting, scraping, or automated comments.
3. Run a syntax check before opening the pull request:

   ```sh
   python -m py_compile reddit_reader.py
   ```

4. Explain what changed and how you tested it.

Please keep commits authored as yourself. Repository commits made by the maintainer use the `tahodev` identity.
