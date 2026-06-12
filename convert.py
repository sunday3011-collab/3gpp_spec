#!/usr/bin/env python3
"""
3GPP .docx to Markdown converter
Uses only Python standard library (zipfile, xml.etree)
"""

import zipfile
import xml.etree.ElementTree as ET
import os
import re
import html
import sys

# Namespaces used in .docx XML
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'v': 'urn:schemas-microsoft-com:vml',
}

def get_text(elem):
    """Extract all text from a paragraph or run element."""
    texts = []
    for t in elem.findall('.//w:t', NS):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)

def get_para_style(para):
    """Get the style name of a paragraph."""
    pPr = para.find('w:pPr', NS)
    if pPr is not None:
        pStyle = pPr.find('w:pStyle', NS)
        if pStyle is not None:
            return pStyle.get('{%s}val' % NS['w'])
    return None

def get_heading_level(style_name):
    """Convert Word heading style to markdown heading level."""
    if style_name is None:
        return 0
    m = re.match(r'Heading(\d+)', style_name, re.I)
    if m:
        return int(m.group(1))
    # Intl versions
    if 'Heading' in style_name or 'heading' in style_name:
        for i in range(1, 7):
            if str(i) in style_name:
                return i
    return 0

def para_to_md(para):
    """Convert a paragraph element to markdown text."""
    style = get_para_style(para)
    level = get_heading_level(style)
    text = get_text(para).strip()
    
    if not text:
        return ''
    
    if level > 0:
        return '#' * min(level, 6) + ' ' + text
    return text

def table_to_md(table_elem):
    """Convert a table element to markdown pipe table."""
    rows = []
    for tr in table_elem.findall('w:tr', NS):
        cells = []
        for tc in tr.findall('w:tc', NS):
            cell_text = get_text(tc).strip().replace('\n', ' ')
            # Remove excessive whitespace
            cell_text = re.sub(r'\s+', ' ', cell_text)
            cells.append(cell_text)
        rows.append(cells)
    
    if not rows:
        return ''
    
    # Build markdown table
    # First row as header
    md = '| ' + ' | '.join(rows[0]) + ' |\n'
    md += '| ' + ' | '.join(['---'] * len(rows[0])) + ' |\n'
    for row in rows[1:]:
        # Pad row to same column count
        while len(row) < len(rows[0]):
            row.append('')
        md += '| ' + ' | '.join(row[:len(rows[0])]) + ' |\n'
    return md

def convert_docx_to_md(docx_path):
    """Convert a .docx file to markdown string."""
    with zipfile.ZipFile(docx_path, 'r') as z:
        # Read main document XML
        doc_xml = z.read('word/document.xml')
    
    root = ET.fromstring(doc_xml)
    
    md_lines = []
    in_table = False
    table_buffer = []
    
    # Iterate through body children
    body = root.find('w:body', NS)
    if body is None:
        return '# Conversion Error\n\nCould not find document body.\n'
    
    for child in body:
        tag = child.tag.replace('{%s}' % NS['w'], 'w:')
        
        if child.tag.endswith('}p'):  # paragraph
            if in_table:
                # Flush table buffer
                if table_buffer:
                    md_lines.append(table_to_md(table_buffer))
                table_buffer = []
                in_table = False
            
            style = get_para_style(child)
            level = get_heading_level(style)
            text = get_text(child).strip()
            
            if not text:
                md_lines.append('')
                continue
            
            if level > 0:
                md_lines.append('#' * min(level, 6) + ' ' + text)
            else:
                md_lines.append(text)
        
        elif child.tag.endswith('}tbl'):  # table
            in_table = True
            table_buffer = child
            # Convert table immediately
            md_lines.append(table_to_md(child))
            md_lines.append('')  # blank line after table
            in_table = False
            table_buffer = []
        
        else:
            # Other elements (sectPr, etc.) - skip
            pass
    
    # Flush any remaining table
    if in_table and table_buffer:
        md_lines.append(table_to_md(table_buffer))
    
    # Clean up: remove redundant blank lines
    result = []
    prev_blank = False
    for line in md_lines:
        is_blank = (line.strip() == '')
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank
    
    return '\n'.join(result)

def main():
    docs_dir = '/Users/huangyang/Desktop/3GPP_Protocols/downloads'
    md_dir = '/Users/huangyang/Desktop/3GPP_Protocols/md'
    
    # Mapping: folder name -> output file name
    mapping = {
        '38331-j20': '38.331_RRC.md',
        '38321-j20': '38.321_MAC.md',
        '38323-j10': '38.323_PDCP.md',
        '38322-j20': '38.322_RLC.md',
        '38211-j30': '38.211_PHY-Channels.md',
        '38212-j30': '38.212_PHY-Coding.md',
        '38213-j30': '38.213_PHY-Control.md',
        '38214-j30': '38.214_PHY-Data.md',
    }
    
    for folder, out_name in mapping.items():
        docx = os.path.join(docs_dir, folder, folder + '.docx')
        if not os.path.exists(docx):
            print(f'SKIP: {docx} not found')
            continue
        
        print(f'Converting: {folder}.docx -> {out_name}')
        md_content = convert_docx_to_md(docx)
        
        out_path = os.path.join(md_dir, out_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f'  -> {out_path} ({len(md_content)} chars)')
    
    print('\nDone!')

if __name__ == '__main__':
    main()
