import json
import re
from pypdf import PdfReader

def extract_clean_text(pdf_path):
    reader = PdfReader(pdf_path)
    lines = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            lines.extend(text.split('\n'))
    return lines

def improved_parser(lines):
    bills = []
    # Pattern to find the start of a bill row: "1. [Title]"
    # Sometimes it might be " 1. " or similar.
    bill_start_pattern = re.compile(r'^\s*(\d+)\.\s+(.*)')
    
    current_bill = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Check if line starts a new bill
        match = bill_start_pattern.match(line)
        if match:
            if current_bill:
                bills.append(current_bill)
            
            no = int(match.group(1))
            title_start = match.group(2)
            
            current_bill = {
                "no": no,
                "title_raw": title_start,
                "sponsor_raw": "",
                "ref_raw": "",
                "status_raw": "",
                "full_text": line
            }
        else:
            if current_bill:
                current_bill["full_text"] += " " + line
                # Keep appending to title until we see a sponsor or ref
                if not current_bill["ref_raw"] and "(" not in line:
                    current_bill["title_raw"] += " " + line

    if current_bill:
        bills.append(current_bill)
        
    final_bills = []
    for b in bills:
        text = b["full_text"]
        
        # Ref search
        ref_match = re.search(r'\((Senate|National Assembly) Bills No\.\s*(\d+)\s*of\s*(\d{4})\)', text, re.I)
        if ref_match:
            b["bill_ref"] = ref_match.group(0)
            b["year"] = int(ref_match.group(3))
            # Clean title: everything before the ref
            b["title"] = text[text.find(str(b["no"])+".")+len(str(b["no"]))+1 : ref_match.start()].strip()
            # If current_bill["title_raw"] was messed up, the slice above should be better
        else:
            b["bill_ref"] = "Unknown"
            b["year"] = 2022
            b["title"] = b["title_raw"]

        # Sponsor search: "Sen. [Name]" or "Chairperson" or "Leader"
        sp_match = re.search(r'(Sen\.\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)*|The Senate Majority Leader|Chairperson[A-Za-z\s,]+Committee)', text)
        if sp_match:
            b["sponsor"] = sp_match.group(0).strip()
        else:
            b["sponsor"] = "Unknown"

        # Status search
        status = "at_cowt"
        remarks = text.lower()
        if "assented" in remarks or "date of assent" in remarks:
            status = "assented"
        elif "referred to the national assembly" in remarks or "at na" in remarks:
            status = "at_na"
        elif "mediation" in remarks:
            status = "in_mediation"
        elif "negatived" in remarks:
            status = "negatived"
        elif "withdrawn" in remarks:
            status = "withdrawn"
        elif "second reading" in remarks and "passed" not in remarks:
            status = "at_2nd_reading"
        
        b["status"] = status
        # Clean record for JSON
        final_bills.append({
            "no": b["no"],
            "title": b["title"],
            "bill_ref": b["bill_ref"],
            "sponsor": b["sponsor"],
            "status": b["status"],
            "year": b["year"]
        })
        
    return final_bills

if __name__ == "__main__":
    PDF_PATH = r"c:\Users\Little Human\Desktop\Senetrack\docs\Bills Tracker updated as at 27.03.2026.pdf"
    OUTPUT_PATH = r"c:\Users\Little Human\Desktop\Senetrack\docs\bills_tracker_2026_fixed.json"
    
    print(f"Reading {PDF_PATH}...")
    lines = extract_clean_text(PDF_PATH)
    print(f"Parsing {len(lines)} lines...")
    data = improved_parser(lines)
    print(f"Extraction complete. Found {len(data)} bills.")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"Saved to {OUTPUT_PATH}")
