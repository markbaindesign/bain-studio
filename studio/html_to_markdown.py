#!/usr/bin/env python3
"""
Convert HTML files or URLs to markdown format for agent consumption.

Supports:
- Local HTML files
- URLs (via urllib)
- Preserves structure, headers, lists, links, images

Usage:
    python3 html_to_markdown.py <url_or_path> [-o output.md]
    python3 html_to_markdown.py https://example.com/page.html
    python3 html_to_markdown.py /path/to/file.html -o output.md
"""

import sys
import os
import argparse
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request

try:
    from html2text import HTML2Text
except ImportError:
    print("ERROR: html2text library not found. Install with: pip install html2text")
    sys.exit(1)


def fetch_html_from_url(url):
    """Fetch HTML content from a URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"ERROR: Failed to fetch URL '{url}': {e}", file=sys.stderr)
        sys.exit(1)


def read_html_file(path):
    """Read HTML content from a local file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def is_url(string):
    """Check if a string is a valid URL."""
    try:
        result = urlparse(string)
        return result.scheme in ('http', 'https')
    except:
        return False


def html_to_markdown(html_content, url=None):
    """Convert HTML content to markdown."""
    converter = HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.ignore_emphasis = False
    converter.body_width = 0  # Don't wrap lines
    converter.unicode_snob = True
    converter.use_automatic_links = True

    # Convert to markdown
    markdown = converter.handle(html_content)

    # Clean up excessive blank lines
    lines = markdown.split('\n')
    cleaned = []
    prev_blank = False
    for line in lines:
        if line.strip() == '':
            if not prev_blank:
                cleaned.append(line)
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    return '\n'.join(cleaned).strip()


def main():
    parser = argparse.ArgumentParser(
        description='Convert HTML files or URLs to markdown format for agent consumption.'
    )
    parser.add_argument(
        'source',
        help='URL or local file path to convert'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: stdout)'
    )

    args = parser.parse_args()

    # Get HTML content
    if is_url(args.source):
        html_content = fetch_html_from_url(args.source)
    else:
        html_content = read_html_file(args.source)

    # Convert to markdown
    markdown = html_to_markdown(html_content, url=args.source)

    # Output result
    if args.output:
        try:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(markdown)
            print(f"Markdown written to: {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Failed to write to '{args.output}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(markdown)


if __name__ == '__main__':
    main()
