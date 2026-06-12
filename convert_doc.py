#!/usr/bin/env python3
"""
Convert .doc (OLE format) to Markdown by extracting text strings.
Works for simple .doc files like 3GPP specifications.
"""

import re
import os

def extract_text_from_doc(doc_path):
    """Extract readable text from a .doc file using string extraction."""
    with open(doc_path, 'rb') as f:
        data = f.read()
    
    # Extract ASCII/UTF-8 readable strings (min length 4)
    strings = []
    current = b''
    for b in data:
        if 32 <= b < 127 or b == 10 or b == 13 or b == 9:
            current += bytes([b])
        else:
            if len(current) >= 4:
                s = current.decode('ascii', errors='ignore').strip()
                if s:
                    strings.append(s)
            current = b''
    
    # Also try to extract Unicode strings (UTF-16 LE, common in .doc files)
    unicode_strings = []
    i = 0
    while i < len(data) - 1:
        # Look for UTF-16 LE strings (pairs of bytes where second byte is 0)
        chars = []
        while i < len(data) - 1:
            char_code = data[i] | (data[i+1] << 8)
            if 32 <= char_code < 65536 and char_code != 0xFFFD:
                # Filter out surrogate characters
                if 0xD800 <= char_code <= 0xDFFF:
                    chars.append('?')
                else:
                    chars.append(chr(char_code))
                i += 2
            else:
                break
        if len(chars) >= 4:
            s = ''.join(chars).strip()
            if s and not all(c in ' \t\n\r' for c in s):
                unicode_strings.append(s)
        i += 1
    
    return strings, unicode_strings

def clean_text(text):
    """Clean up extracted text."""
    # Remove control characters except newline
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text

def identify_headings(lines):
    """Try to identify headings from the text."""
    headings = set()
    
    # Look for common heading patterns in 3GPP docs
    for line in lines:
        line = line.strip()
        # Chapter/section headings like "1. General description"
        if re.match(r'^\d+(\.\d+)*\s+[A-Z]', line) and len(line) < 100:
            headings.add(line)
        # All-caps short lines (likely headings)
        elif line.isupper() and 5 < len(line) < 80 and not line.startswith('http'):
            headings.add(line)
    
    return headings

def convert_doc_to_markdown(doc_path, output_path):
    """Convert a .doc file to Markdown."""
    print(f"Converting: {doc_path}")
    
    # Extract text
    ascii_strings, unicode_strings = extract_text_from_doc(doc_path)
    print(f"  Extracted {len(ascii_strings)} ASCII strings")
    print(f"  Extracted {len(unicode_strings)} Unicode strings")
    
    # Combine and deduplicate
    all_strings = []
    seen = set()
    for s in ascii_strings + unicode_strings:
        s = clean_text(s)
        if s and s not in seen and len(s) > 3:
            all_strings.append(s)
            seen.add(s)
    
    # Identify potential headings
    heading_set = identify_headings(all_strings)
    
    # Build Markdown content
    md_lines = []
    md_lines.append(f"# {all_strings[0] if all_strings else '3GPP TS 38.201'}")
    md_lines.append("")
    
    # Process strings and format as Markdown
    in_content = False
    prev_was_heading = False
    
    for s in all_strings:
        # Skip TOC references and page numbers
        if re.match(r'^PAGEREF|^TOC|^HYPERLINK|^\d+$', s):
            continue
        
        # Skip copyright boilerplate that appears multiple times
        if 'Organizational Partners' in s and len(s) > 200:
            continue
        
        # Check if this is a heading
        is_heading = s in heading_set or (s.isupper() and 5 < len(s) < 80)
        
        if is_heading and not prev_was_heading:
            # Determine heading level
            if re.match(r'^\d+(\.\d+)*\s', s):
                # Has section number, use appropriate level
                level = s.count('.') + 1
                if level > 3:
                    level = 3
                md_lines.append(f"{'#' * level} {s}")
            else:
                md_lines.append(f"## {s}")
            md_lines.append("")
            prev_was_heading = True
        else:
            md_lines.append(s)
            md_lines.append("")
            prev_was_heading = False
    
    # Write output
    with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write('\n'.join(md_lines))
    
    print(f"  Output: {output_path}")
    print(f"  Size: {os.path.getsize(output_path)} bytes")

if __name__ == '__main__':
    import sys
    
    downloads_dir = '/Users/huangyang/Desktop/3GPP_Protocols/downloads'
    md_dir = '/Users/huangyang/Desktop/3GPP_Protocols/md'
    
    # Convert 38201-j00
    doc_file = os.path.join(downloads_dir, '38201-j00', '38201-j00.doc')
    output_file = os.path.join(md_dir, '38.201_PHY_General_j00.md')
    
    if os.path.exists(doc_file):
        convert_doc_to_markdown(doc_file, output_file)
    else:
        print(f"File not found: {doc_file}")
