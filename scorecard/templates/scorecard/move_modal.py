import re

with open('c:/Users/Little Human/Desktop/Senetrack/scorecard/templates/scorecard/bills_analytics.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update the CSS for the modal and adding contain: content
css_old = """    /* Bill modal — fade + slide-up transition (no display toggling) */
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

css_new = """    /* Bill modal — fade + slide-up transition */
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
html = html.replace(css_old, css_new)

# 2. Extract Modal HTML
start_marker = "<!-- ── Bill explainer modal ─────────────────────────────────── -->"
end_marker = "</div>\n        <p class=\"text-[10px] text-slate-400 mt-2\">"

start_idx = html.find(start_marker)
end_idx = html.find(end_marker, start_idx) + 6 # +6 to include the closing </div>

modal_html = html[start_idx:end_idx]
html = html[:start_idx] + html[end_idx:] # Remove it from the dom

chart_data_marker = "{{ chart_data|json_script:\"chart-data\" }}"
insert_idx = html.find(chart_data_marker)
html = html[:insert_idx] + modal_html + "\n\n" + html[insert_idx:]

# 3. Update the JavaScript references (just replace 'bill-modal-overlay' with 'bill-modal-v3-overlay', fix the scroll styling to body.classList toggles, and hook the new delegated event listener)
js_script_old = "const overlay = document.getElementById('bill-modal-overlay');"
js_script_new = "const overlay = document.getElementById('bill-modal-v3-overlay');"
html = html.replace(js_script_old, js_script_new)

html = html.replace("document.body.style.overflow = 'hidden';", "document.body.classList.add('modal-open');")
html = html.replace("setTimeout(() => { document.body.style.overflow = ''; }, 240);", "document.body.classList.remove('modal-open');")

# 4. Inject the new click listener
js_click_old = """        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && overlay.classList.contains('is-open')) { closeModal(); }
        });
    })();"""

js_click_new = """        document.addEventListener('click', (e) => {
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
html = html.replace(js_click_old, js_click_new)

# Write it out
with open('c:/Users/Little Human/Desktop/Senetrack/scorecard/templates/scorecard/bills_analytics.html', 'w', encoding='utf-8') as f:
    f.write(html)
