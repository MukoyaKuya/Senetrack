import sqlite3

def check_counties():
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    cur.execute("SELECT name, logo, governor_image, women_rep_image FROM scorecard_county")
    rows = cur.fetchall()
    print("NAME | LOGO | GOV | WOMEN")
    print("-" * 60)
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_counties()
