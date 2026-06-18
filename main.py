import argparse
import re

from pypdf import PdfReader


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("chapter_number", nargs="?", type=int)
    args = parser.parse_args()

    reader = PdfReader(args.pdf_path)

    if args.chapter_number is not None:
        print(chapter_text(reader, args.chapter_number))
        return

    for chapter in chapter_entries(reader):
        print(f"{chapter['title']} - page {chapter['page_number']}")


if __name__ == "__main__":
    main()
