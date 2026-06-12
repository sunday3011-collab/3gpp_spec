#!/usr/bin/env python3
"""
Convert 3GPP .docx files to Markdown.
Handles multiple .docx files per spec (combines them).
"""

import zipfile
import xml.etree.ElementTree as ET
import os
import sys
import glob

def docx_to_markdown(docx_path):
    """Convert a .docx file to markdown text."""
    with zipfile.ZipFile(docx_path, 'r') as z:
        # Read document.xml
        xml_content = z.read('word/document.xml')
    
    # Parse XML
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    root = ET.fromstring(xml_content)
    
    md_lines = []
    in_table = False
    table_rows = []
    
    def process_para(para):
        nonlocal in_table, table_rows
        # Get paragraph text
        texts = []
        for r in para.findall('.//w:r', ns):
            for t in r.findall('w:t', ns):
                if t.text:
                    texts.append(t.text)
        
        para_text = ''.join(texts).strip()
        if not para_text:
            return ''
        
        # Detect heading style
        pstyle = para.find('.//w:pStyle', ns)
        style = pstyle.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') if pstyle is not None else ''
        
        # Map heading styles
        if style and style.startswith('Heading'):
            level = style.replace('Heading', '')
            try:
                lv = int(level)
                if lv <= 6:
                    return '#' * lv + ' ' + para_text
            except:
                pass
        
        # Check for bold/italic (simplified)
        return para_text
    
    def process_table(table_elem):
        """Process a table element and return markdown table."""
        rows = []
        for tr in table_elem.findall('.//w:tr', ns):
            cells = []
            for tc in tr.findall('.//w:tc', ns):
                # Get cell text
                cell_texts = []
                for r in tc.findall('.//w:r', ns):
                    for t in r.findall('w:t', ns):
                        if t.text:
                            cell_texts.append(t.text)
                cells.append(''.join(cell_texts).strip())
            rows.append(cells)
        
        if not rows:
            return ''
        
        # Build markdown table
        md = []
        # Header row
        md.append('| ' + ' | '.join(rows[0]) + ' |')
        # Separator
        md.append('| ' + ' | '.join(['---'] * len(rows[0])) + ' |')
        # Data rows
        for row in rows[1:]:
            # Pad row to match header length
            while len(row) < len(rows[0]):
                row.append('')
            md.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(md)
    
    # Process body
    body = root.find('.//w:body', ns)
    if body is None:
        return ''
    
    for child in body:
        tag = child.tag.replace('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}', '')
        
        if tag == 'p':  # Paragraph
            # Check if paragraph is inside a table (skip, handled by table)
            parent = child.getparent() if hasattr(child, 'getparent') else None
            md = process_para(child)
            if md:
                md_lines.append(md)
                md_lines.append('')  # Empty line
        
        elif tag == 'tbl':  # Table
            tbl_md = process_table(child)
            if tbl_md:
                md_lines.append(tbl_md)
                md_lines.append('')
    
    return '\n'.join(md_lines)

def find_docx_files(unzip_dir):
    """Find all .docx files in unzipped directory."""
    docx_files = []
    for f in os.listdir(unzip_dir):
        if f.endswith('.docx'):
            docx_files.append(os.path.join(unzip_dir, f))
    return sorted(docx_files)

def main():
    downloads_dir = '/Users/huangyang/Desktop/3GPP_Protocols/downloads'
    md_dir = '/Users/huangyang/Desktop/3GPP_Protocols/md'
    
    # Protocol name mapping
    name_map = {
        '37213-j00': '37.213_Shared_Spectrum',
        '38101-1-j50': '38.101-1_RF_Requirements_FR1',
        '38101-2-j40': '38.101-2_RF_Requirements_FR2',
        '38101-3-j50': '38.101-3_RF_Requirements_Interworking',
        '38101-4-j22': '38.101-4_RF_Performance',
        '38201-j00': '38.201_PHY_General',
        '38202-j00': '38.202_PHY_Services',
        '38215-j20': '38.215_PHY_Measurements',
        '38300-j20': '38.300_NG-RAN_Overall',
        '38304-j20': '38.304_UE_Idle',
        '38305-j10': '38.305_UE_Positioning',
        '38306-j20': '38.306_UE_Capabilities',
        '38314-j00': '38.314_L2_Measurements',
        '38340-j00': '38.340_BAP',
    }
    
    for spec_dir in os.listdir(downloads_dir):
        spec_path = os.path.join(downloads_dir, spec_dir)
        if not os.path.isdir(spec_path):
            continue
        
        docx_files = find_docx_files(spec_path)
        if not docx_files:
            # Check for .doc file
            doc_files = [f for f in os.listdir(spec_path) if f.endswith('.doc')]
            if doc_files:
                print(f"SKIP (old .doc format): {spec_dir}")
            else:
                print(f"SKIP (no .docx found): {spec_dir}")
            continue
        
        # Get output file name
        base_name = name_map.get(spec_dir, spec_dir)
        version = spec_dir.split('-')[-1]  # e.g., j50
        md_filename = f"{base_name}_{version}.md"
        md_path = os.path.join(md_dir, md_filename)
        
        print(f"Converting: {spec_dir} -> {md_filename}")
        
        # Convert and combine all .docx files
        all_md = []
        for docx_file in docx_files:
            print(f"  Processing: {os.path.basename(docx_file)}")
            md_text = docx_to_markdown(docx_file)
            all_md.append(md_text)
        
        # Write combined markdown
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n\n---\n\n'.join(all_md))
        
        size_kb = os.path.getsize(md_path) / 1024
        print(f"  Done: {size_kb:.1f} KB")
    
    print("\nAll conversions complete!")

if __name__ == '__main__':
    main()
