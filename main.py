import sys

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
        yield title, page_number


def main():
    try:
        pdf_path = sys.argv[1]
        reader = PdfReader(pdf_path)
    
        for title, page_number in chapter_entries(reader):
            print(f"{title} - page {page_number}")
    except IndexError:
        print("Expected usage: main.py <pdf_path>")


if __name__ == "__main__":
    main()
