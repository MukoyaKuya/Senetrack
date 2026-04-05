import json
import re

def parse_bills_ocr(ocr_text):
    """
    Parses OCR text from the Senate Bills Tracker PDF into a list of dictionaries.
    """
    bills = []
    
    # We look for "N. <Title> <Reference> <Sponsor> ..."
    # This is tricky because OCR text can be fragmented.
    # We'll use regex to find bill starts: Digit followed by dot.
    
    # Pre-process: Join lines that don't start with a number or are likely part of the previous field
    lines = ocr_text.split('\n')
    
    current_bill = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # New bill marker: "1. ", "10.", etc. at the start of a line
        match = re.match(r'^(\d+)[\.\s]', line)
        if match:
            if current_bill:
                bills.append(current_bill)
            
            bill_no = int(match.group(1))
            remaining = line[len(match.group(0)):].strip()
            
            current_bill = {
                "no": bill_no,
                "raw_text": remaining,
                "title": "",
                "bill_ref": "",
                "sponsor": "",
                "committee": "",
                "date_pub": "",
                "status_raw": "",
                "assent_date": ""
            }
        elif current_bill:
            current_bill["raw_text"] += " " + line

    if current_bill:
        bills.append(current_bill)

    # Post-process: Extract fields from raw_text
    processed_bills = []
    for b in bills:
        text = b["raw_text"]
        
        # Regex for Senate Bill Ref: "(Senate Bills No. X of YYYY)"
        ref_match = re.search(r'\(Senate Bills No\.\s*\d+\s*of\s*\d{4}\)', text, re.I)
        if ref_match:
            b["bill_ref"] = ref_match.group(0).strip()
            # Title is everything before the ref
            b["title"] = text[:ref_match.start()].strip()
            remaining = text[ref_match.end():].strip()
        else:
            # Try National Assembly ref
            ref_match = re.search(r'\(National Assembly Bills No\.\s*\d+\s*of\s*\d{4}\)', text, re.I)
            if ref_match:
                b["bill_ref"] = ref_match.group(0).strip()
                b["title"] = text[:ref_match.start()].strip()
                remaining = text[ref_match.end():].strip()
            else:
                remaining = text

        # Status heuristic based on keywords
        status = "at_cowt" # Default
        if "assented" in text.lower() or "date of assent" in text.lower():
            status = "assented"
        elif "referred to the national assembly" in text.lower():
            status = "at_na"
        elif "mediation" in text.lower():
            status = "in_mediation"
        elif "negatived" in text.lower():
            status = "negatived"
        elif "withdrawn" in text.lower():
            status = "withdrawn"
        elif "second reading" in text.lower() and "passed" not in text.lower():
            status = "at_2nd_reading"
        
        b["status_slug"] = status
        
        # Simple sponsor extraction (Sen. X)
        sponsor_match = re.search(r'Sen\.\s+([A-Z][a-z\s]+)', text)
        if sponsor_match:
            b["sponsor"] = sponsor_match.group(0).strip()

        processed_bills.append(b)
        
    return processed_bills

if __name__ == "__main__":
    # In a real scenario, we'd read the full text from a file.
    # Since I have the OCR chunks, I'll combine them here or read from a temp file.
    # For now, I'll write the structure and ask for the full text dump to be parsed.
    print("Script ready. Provide OCR text to process.")
