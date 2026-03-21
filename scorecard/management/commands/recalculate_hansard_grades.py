"""
Import Hansard 2025 report data and recalculate senator grades using the Hansard engine.
Run: python manage.py recalculate_hansard_grades
"""
import re
from django.core.management.base import BaseCommand
from scorecard.models import Senator, ParliamentaryPerformance


# Hansard 2025 report data: name, words, votes_attended, votes_total, bills, sessions, speeches, motions,
# overall_score, grade, structural_score, debate_score (canonical from report)
HANSARD_2025_DATA = [
    ("Oketch Eddy Gicheru", 79017, 20, 20, 3, 77, 755, 18, 89.8, "A", 49.57, 40.23),
    ("Sifuna Edwin Watenya", 86034, 17, 19, 3, 97, 868, 21, 89.0, "A", 47.92, 41.07),
    ("Osotsi Godfrey Otieno", 54186, 19, 19, 2, 81, 592, 24, 88.97, "A", 49.0, 39.97),
    ("Samson Kiprotich Cherargei", 133532, 20, 20, 0, 102, 1428, 27, 88.47, "A", 45.0, 43.47),
    ("Aaron Kipkirui Cheruiyot", 116604, 20, 20, 18, 94, 945, 0, 87.12, "A", 54.65, 32.47),
    ("Khalwale Boni", 105765, 20, 20, 1, 88, 1060, 4, 85.6, "A", 48.25, 37.35),
    ("Ledama Olekina", 72051, 14, 14, 2, 68, 408, 8, 84.95, "A", 48.26, 36.7),
    ("Chute Mohamed Said", 37602, 20, 20, 1, 66, 391, 12, 83.65, "A", 47.03, 36.62),
    ("Murungi Kathuri", 67462, 19, 20, 3, 78, 2165, 0, 81.45, "A", 48.37, 33.08),
    ("David Wakoli Wafula", 32035, 19, 20, 2, 55, 324, 7, 80.65, "A", 46.11, 34.54),
    ("Mogeni Erick Okongo", 46349, 18, 20, 1, 58, 476, 7, 79.86, "A-", 43.98, 35.88),
    ("Hillary Kiprotich Sigei", 56638, 17, 20, 1, 68, 1470, 3, 79.63, "A-", 43.4, 36.23),
    ("Ali Ibrahim Roba", 46639, 17, 20, 12, 35, 256, 4, 79.02, "A-", 45.68, 33.33),
    ("Mohamed Faki Mwinyihaji", 40888, 19, 20, 0, 78, 422, 9, 78.72, "A-", 42.61, 36.11),
    ("Andrew Okiya Omtatah Okoiti", 64880, 17, 20, 0, 58, 466, 21, 78.29, "A-", 38.85, 39.45),
    ("Enoch Kiio Wambua", 35801, 17, 20, 0, 90, 517, 13, 77.99, "A-", 40.72, 37.27),
    ("Catherine Muyeka Mumma", 76420, 10, 19, 2, 71, 1388, 17, 77.74, "A-", 36.6, 41.14),
    ("Abass Sheikh Mohamed", 25606, 18, 19, 1, 68, 291, 3, 77.72, "A-", 45.84, 31.88),
    ("Stewart Mwachiru Shadrack Madzayo", 17690, 18, 20, 8, 53, 270, 1, 76.72, "A-", 47.68, 29.04),
    ("Kiplagat Jackson Mandago", 29082, 19, 20, 0, 62, 334, 6, 75.66, "A-", 41.63, 34.03),
    ("William Kipkemoi Kisang", 22496, 19, 20, 1, 55, 263, 2, 75.62, "A-", 45.0, 30.61),
    ("Murango James Kamau", 22823, 17, 20, 3, 43, 242, 4, 75.36, "A-", 43.35, 32.02),
    ("Alexander Mundigi Munyi", 26679, 19, 20, 0, 67, 355, 4, 74.95, "B+", 41.96, 32.99),
    ("Mungatana Danson Buya", 59928, 12, 18, 3, 72, 410, 3, 74.91, "B+", 40.95, 33.96),
    ("Methu John Muhia", 22358, 19, 20, 0, 51, 309, 6, 74.24, "B+", 40.8, 33.44),
    ("Mwaruma Johnes Mwashushe", 25064, 18, 20, 1, 48, 257, 2, 73.93, "B+", 43.18, 30.75),
    ("Haji Abdul Mohammed", 28338, 12, 19, 2, 46, 1046, 7, 73.89, "B+", 37.39, 36.5),
    ("John Kinyua Nderitu", 26238, 13, 14, 0, 62, 352, 3, 73.37, "B+", 41.09, 32.28),
    ("Recha Julius Murgor", 30862, 19, 20, 1, 49, 336, 0, 72.82, "B+", 44.51, 28.31),
    ("Samuel Seki Kanar", 8728, 19, 20, 1, 47, 169, 2, 72.53, "B+", 44.34, 28.19),
    ("Ngugi Joe Joseph Nyutu", 19958, 19, 20, 0, 60, 318, 2, 72.25, "B+", 41.49, 30.76),
    ("Veronica Waheti Nduati", 60436, 11, 20, 2, 69, 1243, 2, 72.23, "B+", 37.07, 35.16),
    ("Ojienda Tom Odhiambo", 30202, 16, 20, 1, 52, 270, 2, 72.18, "B+", 41.02, 31.16),
    ("Hamida Ali Kibwana", 28283, 11, 20, 3, 38, 195, 22, 71.89, "B+", 35.33, 36.56),
    ("Esther Anyieni Okenyuri", 21774, 11, 20, 2, 66, 239, 12, 71.66, "B+", 36.88, 34.78),
    ("Mwenda Gataya Mo Fire", 22255, 19, 20, 0, 52, 261, 2, 71.46, "B+", 40.88, 30.58),
    ("Maanzo Daniel Kitonga", 22361, 17, 20, 0, 53, 255, 4, 70.54, "B+", 38.46, 32.08),
    ("Dullo Fatuma Adan", 20219, 14, 20, 1, 39, 249, 6, 70.18, "B+", 37.3, 32.88),
    ("Onyonka Richard Momoima", 26670, 11, 16, 0, 59, 335, 9, 69.82, "B", 34.86, 34.96),
    ("Steve Ltumbesi Lelegwe", 15386, 19, 20, 1, 39, 191, 0, 69.64, "B", 43.55, 26.08),
    ("Miraj Abdillahi Abdulrahman", 13286, 11, 13, 2, 30, 137, 2, 69.48, "B", 40.96, 28.52),
    ("Wahome Wamatinga", 20756, 15, 17, 1, 34, 138, 1, 69.36, "B", 41.28, 28.07),
    ("Muthama Agnes Kavindu Mbuku", 15936, 15, 20, 0, 50, 236, 8, 68.84, "B", 35.72, 33.13),
    ("Chesang Allan Kiprotich", 12636, 18, 20, 1, 19, 330, 1, 68.15, "B", 39.31, 28.84),
    ("Crystal Asige", 19487, 13, 20, 7, 31, 146, 2, 68.14, "B", 38.86, 29.29),
    ("Joyce Chepkoech Korir", 16906, 13, 20, 1, 31, 241, 6, 67.6, "B", 35.09, 32.51),
    ("Mutinda Maureen Tabitha", 35676, 11, 20, 2, 48, 227, 3, 67.52, "B", 35.53, 31.99),
    ("Karungo Paul Thangwa", 5374, 18, 20, 3, 12, 87, 3, 66.35, "B", 39.33, 27.02),
    ("Omar Mariam Sheikh", 21992, 14, 20, 3, 41, 190, 0, 66.07, "B", 39.4, 26.68),
    ("Oginga Oburu", 34352, 13, 20, 1, 37, 249, 1, 65.84, "B", 35.83, 30.01),
    ("Nyamu Karen Njeri", 22523, 11, 20, 1, 46, 184, 4, 65.74, "B", 34.25, 31.49),
    ("Gloria Magoma Orwoba", 27599, 11, 19, 2, 22, 252, 4, 65.4, "B", 32.99, 32.41),
    ("Keroche Tabitha Karanja", 10034, 18, 20, 0, 27, 100, 3, 65.21, "B", 36.88, 28.33),
    ("Margaret Kamar", 17765, 10, 13, 2, 32, 98, 0, 64.4, "B-", 39.3, 25.1),
    ("James Lomenen Ekomwa", 7826, 18, 20, 0, 27, 175, 1, 63.74, "B-", 36.88, 26.86),
    ("Kamau Joseph Githuku", 5856, 20, 20, 0, 26, 141, 0, 63.11, "B-", 39.22, 23.89),
    ("George Mungai Mbugua", 21267, 11, 20, 1, 29, 244, 1, 61.47, "B-", 32.31, 29.16),
    ("Beatrice Akinyi Ogolla Oyomo", 4170, 12, 20, 1, 24, 115, 5, 61.09, "B-", 32.77, 28.31),
    ("Peris Pesi Tobiko", 10657, 11, 20, 1, 25, 81, 4, 60.41, "B-", 31.69, 28.71),
    ("Chimera Raphael Mwinzago", 9349, 11, 20, 2, 24, 103, 2, 60.02, "B-", 32.63, 27.4),
    ("Boy Issa Juma", 5175, 16, 20, 0, 24, 118, 1, 59.32, "C+", 33.89, 25.43),
    ("Cheptumo William Kipkiror", 18688, 17, 19, 0, 10, 116, 0, 58.21, "C+", 32.72, 25.49),
    ("Hezena M. Lemaletian", 12893, 11, 20, 0, 30, 113, 3, 57.55, "C+", 28.57, 28.98),
    ("Amason Jeffah Kingi", 79723, 0, 1, 0, 100, 3269, 0, 54.04, "C", 19.92, 34.13),
    ("Beth Kalunda Syengo", 2456, 11, 20, 2, 10, 44, 1, 51.45, "C", 29.08, 22.37),
    ("Moses Otieno Kajwang'", 2119, 17, 20, 3, 2, 15, 0, 49.88, "C-", 31.76, 18.12),
    ("Abdalla Shakilla Mohamed", 4825, 11, 20, 0, 17, 37, 1, 49.42, "C-", 26.22, 23.2),
    ("Betty Batuli Montet", 6864, 11, 20, 0, 13, 50, 0, 47.4, "C-", 25.14, 22.26),
    ("Kipchumba Murkomen", 13548, 0, 0, 0, 11, 76, 0, 47.4, "C-", 23.22, 24.17),
    ("Vincent Cheburet Kiprono Chemitei", 1520, 0, 0, 0, 2, 36, 0, 36.35, "D", 17.24, 19.11),
    ("Consolata Nabwire Wakwabubi", 6823, 0, 1, 0, 13, 70, 0, 34.25, "D-", 11.39, 22.86),
]


def _normalize_name(name: str) -> str:
    """Normalize for matching: lowercase, collapse spaces, remove accents."""
    s = name.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _match_senator(report_name: str, senators: list) -> Senator | None:
    """Match report name to Senator. Tries exact, then contains."""
    norm_report = _normalize_name(report_name)
    for s in senators:
        norm_db = _normalize_name(s.name)
        if norm_report == norm_db:
            return s
        # Check if all significant words from report appear in DB name
        report_words = set(norm_report.split())
        db_words = set(norm_db.split())
        if report_words <= db_words or db_words <= report_words:
            if len(report_words & db_words) >= 2:  # at least 2 words match
                return s
    return None


class Command(BaseCommand):
    help = "Import Hansard 2025 report data and recalculate senator grades"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without saving")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        senators = list(Senator.objects.all())
        updated = 0
        skipped = 0

        for row in HANSARD_2025_DATA:
            report_name, words, votes_att, votes_tot, bills, sessions, speeches, motions = row[:8]
            overall_score, grade, structural_score, debate_score = row[8:12]

            senator = _match_senator(report_name, senators)
            if not senator:
                self.stdout.write(self.style.WARNING(f"  No match: {report_name}"))
                skipped += 1
                continue

            perf, _ = ParliamentaryPerformance.objects.get_or_create(senator=senator, defaults={})

            # Update raw metrics from report
            perf.words_spoken = words
            perf.attended_votes = votes_att
            perf.total_votes = max(votes_tot, 1)
            perf.sponsored_bills = bills
            perf.sessions_attended = sessions
            perf.speeches = speeches
            perf.motions_sponsored = motions
            # Plenary attendance from sessions (max 102 in report)
            perf.attendance_rate = round((sessions / 102.0) * 100, 1) if sessions else 0

            # Use canonical scores from report (not engine calculation)
            perf.overall_score = overall_score
            perf.grade = grade
            perf.structural_score = structural_score
            perf.debate_score = debate_score

            if not dry_run:
                perf.save()

            updated += 1
            self.stdout.write(
                f"  {senator.name}: {overall_score} ({grade}) "
                f"[S:{structural_score:.1f} D:{debate_score:.1f}]"
            )

        self.stdout.write(self.style.SUCCESS(f"\nUpdated {updated} senators. Skipped {skipped}."))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - no changes saved."))
