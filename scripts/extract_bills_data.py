import json
import re
import os
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    return full_text

def parse_bills_text(text):
    """
    Parses the extracted text into structured bill records.
    The PDF has headers like: NO. BILL SPONSOR GAZETTE NO. DATE OF PUBLICATION ...
    Rows start with a number followed by a dot (e.g. "1. ")
    """
    # Remove page headers/footers (simplified)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if "THE SENATE" in line or "BILLS TRACKER" in line or "PAGE" in line:
            continue
        cleaned_lines.append(line.strip())
    
    records = []
    current_record = None
    
    # regex for line starting with "1. ", "56.", etc.
    bill_start_re = re.compile(r'^(\d+)\.\b')
    
    for line in cleaned_lines:
        match = bill_start_re.match(line)
        if match:
            if current_record:
                records.append(current_record)
            
            bill_no = int(match.group(1))
            # Start new record
            current_record = {
                "no": bill_no,
                "raw_content": line[match.end():].strip()
            }
        else:
            if current_record:
                current_record["raw_content"] += " " + line

    if current_record:
        records.append(current_record)
        
    return records

def refine_records(records):
    """
    Refines raw records into structured fields.
    """
    refined = []
    for r in records:
        text = r["raw_content"]
        
        # 1. Extract Ref: (Senate Bills No. X of YYYY)
        ref_match = re.search(r'\((Senate|National Assembly) Bills No\.\s*(\d+)\s*of\s*(\d{4})\)', text, re.I)
        ref = ""
        year = 2022 # Default
        title = ""
        if ref_match:
            ref = ref_match.group(0)
            year = int(ref_match.group(3))
            title_end = ref_match.start()
            title = text[:title_end].strip()
            # Clean up title: remove "The " if redundant, but usually it's correct
            remaining = text[ref_match.end():].strip()
        else:
            title = text # Fallback
            remaining = ""

        # 2. Extract Sponsor
        # Usually follows the ref, often starts with "Sen." or "Chairperson" or "The Senate Majority Leader"
        sponsor = "Unknown"
        s_match = re.search(r'(Sen\.\s+[A-Z][a-z\s]+|Chairperson[A-Z\s,]+|The Senate Majority Leader)', remaining)
        if s_match:
            sponsor = s_match.group(0).strip()
            remaining = remaining[s_match.end():].strip()

        # 3. Status Mapping (Logic from Implementation Plan)
        status = "at_cowt"
        if "assented" in text.lower() or "date of assent" in text.lower():
            status = "assented"
        elif "referred to the national assembly" in text.lower() or "at na" in text.lower():
            status = "at_na"
        elif "mediation" in text.lower():
            status = "in_mediation"
        elif "negatived" in text.lower():
            status = "negatived"
        elif "withdrawn" in text.lower():
            status = "withdrawn"
        elif "second reading" in text.lower() and "passed" not in text.lower():
            status = "at_2nd_reading"

        # 4. Committee (Basic heuristic)
        committee = "Unknown"
        c_match = re.search(r'(Education|Health|Agriculture|Finance|Justice|Labour|ICT|Devolution|Security|Land|Transport|Energy|Trade)', text, re.I)
        if c_match:
            committee = c_match.group(0).strip()

        refined.append({
            "no": r["no"],
            "title": title,
            "bill_ref": ref,
            "sponsor": sponsor,
            "committee": committee,
            "status": status,
            "year": year,
            "remarks": text[-100:] # Capture last part as hint for remarks
        })
    return refined

if __name__ == "__main__":
    PDF_PATH = r"c:\Users\Little Human\Desktop\Senetrack\docs\Bills Tracker updated as at 27.03.2026.pdf"
    OUTPUT_PATH = r"c:\Users\Little Human\Desktop\Senetrack\docs\bills_tracker_2026.json"
    
    if not os.path.exists(PDF_PATH):
        print(f"Error: {PDF_PATH} not found.")
    else:
        print(f"Extracting text from {PDF_PATH}...")
        raw_text = extract_text_from_pdf(PDF_PATH)
        print(f"Parsing bills...")
        raw_records = parse_bills_text(raw_text)
        print(f"Refining {len(raw_records)} records...")
        final_data = refine_records(raw_records)
        
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=4)
        
        print(f"Success! JSON data saved to {OUTPUT_PATH}")
