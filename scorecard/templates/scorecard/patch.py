from pathlib import Path

file_path = Path("c:/Users/Little Human/Desktop/Senetrack/scorecard/templates/scorecard/bills_analytics.html")
lines = file_path.read_text(encoding="utf-8").splitlines(True)

# 1. MOUNT MODAL OUT OF s-ttl AND s-stalled sections
# Lines 1313 to 1453 (0-indexed 1312 to 1453)
modal_chunk = lines[1312:1453]

# Verify we got the modal correctly to avoid deleting wrong lines
if "<!-- ── Bill explainer modal" in modal_chunk[0] and "</div>" in modal_chunk[-1]:
    del lines[1312:1453]
    
    # Find {{ chart_data|json_script:"chart-data" }} line which is at the end of the content block
    insert_idx = -1
    for i, line in enumerate(lines):
        if '{{ chart_data|json_script:"chart-data" }}' in line:
            insert_idx = i
            break
            
    if insert_idx != -1:
        lines = lines[:insert_idx] + modal_chunk + ["\n"] + lines[insert_idx:]

text = "".join(lines)

# 2. BULLETPROOF CSS CHANGES
old_css = """    /* Bill modal — fade + slide-up transition (no display toggling) */
    #bill-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 10000;
        display: flex !important;
        align-items: center;
        justify-content: center;
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(4px);
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        transition: opacity 0.24s ease, visibility 0s linear 0.24s;
        will-change: opacity;
    }
    #bill-modal-overlay.is-open {
        opacity: 1;
        visibility: visible;
        pointer-events: auto;
        transition: opacity 0.24s ease, visibility 0s linear 0s;
    }
    #bill-modal {
        transform: translateY(12px);
        opacity: 0;
        transition: transform 0.28s cubic-bezier(0.2, 1, 0.3, 1), opacity 0.2s ease;
        will-change: transform, opacity;
    }
    #bill-modal-overlay.is-open #bill-modal {
        transform: translateY(0);
        opacity: 1;
    }
    /* Section card hover lift */"""

new_css = """    /* Bill modal — fade + slide-up transition (no display toggling) */
    #bill-modal-v3-overlay {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        z-index: 99999 !important;
        display: none;
        align-items: center;
        justify-content: center;
        background: rgba(15, 23, 42, 0.75);
        backdrop-filter: blur(4px);
    }
    #bill-modal-v3-overlay.is-open {
        display: flex !important;
    }
    #bill-modal {
        transform: translateY(12px);
        opacity: 0;
        transition: transform 0.2s cubic-bezier(0.2, 1, 0.3, 1), opacity 0.15s ease;
    }
    #bill-modal-v3-overlay.is-open #bill-modal {
        transform: translateY(0);
        opacity: 1;
    }
    body.modal-open { overflow: hidden !important; }
    .ttl-row, .stalled-row { cursor: pointer !important; pointer-events: auto !important; }
    [id^="s-"] { contain: content; position: relative; z-index: 1; transition: box-shadow 0.2s ease, transform 0.2s ease; }
    [id^="s-"]:hover { box-shadow: 0 6px 24px rgba(15,23,42,0.09); transform: translateY(-2px); z-index: 2; }
    /* Section card hover lift */"""

text = text.replace(old_css, new_css)
text = text.replace('id="bill-modal-overlay"', 'id="bill-modal-v3-overlay"')

# 3. BULLETPROOF JS CHANGES
text = text.replace("const overlay = document.getElementById('bill-modal-overlay');", "const overlay = document.getElementById('bill-modal-v3-overlay');")
text = text.replace("document.body.style.overflow = 'hidden';", "document.body.classList.add('modal-open');")
text = text.replace("setTimeout(() => { document.body.style.overflow = ''; }, 240);", "document.body.classList.remove('modal-open');")

old_js_click = """        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && overlay.classList.contains('is-open')) { closeModal(); }
        });
    })();"""

new_js_click = """        document.addEventListener('click', (e) => {
            const row = e.target.closest('.ttl-row, .stalled-row');
            if (row) {
                if (row.classList.contains('ttl-row')) { resetStatTiles(); openModal(row); }
                else { openStalledModal(row); }
            } else if (e.target.closest('#modal-close') || e.target === overlay) {
                closeModal();
            }
        });

        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && overlay.classList.contains('is-open')) { closeModal(); }
        });
    })();"""

text = text.replace(old_js_click, new_js_click)

file_path.write_text(text, encoding="utf-8")
