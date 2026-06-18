import argparse
import asyncio
import re
import sys
import wave
from pathlib import Path

from pypdf import PdfReader

from tts_text_model import DEFAULT_MODEL, text_for_tts


PCM_SAMPLE_RATE = 24_000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH_BYTES = 2


def chapter_entries(reader):
    for item in reader.outline:
        if isinstance(item, list):
            continue

        title = getattr(item, "title", "")
        if not title.startswith("Chapter "):
            continue

        page_index = reader.get_destination_page_number(item)
        page_number = reader.page_labels[page_index]
        yield {
            "title": title,
            "page_index": page_index,
            "page_number": page_number,
        }


def clean_page_lines(text, page_number):
    lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line == str(page_number):
            continue

        if re.fullmatch(r"\d+\s*\|\s*Chapter \d+:.*", line):
            continue

        if re.fullmatch(r".+\s*\|\s*\d+", line):
            continue

        line = line.removesuffix("•").strip()
        lines.append(line)

    return lines


def clean_chapter_text(text):
    text = re.sub(r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]", "", text)
    text = DEFAULT_MODEL.fix_pdf_text_artifacts(text)
    text = re.sub(r"\bY\s+ou\b", "You", text)
    text = re.sub(r"\bY\s+our\b", "Your", text)
    text = re.sub(r"\bY\s+ear\b", "Year", text)
    text = re.sub(r"\bY\s+ears\b", "Years", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def merge_wrapped_lines(lines):
    paragraphs = []
    current = []

    for line in lines:
        if line in {"References", "References and Further Reading"}:
            break

        if current and current[-1].endswith(("‐", "-", "\u00ad")):
            current[-1] = current[-1].rstrip("‐-\u00ad") + line
        elif is_paragraph_break(line, current):
            paragraphs.append(" ".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def is_paragraph_break(line, current):
    if not current:
        return False

    previous = current[-1]

    if line.startswith("• "):
        return True

    if (
        current[0].startswith("• ")
        and previous.endswith((".", "?", "!", ")"))
        and not line.startswith("• ")
    ):
        return True

    if not current[0].startswith("• ") and looks_like_heading(previous):
        return True

    if previous.endswith((".", "?", "!", ":", "”")) and looks_like_heading(line):
        return True

    return False


def looks_like_heading(line):
    if len(line) > 80:
        return False

    if line.startswith(("CHAPTER ", "• ")):
        return True

    if line.endswith((".", ",", ";")):
        return False

    words = line.split()
    if not words:
        return False

    uppercase_or_titlecase = sum(
        word[:1].isupper() or word[:1].isdigit() for word in words
    )
    return uppercase_or_titlecase / len(words) >= 0.7


def chapter_text(reader, chapter_number):
    chapters = list(chapter_entries(reader))
    chapter = next(
        (
            entry
            for entry in chapters
            if entry["title"].startswith(f"Chapter {chapter_number}.")
        ),
        None,
    )

    if chapter is None:
        raise ValueError(f"Could not find chapter {chapter_number}")

    chapter_position = chapters.index(chapter)
    start_page = chapter["page_index"]
    end_page = (
        chapters[chapter_position + 1]["page_index"]
        if chapter_position + 1 < len(chapters)
        else len(reader.pages)
    )

    lines = []
    for page_index in range(start_page, end_page):
        page_text = reader.pages[page_index].extract_text() or ""
        page_number = reader.page_labels[page_index]
        lines.extend(clean_page_lines(page_text, page_number))

    return clean_chapter_text(merge_wrapped_lines(lines))


def chapter_number_from_title(title):
    match = re.match(r"Chapter\s+(\d+)\.", title)
    if match is None:
        raise ValueError(f"Could not parse chapter number from {title!r}")
    return int(match.group(1))


def safe_filename(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "chapter"


def default_output_path(pdf_path, chapters):
    pdf_path = Path(pdf_path)
    if len(chapters) == 1:
        chapter = chapters[0]
        chapter_number = chapter_number_from_title(chapter["title"])
        chapter_slug = safe_filename(chapter["title"])
        return pdf_path.with_name(f"{pdf_path.stem}-{chapter_number:02d}-{chapter_slug}.wav")
    return pdf_path.with_suffix(".wav")


def open_wav(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    wav_file = wave.open(str(path), "wb")
    try:
        wav_file.setnchannels(PCM_CHANNELS)
        wav_file.setsampwidth(PCM_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(PCM_SAMPLE_RATE)
        return wav_file
    except Exception:
        wav_file.close()
        raise


async def synthesize_chapters(reader, chapters, output_path, voice, speed, overwrite):
    from trillim import TTS

    if output_path.exists() and not overwrite:
        print(f"skipping existing {output_path}", file=sys.stderr)
        return

    tts = TTS()
    await tts.start()
    try:
        with open_wav(output_path) as wav_file:
            async with tts.open_session(voice=voice, speed=speed) as session:
                for chapter in chapters:
                    chapter_number = chapter_number_from_title(chapter["title"])
                    print(f"synthesizing {chapter['title']}", file=sys.stderr)
                    text = text_for_tts(chapter_text(reader, chapter_number))
                    async for pcm_audio in session.synthesize(text):
                        wav_file.writeframes(pcm_audio)
        print(f"wrote {output_path}", file=sys.stderr)
    finally:
        await tts.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("chapter_number", nargs="?", type=int)
    parser.add_argument("--list", action="store_true", help="list chapter names and page numbers")
    parser.add_argument("--output", type=Path, help="output WAV path")
    parser.add_argument("--voice", default="alba", help="Trillim voice to use")
    parser.add_argument("--speed", type=float, default=1.0, help="speech speed")
    parser.add_argument("--overwrite", action="store_true", help="overwrite an existing WAV file")
    args = parser.parse_args()

    reader = PdfReader(args.pdf_path)
    chapters = list(chapter_entries(reader))

    if args.list:
        for chapter in chapters:
            print(f"{chapter['title']} - page {chapter['page_number']}")
        return

    if args.chapter_number is None:
        selected_chapters = chapters
    else:
        selected_chapters = [
            chapter
            for chapter in chapters
            if chapter["title"].startswith(f"Chapter {args.chapter_number}.")
        ]
        if not selected_chapters:
            raise ValueError(f"Could not find chapter {args.chapter_number}")

    output_path = args.output or default_output_path(args.pdf_path, selected_chapters)
    asyncio.run(
        synthesize_chapters(
            reader,
            selected_chapters,
            output_path,
            args.voice,
            args.speed,
            args.overwrite,
        )
    )


if __name__ == "__main__":
    main()
