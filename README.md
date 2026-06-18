# Audiobooks

Convert PDF chapters into WAV audiobooks.

This is a small CLI for extracting chapter text from PDF outlines, cleaning it for
text-to-speech, and synthesizing audio with Trillim. It can generate a full-book
WAV or a single chapter WAV.

## Requirements

- Python 3.14 or newer
- `uv` for dependency management
- Any local/system prerequisites required by `trillim[voice]`

## Installation

```bash
uv sync
```

## Usage

List the chapters detected from the PDF outline:

```bash
uv run python main.py book.pdf --list
```

Create a WAV file for the whole PDF:

```bash
uv run python main.py book.pdf
```

Create a WAV file for one chapter:

```bash
uv run python main.py book.pdf 3
```

Write to a specific output path:

```bash
uv run python main.py book.pdf 3 --output output/chapter-03.wav
```

Tune voice, speed, and parallel chapter synthesis:

```bash
uv run python main.py book.pdf --voice alba --speed 1.1 --jobs 4
```

By default, existing output files are skipped. Use `--overwrite` to replace them:

```bash
uv run python main.py book.pdf --overwrite
```

## PDF Expectations

The converter reads the PDF outline/table of contents and looks for entries named
like `Chapter 1.`. PDFs without usable chapter outline entries will not produce
chapter output.

Generated audio is written as mono 24 kHz, 16-bit PCM WAV.

## CLI Options

- `pdf_path`: PDF file to convert.
- `chapter_number`: Optional chapter number to synthesize.
- `--list`: Print detected chapters and page numbers.
- `--output`: Output WAV path.
- `--voice`: Trillim voice name. Defaults to `alba`.
- `--speed`: Speech speed multiplier. Defaults to `1.0`.
- `--jobs`: Number of chapter synthesis processes for full-book output. Defaults to `4`.
- `--overwrite`: Replace an existing output file.

## License

MIT. See [LICENSE](LICENSE).
