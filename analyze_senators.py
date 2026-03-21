"""
Analyze all senators: compare DB vs Hansard 2025 report to find mismatches.
Run: python analyze_senators.py
"""
import os
import sys
import re

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
import django
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

# Hansard 2025: name, words, votes_att, votes_tot, bills, sessions, speeches, motions
HANSARD_2025 = [
    ("Oketch Eddy Gicheru", 79017, 20, 20, 3, 77, 755, 18),
    ("Sifuna Edwin Watenya", 86034, 17, 19, 3, 97, 868, 21),
    ("Osotsi Godfrey Otieno", 54186, 19, 19, 2, 81, 592, 24),
    ("Samson Kiprotich Cherargei", 133532, 20, 20, 0, 102, 1428, 27),
    ("Aaron Kipkirui Cheruiyot", 116604, 20, 20, 18, 94, 945, 0),
    ("Khalwale Boni", 105765, 20, 20, 1, 88, 1060, 4),
    ("Ledama Olekina", 72051, 14, 14, 2, 68, 408, 8),
    ("Chute Mohamed Said", 37602, 20, 20, 1, 66, 391, 12),
    ("Murungi Kathuri", 67462, 19, 20, 3, 78, 2165, 0),
    ("David Wakoli Wafula", 32035, 19, 20, 2, 55, 324, 7),
    ("Mogeni Erick Okongo", 46349, 18, 20, 1, 58, 476, 7),
    ("Hillary Kiprotich Sigei", 56638, 17, 20, 1, 68, 1470, 3),
    ("Ali Ibrahim Roba", 46639, 17, 20, 12, 35, 256, 4),
    ("Mohamed Faki Mwinyihaji", 40888, 19, 20, 0, 78, 422, 9),
    ("Andrew Okiya Omtatah Okoiti", 64880, 17, 20, 0, 58, 466, 21),
    ("Enoch Kiio Wambua", 35801, 17, 20, 0, 90, 517, 13),
    ("Catherine Muyeka Mumma", 76420, 10, 19, 2, 71, 1388, 17),
    ("Abass Sheikh Mohamed", 25606, 18, 19, 1, 68, 291, 3),
    ("Stewart Mwachiru Shadrack Madzayo", 17690, 18, 20, 8, 53, 270, 1),
    ("Kiplagat Jackson Mandago", 29082, 19, 20, 0, 62, 334, 6),
    ("William Kipkemoi Kisang", 22496, 19, 20, 1, 55, 263, 2),
    ("Murango James Kamau", 22823, 17, 20, 3, 43, 242, 4),
    ("Alexander Mundigi Munyi", 26679, 19, 20, 0, 67, 355, 4),
    ("Mungatana Danson Buya", 59928, 12, 18, 3, 72, 410, 3),
    ("Methu John Muhia", 22358, 19, 20, 0, 51, 309, 6),
    ("Mwaruma Johnes Mwashushe", 25064, 18, 20, 1, 48, 257, 2),
    ("Haji Abdul Mohammed", 28338, 12, 19, 2, 46, 1046, 7),
    ("John Kinyua Nderitu", 26238, 13, 14, 0, 62, 352, 3),
    ("Recha Julius Murgor", 30862, 19, 20, 1, 49, 336, 0),
    ("Samuel Seki Kanar", 8728, 19, 20, 1, 47, 169, 2),
    ("Ngugi Joe Joseph Nyutu", 19958, 19, 20, 0, 60, 318, 2),
    ("Veronica Waheti Nduati", 60436, 11, 20, 2, 69, 1243, 2),
    ("Ojienda Tom Odhiambo", 30202, 16, 20, 1, 52, 270, 2),
    ("Hamida Ali Kibwana", 28283, 11, 20, 3, 38, 195, 22),
    ("Esther Anyieni Okenyuri", 21774, 11, 20, 2, 66, 239, 12),
    ("Mwenda Gataya Mo Fire", 22255, 19, 20, 0, 52, 261, 2),
    ("Maanzo Daniel Kitonga", 22361, 17, 20, 0, 53, 255, 4),
    ("Dullo Fatuma Adan", 20219, 14, 20, 1, 39, 249, 6),
    ("Onyonka Richard Momoima", 26670, 11, 16, 0, 59, 335, 9),
    ("Steve Ltumbesi Lelegwe", 15386, 19, 20, 1, 39, 191, 0),
    ("Miraj Abdillahi Abdulrahman", 13286, 11, 13, 2, 30, 137, 2),
    ("Wahome Wamatinga", 20756, 15, 17, 1, 34, 138, 1),
    ("Muthama Agnes Kavindu Mbuku", 15936, 15, 20, 0, 50, 236, 8),
    ("Chesang Allan Kiprotich", 12636, 18, 20, 1, 19, 330, 1),
    ("Crystal Asige", 19487, 13, 20, 7, 31, 146, 2),
    ("Joyce Chepkoech Korir", 16906, 13, 20, 1, 31, 241, 6),
    ("Mutinda Maureen Tabitha", 35676, 11, 20, 2, 48, 227, 3),
    ("Karungo Paul Thangwa", 5374, 18, 20, 3, 12, 87, 3),
    ("Omar Mariam Sheikh", 21992, 14, 20, 3, 41, 190, 0),
    ("Oginga Oburu", 34352, 13, 20, 1, 37, 249, 1),
    ("Nyamu Karen Njeri", 22523, 11, 20, 1, 46, 184, 4),
    ("Gloria Magoma Orwoba", 27599, 11, 19, 2, 22, 252, 4),
    ("Keroche Tabitha Karanja", 10034, 18, 20, 0, 27, 100, 3),
    ("Margaret Kamar", 17765, 10, 13, 2, 32, 98, 0),
    ("James Lomenen Ekomwa", 7826, 18, 20, 0, 27, 175, 1),
    ("Kamau Joseph Githuku", 5856, 20, 20, 0, 26, 141, 0),
    ("George Mungai Mbugua", 21267, 11, 20, 1, 29, 244, 1),
    ("Beatrice Akinyi Ogolla Oyomo", 4170, 12, 20, 1, 24, 115, 5),
    ("Peris Pesi Tobiko", 10657, 11, 20, 1, 25, 81, 4),
    ("Chimera Raphael Mwinzago", 9349, 11, 20, 2, 24, 103, 2),
    ("Boy Issa Juma", 5175, 16, 20, 0, 24, 118, 1),
    ("Cheptumo William Kipkiror", 18688, 17, 19, 0, 10, 116, 0),
    ("Hezena M. Lemaletian", 12893, 11, 20, 0, 30, 113, 3),
    ("Amason Jeffah Kingi", 79723, 0, 1, 0, 100, 3269, 0),
    ("Beth Kalunda Syengo", 2456, 11, 20, 2, 10, 44, 1),
    ("Moses Otieno Kajwang'", 2119, 17, 20, 3, 2, 15, 0),
    ("Abdalla Shakilla Mohamed", 4825, 11, 20, 0, 17, 37, 1),
    ("Betty Batuli Montet", 6864, 11, 20, 0, 13, 50, 0),
    ("Kipchumba Murkomen", 13548, 0, 0, 0, 11, 76, 0),
    ("Vincent Cheburet Kiprono Chemitei", 1520, 0, 0, 0, 2, 36, 0),
    ("Consolata Nabwire Wakwabubi", 6823, 0, 1, 0, 13, 70, 0),
]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().replace("'", "").strip())


def match_name(report_name, db_name):
    rn = norm(report_name)
    dn = norm(db_name)
    if rn == dn:
        return True
    rw = set(rn.split())
    dw = set(dn.split())
    return len(rw & dw) >= 2 and (rw <= dw or dw <= rw)


def main():
    senators = {norm(s.name): s for s in Senator.objects.filter(perf__isnull=False).select_related("perf")}
    hansard_by_norm = {norm(r[0]): r for r in HANSARD_2025}

    print("=" * 80)
    print("SENATOR ANALYSIS: DB vs Hansard 2025 Report")
    print("=" * 80)
    print()

    # 1. DB senators not in Hansard
    db_only = set(senators.keys()) - set(hansard_by_norm.keys())
    if db_only:
        print("DB senators NOT in Hansard report (possible missing or different names):")
        for n in sorted(db_only):
            s = senators.get(n)
            if s:
                for hn, row in hansard_by_norm.items():
                    if match_name(row[0], s.name):
                        print(f"  -> {s.name} may match Hansard: {row[0]}")
                        break
                else:
                    print(f"  {s.name} ({s.senator_id})")
        print()

    # 2. Hansard senators not in DB
    hansard_only = set(hansard_by_norm.keys()) - set(senators.keys())
    if hansard_only:
        print("Hansard senators NOT in DB (by normalized name):")
        for n in sorted(hansard_only):
            row = hansard_by_norm[n]
            for db_n, s in senators.items():
                if match_name(row[0], s.name):
                    break
            else:
                print(f"  {row[0]}")
        print()

    # 3. Metric mismatches (DB vs Hansard)
    print("METRIC MISMATCHES (DB vs Hansard):")
    print("-" * 80)
    mismatches = []

    for row in HANSARD_2025:
        report_name, words, v_att, v_tot, bills, sessions, speeches, motions = row
        matched = None
        for db_n, s in senators.items():
            if match_name(report_name, s.name):
                matched = s
                break
        if not matched or not matched.perf:
            continue

        p = matched.perf
        diffs = []

        if p.words_spoken != words:
            diffs.append(("words", p.words_spoken, words))
        if p.attended_votes != v_att:
            diffs.append(("votes_att", p.attended_votes, v_att))
        if p.total_votes != v_tot:
            diffs.append(("votes_tot", p.total_votes, v_tot))
        if p.sponsored_bills != bills:
            diffs.append(("bills", p.sponsored_bills, bills))
        if p.sessions_attended != sessions:
            diffs.append(("sessions", p.sessions_attended, sessions))
        if p.speeches != speeches:
            diffs.append(("speeches", p.speeches, speeches))
        if p.motions_sponsored != motions:
            diffs.append(("motions", p.motions_sponsored, motions))

        if diffs:
            mismatches.append((matched.name, matched.senator_id, diffs))

    for name, sid, diffs in sorted(mismatches, key=lambda x: -len(x[2])):
        print(f"\n{name} ({sid}):")
        for field, db_val, h_val in diffs:
            print(f"  {field}: DB={db_val}  Hansard={h_val}")

    print()
    print("=" * 80)
    print("INTENTIONAL UPDATES (from external sources - DB is correct)")
    print("=" * 80)
    intentional = [
        ("Moses Kajwang'", "Parliament/Mzalendo: 613 speeches, 80 sessions, 3 bills, 2 passed"),
        ("Kiplagat Jackson Mandago", "Mzalendo: 582 speeches, Local Content Bill"),
        ("Samson Cherargei", "Tuko/Capital FM: 3 bills, 1 passed (Employment)"),
        ("Crystal Asige", "Parliament: 5 bills, 1 passed (PWD Bill)"),
    ]
    for name, note in intentional:
        print(f"  {name}: {note}")

    print()
    print("=" * 80)
    print("HANSARD NOT IN DB (excluded by design)")
    print("=" * 80)
    print("  Amason Jeffah Kingi - Speaker of Senate (may be excluded)")
    print("  Kipchumba Murkomen - Former CS (may be excluded)")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"DB senators with perf: {len(senators)}")
    print(f"Hansard report entries: {len(HANSARD_2025)}")
    print(f"Senators with metric mismatches: {len(mismatches)}")
    print(f"DB-only (not in Hansard): {len(db_only)}")
    print(f"Hansard-only (not in DB): {len(hansard_only)}")


if __name__ == "__main__":
    main()
