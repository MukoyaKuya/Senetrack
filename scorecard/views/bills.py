import re
from collections import Counter

from django.shortcuts import render


STATUS_LABELS = {
    "assented":        "Assented into Law",
    "at_na":           "At National Assembly",
    "in_mediation":    "In Mediation",
    "at_cowt":         "At Committee (Senate)",
    "at_2nd_reading":  "At Second Reading",
    "negatived":       "Negatived",
    "withdrawn":       "Withdrawn",
    "presidential_memo": "Presidential Memorandum",
}

# (number, title, bill_ref, sponsor, committee, status, year)
_BILLS_RAW = [
    (1,  "The Vocational Training Bill",
         "Senate Bills No. 3 of 2022",
         "Sen. Moses Kajwang'", "Education", "at_na", 2022),
    (2,  "The County Governments Additional Allocation Bill",
         "Senate Bills No. 4 of 2022",
         "Chairperson, Finance & Budget Committee", "Finance & Budget", "assented", 2022),
    (3,  "The Parliamentary Powers and Privileges (Amendment) Bill",
         "Senate Bills No. 5 of 2022",
         "Sen. Danson Mungatana", "Justice & Legal", "at_na", 2022),
    (4,  "The Natural Resources (Benefit Sharing) Bill",
         "Senate Bills No. 6 of 2022",
         "Sen. Danson Mungatana", "Land & Environment", "in_mediation", 2022),
    (5,  "The Economic and Social Rights Bill",
         "Senate Bills No. 7 of 2022",
         "Sen. Danson Mungatana", "Justice & Legal", "at_na", 2022),
    (6,  "The Independent Electoral and Boundaries Commission (Amendment) Bill",
         "National Assembly Bills No. 49 of 2022",
         "The Senate Majority Leader", "Justice & Legal", "assented", 2022),
    (7,  "The Prompt Payment Bill",
         "Senate Bills No. 8 of 2022",
         "Sen. Mariam Sheikh Omar", "Finance & Budget", "negatived", 2022),
    (8,  "The County Licensing (Uniform Procedures) Bill",
         "Senate Bills No. 9 of 2022",
         "Sen. Mariam Sheikh Omar", "Trade & Industry", "assented", 2022),
    (9,  "The Office of the County Printer Bill",
         "Senate Bills No. 10 of 2022",
         "Sen. Edwin Sifuna", "ICT", "withdrawn", 2022),
    (10, "The Employment (Amendment) Bill",
         "Senate Bills No. 11 of 2022",
         "Sen. Samson Cherarkey", "Labour & Social Welfare", "in_mediation", 2022),
    (11, "The Agricultural and Livestock Extension Services Bill",
         "Senate Bills No. 12 of 2022",
         "Sen. Maureen Tabitha Mutinda", "Agriculture", "at_na", 2022),
    (12, "The Mung Beans Bill",
         "Senate Bills No. 13 of 2022",
         "Sen. Enoch Kiio Wambua", "Agriculture", "in_mediation", 2022),
    (13, "The Startup Bill",
         "Senate Bills No. 14 of 2022",
         "Sen. Crystal Kegehi Asige", "Trade & Industry", "in_mediation", 2022),
    (14, "The Tea (Amendment) Bill",
         "Senate Bills No. 1 of 2023",
         "Sen. Wakili Hillary Sigei", "Agriculture", "at_na", 2023),
    (15, "The Konza Technopolis Bill",
         "Senate Bills No. 2 of 2023",
         "Sen. Gloria Orwoba", "ICT", "negatived", 2023),
    (16, "The Equalization Fund Appropriation Bill",
         "Senate Bills No. 3 of 2023",
         "Chairperson, Finance & Budget Committee", "Finance & Budget", "assented", 2023),
    (17, "The Learners with Disabilities Bill",
         "Senate Bills No. 4 of 2023",
         "Sen. Margaret Kamar & Sen. Crystal Asige", "Education", "at_na", 2023),
    (18, "The Cotton Industry Development Bill",
         "Senate Bills No. 5 of 2023",
         "Sen. Beth Syengo", "Agriculture", "presidential_memo", 2023),
    (19, "The County Boundaries Bill",
         "Senate Bills No. 6 of 2023",
         "Sen. Moses Kajwang'", "Devolution", "at_na", 2023),
    (20, "The Persons with Disabilities Bill",
         "Senate Bills No. 7 of 2023",
         "Sen. Crystal Asige", "Labour & Social Welfare", "assented", 2023),
    (21, "The Heritage and Museums Bill",
         "Senate Bills No. 8 of 2023",
         "Chairperson, Labour & Social Welfare Committee", "Labour & Social Welfare", "at_cowt", 2023),
    (22, "The Kenyan Sign Language Bill",
         "Senate Bills No. 9 of 2023",
         "Sen. Margaret Kamar & Sen. Crystal Asige", "Education", "at_na", 2023),
    (23, "The Division of Revenue Bill",
         "National Assembly Bills No. 9 of 2023",
         "The Senate Majority Leader", "Finance & Budget", "assented", 2023),
    (24, "The Coffee Bill",
         "Senate Bills No. 10 of 2023",
         "Chairperson, Agriculture, Livestock & Fisheries Committee", "Agriculture", "assented", 2023),
    (25, "The Prevention of Livestock and Produce Theft Bill",
         "Senate Bills No. 12 of 2023",
         "Sen. Samson Cherarkey", "Agriculture", "at_na", 2023),
    (26, "The Agriculture and Food Authority (Amendment) Bill",
         "Senate Bills No. 13 of 2023",
         "Sen. James Murango", "Agriculture", "at_2nd_reading", 2023),
    (27, "The Equalization Fund (Administration) Bill",
         "Senate Bills No. 14 of 2023",
         "Chairperson, Finance & Budget Committee", "Finance & Budget", "at_na", 2023),
    (28, "The Constitution of Kenya (Amendment) Bill",
         "Senate Bills No. 15 of 2023",
         "Sen. Beth Syengo", "Justice & Legal", "at_2nd_reading", 2023),
    (29, "The County Allocation of Revenue Bill",
         "Senate Bills No. 16 of 2023",
         "Chairperson, Finance & Budget Committee", "Finance & Budget", "assented", 2023),
    (30, "The Maternal, Newborn and Child Health Bill",
         "Senate Bills No. 17 of 2023",
         "Sen. Beatrice Ogolla", "Health", "at_na", 2023),
    (31, "The County Hall of Fame Bill",
         "Senate Bills No. 18 of 2023",
         "Sen. Miraj A. Abdulrahman", "Labour & Social Welfare", "at_cowt", 2023),
    (32, "The Rice Bill",
         "Senate Bills No. 19 of 2023",
         "Sen. James Kamau Murango", "Agriculture", "withdrawn", 2023),
    (33, "The Law of Succession (Amendment) Bill",
         "Senate Bills No. 20 of 2023",
         "Sen. Veronica Maina", "Justice & Legal", "negatived", 2023),
    (34, "The County Governments (Revenue Raising Process) Bill",
         "Senate Bills No. 22 of 2023",
         "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2023),
    (35, "The Community Health Services Bill",
         "Senate Bills No. 24 of 2023",
         "Sen. Moses Kajwang'", "Health", "at_2nd_reading", 2023),
    (36, "The County Governments (Amendment) Bill",
         "Senate Bills No. 25 of 2023",
         "Sen. Samson Cherarkey", "Devolution", "at_na", 2023),
    (37, "The Public Finance Management (Amendment) Bill",
         "National Assembly Bills No. 16 of 2023",
         "The Senate Majority Leader", "Finance & Budget", "assented", 2023),
    (38, "The County Governments Additional Allocations Bill",
         "National Assembly Bills No. 23 of 2023",
         "The Senate Majority Leader", "Finance & Budget", "assented", 2023),
    (39, "The Care and Protection of Child Parents Bill",
         "Senate Bills No. 29 of 2023",
         "Sen. Miraj Abdilllahi Abdulrahman", "Labour & Social Welfare", "at_na", 2023),
    (40, "The Equalization Fund Appropriation (No. 2) Bill",
         "Senate Bills No. 30 of 2023",
         "Chairperson, Finance & Budget Committee", "Finance & Budget", "in_mediation", 2023),
    (41, "The Public Holidays (Amendment) Bill",
         "Senate Bills No. 31 of 2023",
         "Sen. Karungo Wa Thang'wa", "National Security", "withdrawn", 2023),
    (42, "The E-Health Bill",
         "Senate Bills No. 32 of 2023",
         "Sen. Hamida Kibwana", "Health", "at_2nd_reading", 2023),
    (43, "The County Assembly Services (Amendment) Bill",
         "Senate Bills No. 34 of 2023",
         "Sen. Mohamed Chute", "Devolution", "at_na", 2023),
    (44, "The Real Estate Regulation Bill",
         "Senate Bills No. 35 of 2023",
         "Sen. Allan Kiprotich Chesang", "Land & Environment", "at_2nd_reading", 2023),
    (45, "The Climate Change (Amendment) Bill",
         "National Assembly Bills No. 42 of 2023",
         "The Senate Majority Leader", "Land & Environment", "assented", 2023),
    (46, "The Food and Feed Safety Control Coordination Bill",
         "National Assembly Bills No. 21 of 2023",
         "The Senate Majority Leader", "Agriculture", "in_mediation", 2023),
    (47, "The Water (Amendment) Bill",
         "National Assembly Bills No. 33 of 2023",
         "The Senate Majority Leader", "Land & Environment", "assented", 2023),
    (48, "The Parliamentary Powers and Privileges (Amendment) Bill",
         "Senate Bills No. 37 of 2023",
         "Sen. Godfrey Osotsi", "Justice & Legal", "at_na", 2023),
    (49, "The Public Transport (Motorcycle Regulation) Bill",
         "Senate Bills No. 38 of 2023",
         "Sen. Boni Khalwale", "Roads & Housing", "at_na", 2023),
    (50, "The County Public Finance Laws (Amendment) Bill",
         "Senate Bills No. 39 of 2023",
         "Sen. Kathuri Murungi", "Finance & Budget", "assented", 2023),
    (51, "The Public Finance Management (Amendment) Bill",
         "Senate Bills No. 40 of 2023",
         "Sen. Hamida Kibwana", "Finance & Budget", "at_na", 2023),
    (52, "The Street Vendors (Protection of Livelihood) Bill",
         "Senate Bills No. 41 of 2023",
         "Sen. Esther Okenyuri", "Trade & Industry", "at_na", 2023),
    (53, "The Energy (Amendment) Bill",
         "Senate Bills No. 42 of 2023",
         "Sen. Edwin Sifuna", "Energy", "at_na", 2023),
    (54, "The Facilities Improvement Financing Bill",
         "Senate Bills No. 43 of 2023",
         "The Senate Majority Leader", "Health", "assented", 2023),
    (55, "The Primary Health Care Bill",
         "Senate Bills No. 44 of 2023",
         "The Senate Majority Leader", "Health", "assented", 2023),
    (56, "The Digital Health Bill",
         "National Assembly Bills No. 57 of 2023",
         "The Senate Majority Leader", "Health", "assented", 2023),
    (57, "The Social Health Insurance Bill",
         "National Assembly Bills No. 58 of 2023",
         "The Senate Majority Leader", "Health", "assented", 2023),
    (58, "The Sugar Bill",
         "National Assembly Bills No. 34 of 2022",
         "Sen. David W. Wafula", "Agriculture", "assented", 2022),
    (59, "The National Rating Bill",
         "National Assembly Bills No. 55 of 2022",
         "The Senate Majority Leader", "Land & Environment", "assented", 2022),
    (60, "The Meteorology Bill",
         "Senate Bills No. 45 of 2023",
         "The Senate Majority Leader", "Land & Environment", "assented", 2023),
    (61, "The Public Service (Values and Principles) (Amendment) Bill",
         "National Assembly Bills No. 46 of 2022",
         "Sen. Samson Cherarkey", "Labour & Social Welfare", "at_na", 2022),
    (62, "The National Construction Authority (Amendment) Bill",
         "National Assembly Bills No. 59 of 2022",
         "The Senate Majority Leader", "Roads & Housing", "at_na", 2022),
    (63, "The Statutory Instruments (Amendment) Bill",
         "National Assembly Bills No. 2 of 2023",
         "The Senate Majority Leader", "Justice & Legal", "assented", 2023),
    (64, "The Conflict of Interest Bill",
         "National Assembly Bills No. 12 of 2023",
         "The Senate Majority Leader", "Justice & Legal", "assented", 2023),
    (65, "The Gambling Control Bill",
         "National Assembly Bills No. 70 of 2023",
         "The Senate Majority Leader", "Labour & Social Welfare", "assented", 2023),
    (66, "The Wildlife Conservation and Management (Amendment) Bill",
         "Senate Bills No. 46 of 2023",
         "Sen. Johnes Mwaruma", "Land & Environment", "at_2nd_reading", 2023),
    (67, "The Nuts and Oil Crops Development Bill",
         "Senate Bills No. 47 of 2023",
         "Sen. Hamida Kibwana", "Agriculture", "at_cowt", 2023),
    (68, "The Wildlife Conservation and Management (Amendment) Bill",
         "Senate Bills No. 49 of 2023",
         "Sen. Lenku Ole Kanar Seki", "Land & Environment", "at_2nd_reading", 2023),
    (69, "The Local Content Bill",
         "Senate Bills No. 50 of 2023",
         "Chairperson, Energy Committee", "Energy", "at_na", 2023),
    (70, "The Constitution of Kenya (Amendment) (No. 2) Bill",
         "Senate Bills No. 52 of 2023",
         "Sen. Raphael Chimera", "Justice & Legal", "withdrawn", 2023),
    (71, "The Affordable Housing Bill",
         "National Assembly Bills No. 75 of 2023",
         "The Senate Majority Leader", "Roads & Housing", "assented", 2023),
    (72, "The Co-Operative Societies (Amendment) Bill",
         "Senate Bills No. 53 of 2023",
         "Sen. Omar Mariam Sheikh", "Trade & Industry", "at_cowt", 2023),
    (73, "The Early Childhood Education (Amendment) Bill",
         "Senate Bills No. 54 of 2023",
         "Sen. Eddy Oketch", "Education", "at_na", 2023),
    (74, "The Fire and Rescue Services Professionals Bill",
         "Senate Bills No. 55 of 2023",
         "Sen. Mohamed Abass Sheikh", "National Security", "at_na", 2023),
    (75, "The Narcotic Drugs and Psychotropic Substances (Control) (Amendment) Bill",
         "Senate Bills No. 1 of 2024",
         "Sen. Kathuri Murungi", "National Security", "at_2nd_reading", 2024),
    (76, "The Division of Revenue Bill",
         "National Assembly Bills No. 14 of 2024",
         "The Senate Majority Leader", "Finance & Budget", "assented", 2024),
    (77, "The Cancer Prevention and Control (Amendment) (No. 2) Bill",
         "National Assembly Bills No. 45 of 2022",
         "Sen. Samson Cherarkey", "Health", "at_na", 2022),
    (78, "The Houses of Parliament (Bicameral Relations) Bill",
         "National Assembly Bills No. 44 of 2023",
         "The Senate Majority Leader", "Justice & Legal", "in_mediation", 2023),
    (79, "The Statutory Instruments (Amendment) Bill",
         "National Assembly Bills No. 3 of 2024",
         "The Senate Majority Leader", "Justice & Legal", "at_2nd_reading", 2024),
    (80, "The County Governments Election Laws (Amendment) Bill",
         "Senate Bills No. 2 of 2024",
         "Sen. Crystal Asige", "Justice & Legal", "at_na", 2024),
    (81, "The County Oversight and Accountability Bill",
         "Senate Bills No. 3 of 2024",
         "Sen. Ledama Olekina & Sen. William Kisang", "Devolution", "at_cowt", 2024),
    (82, "The County Civic Education Bill",
         "Senate Bills No. 4 of 2024",
         "Sen. Esther Okenyuri", "Justice & Legal", "at_cowt", 2024),
    (83, "The County Statistics Bill",
         "Senate Bills No. 5 of 2024",
         "Sen. Ali Roba Ibrahim", "Finance & Budget", "withdrawn", 2024),
    (84, "The Provision of Sanitary Towels Bill",
         "Senate Bills No. 7 of 2024",
         "Sen. Gloria Orwoba", "Labour & Social Welfare", "at_2nd_reading", 2024),
    (85, "The Election Offences (Amendment) Bill",
         "Senate Bills No. 9 of 2024",
         "The Senate Majority Leader & Minority Leader", "Justice & Legal", "withdrawn", 2024),
    (86, "The Statutory Instruments (Amendment) Bill",
         "Senate Bills No. 10 of 2024",
         "The Senate Majority Leader & Minority Leader", "Justice & Legal", "at_cowt", 2024),
    (87, "The Elections (Amendment) Bill",
         "Senate Bills No. 11 of 2024",
         "The Senate Majority Leader & Minority Leader", "Justice & Legal", "withdrawn", 2024),
    (88, "The Intergovernmental Relations (Amendment) Bill",
         "Senate Bills No. 12 of 2024",
         "The Senate Majority Leader", "Devolution", "at_na", 2024),
    (89, "The Political Parties (Amendment) Bill",
         "Senate Bills No. 13 of 2024",
         "The Senate Majority Leader & Minority Leader", "Justice & Legal", "withdrawn", 2024),
    (90, "The County Assemblies Pensions Scheme Bill",
         "Senate Bills No. 14 of 2024",
         "The Senate Majority Leader", "Labour & Social Welfare", "at_na", 2024),
    (91, "The Land (Amendment) Bill",
         "National Assembly Bills No. 40 of 2022",
         "The Senate Majority Leader", "Land & Environment", "assented", 2022),
    (92, "The Independent Electoral and Boundaries Commission (Amendment) Bill",
         "National Assembly Bills No. 10 of 2024",
         "The Senate Majority Leader", "Justice & Legal", "assented", 2024),
    (93, "The Constitution of Kenya (Amendment) Bill",
         "Senate Bills No. 17 of 2024",
         "Sen. Crystal Asige", "Justice & Legal", "at_2nd_reading", 2024),
    (94, "The County Governments Additional Allocations Bill",
         "Senate Bills No. 19 of 2024",
         "Chairperson, Finance & Budget Committee", "Finance & Budget", "in_mediation", 2024),
    (95, "The County Wards (Equitable Development) Bill",
         "Senate Bills No. 20 of 2024",
         "Sen. Karungo Thangwa & Sen. Godfrey Osotsi", "Finance & Budget", "at_2nd_reading", 2024),
    (96, "The Environment Laws (Amendment) Bill",
         "Senate Bills No. 23 of 2024",
         "Sen. Abdul Haji", "Land & Environment", "at_cowt", 2024),
    (97, "The County Allocation of Revenue Bill",
         "Senate Bills No. 25 of 2024",
         "Chairperson, Finance & Budget Committee", "Finance & Budget", "assented", 2024),
    (98, "The Political Parties (Amendment) (No. 2) Bill",
         "Senate Bills No. 26 of 2024",
         "The Senate Majority Leader & Minority Leader", "Justice & Legal", "at_na", 2024),
    (99, "The Public Finance Management (Amendment) Bill",
         "Senate Bills No. 27 of 2024",
         "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2024),
    (100, "The Election Offences (Amendment) (No. 2) Bill",
          "Senate Bills No. 28 of 2024",
          "The Senate Majority Leader & Minority Leader", "Justice & Legal", "in_mediation", 2024),
    (101, "The Elections (Amendment) (No. 2) Bill",
          "Senate Bills No. 29 of 2024",
          "The Senate Majority Leader & Minority Leader", "Justice & Legal", "at_na", 2024),
    (102, "The Creative Economy Support Bill",
          "Senate Bills No. 30 of 2024",
          "Sen. Eddy Oketch", "Trade & Industry", "at_na", 2024),
    (103, "The Livestock Protection and Sustainability Bill",
          "Senate Bills No. 32 of 2024",
          "Sen. Lelegwe Ltumbesi", "Agriculture", "at_2nd_reading", 2024),
    (104, "The Sports (Amendment) Bill",
          "Senate Bills No. 33 of 2024",
          "Sen. Edwin Sifuna", "Labour & Social Welfare", "at_cowt", 2024),
    (105, "The County Governments (State Officers' Removal from Office) Procedure Bill",
          "Senate Bills No. 34 of 2024",
          "Sen. Karungo Thang'wa", "Justice & Legal", "at_2nd_reading", 2024),
    (106, "The Tobacco Control (Amendment) Bill",
          "Senate Bills No. 35 of 2024",
          "Sen. Catherine Mumma", "Health", "at_na", 2024),
    (107, "The National Disaster Management Bill",
          "National Assembly Bills No. 24 of 2023",
          "The Senate Majority Leader", "National Security", "in_mediation", 2023),
    (108, "The Public Fundraising Appeals Bill",
          "Senate Bills No. 36 of 2024",
          "The Senate Majority Leader", "Labour & Social Welfare", "at_cowt", 2024),
    (109, "The Division of Revenue (Amendment) Bill",
          "National Assembly Bills No. 38 of 2024",
          "The Senate Majority Leader", "Finance & Budget", "assented", 2024),
    (110, "The County Governments (Amendment) Bill",
          "Senate Bills No. 39 of 2024",
          "Sen. George Mbugua", "Devolution", "at_2nd_reading", 2024),
    (111, "The County Library Services Bill",
          "Senate Bills No. 40 of 2024",
          "Sen. Joyce Korir", "Labour & Social Welfare", "at_na", 2024),
    (112, "The Labour Migration and Management (No. 2) Bill",
          "Senate Bills No. 42 of 2024",
          "Sen. Tabitha Mutinda", "Labour & Social Welfare", "at_na", 2024),
    (113, "The Street Naming and Property Addressing System Bill",
          "Senate Bills No. 43 of 2024",
          "Sen. Fatuma Dullo", "Roads & Housing", "at_2nd_reading", 2024),
    (114, "The Sports (Amendment) (No. 2) Bill",
          "Senate Bills No. 45 of 2024",
          "Sen. Tom Ojienda & Sen. Raphael Chimera", "Labour & Social Welfare", "at_cowt", 2024),
    (115, "The Constitution of Kenya (Amendment) No. 2 Bill",
          "Senate Bills No. 46 of 2024",
          "Sen. Samson Cherarkey", "Justice & Legal", "at_2nd_reading", 2024),
    (116, "The Office of the County Attorney (Amendment) Bill",
          "Senate Bills No. 47 of 2024",
          "Sen. David Wakoli", "Devolution", "at_cowt", 2024),
    (117, "The Business Laws (Amendment) Bill",
          "Senate Bills No. 51 of 2024",
          "The Senate Majority Leader", "Trade & Industry", "at_na", 2024),
    (118, "The County Governments Laws (Amendment) Bill",
          "Senate Bills No. 52 of 2024",
          "Sen. Kathuri Murungi", "Devolution", "at_2nd_reading", 2024),
    (119, "The Community Health Promoters Bill",
          "National Assembly Bills No. 53 of 2022",
          "The Senate Majority Leader", "Health", "at_2nd_reading", 2022),
    (120, "The Kenya Health Products and Technologies Regulatory Authority Bill",
          "National Assembly Bills No. 54 of 2022",
          "The Senate Majority Leader", "Health", "at_2nd_reading", 2022),
    (121, "The Technopolis Bill",
          "National Assembly Bills No. 6 of 2024",
          "The Senate Majority Leader", "ICT", "at_na", 2024),
    (122, "The Public Finance Management (Amendment) (No. 3) Bill",
          "National Assembly Bills No. 44 of 2024",
          "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2024),
    (123, "The Public Finance Management (Amendment) (No. 4) Bill",
          "National Assembly Bills No. 45 of 2024",
          "The Senate Majority Leader", "Finance & Budget", "at_na", 2024),
    (124, "The Public Procurement and Asset Disposal (Amendment) Bill",
          "National Assembly Bills No. 48 of 2024",
          "The Senate Majority Leader", "Finance & Budget", "at_cowt", 2024),
    (125, "The Cooperatives Bill",
          "National Assembly Bills No. 7 of 2024",
          "The Senate Majority Leader", "Trade & Industry", "at_na", 2024),
    (126, "The County Governments Additional Allocation Bill",
          "Senate Bills No. 1 of 2025",
          "Chairperson, Finance & Budget Committee", "Finance & Budget", "assented", 2025),
    (127, "The County Governments (Revenue Raising Process) Bill",
          "National Assembly Bills No. 11 of 2023",
          "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2023),
    (128, "The Public Audit (Amendment) Bill",
          "National Assembly Bills No. 4 of 2024",
          "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2024),
    (129, "The Public Finance Management (Amendment) (No. 2) Bill",
          "National Assembly Bills No. 26 of 2024",
          "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2024),
    (130, "The County Governments Additional Allocations Bill",
          "National Assembly Bills No. 2 of 2025",
          "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2025),
    (131, "The Division of Revenue Bill",
          "National Assembly Bills No. 10 of 2025",
          "The Senate Majority Leader", "Finance & Budget", "assented", 2025),
    (132, "The Social Protection Bill",
          "National Assembly Bills No. 12 of 2025",
          "The Senate Majority Leader", "Labour & Social Welfare", "assented", 2025),
    (133, "The Equalisation Fund Appropriation Bill",
          "Senate Bills No. 7 of 2025",
          "Chairperson, Finance & Budget Committee", "Finance & Budget", "at_na", 2025),
    (134, "The County Governments Additional Allocations (No. 2) Bill",
          "Senate Bills No. 8 of 2025",
          "Chairperson, Finance & Budget Committee", "Finance & Budget", "assented", 2025),
    (135, "The County Allocation of Revenue Bill",
          "Senate Bills No. 9 of 2025",
          "Chairperson, Finance & Budget Committee", "Finance & Budget", "assented", 2025),
    (136, "The Seeds and Plant Varieties (Amendment) Bill",
          "Senate Bills No. 4 of 2025",
          "Sen. Ledama Olekina", "Agriculture", "at_cowt", 2025),
    (137, "The Kenya National Council for Population and Development Bill",
          "National Assembly Bills No. 72 of 2023",
          "The Senate Majority Leader", "Finance & Budget", "at_cowt", 2023),
    (138, "The Culture Bill",
          "National Assembly Bills No. 12 of 2024",
          "The Senate Majority Leader", "Labour & Social Welfare", "at_2nd_reading", 2024),
    (139, "The Constitution of Kenya (Amendment) Bill",
          "Senate Bills No. 13 of 2025",
          "The Senate Majority Leader & Minority Leader", "Justice & Legal", "at_2nd_reading", 2025),
    (140, "The Electronic Equipment Disposal Recycling and Reuse Bill",
          "Senate Bills No. 5 of 2025",
          "Sen. Peris Tobiko", "ICT", "at_cowt", 2025),
    (141, "The Energy (Amendment) Bill",
          "Senate Bills No. 11 of 2025",
          "Chairperson, Energy Committee", "Energy", "withdrawn", 2025),
    (142, "The Health (Amendment) Bill",
          "Senate Bills No. 12 of 2025",
          "Sen. Mogeni Erick Okong'o", "Health", "at_2nd_reading", 2025),
    (143, "The Constitution of Kenya (Amendment) (No. 2) Bill",
          "Senate Bills No. 16 of 2025",
          "The Senate Majority Leader", "Justice & Legal", "at_2nd_reading", 2025),
    (144, "The County Governments Laws (Amendment) Bill",
          "Senate Bills No. 14 of 2025",
          "Sen. Abdul Haji", "Devolution", "at_2nd_reading", 2025),
    (145, "The National Construction Authority (Amendment) Bill",
          "Senate Bills No. 15 of 2025",
          "Sen. Eddy Oketch", "Roads & Housing", "at_2nd_reading", 2025),
    (146, "The Agriculture Produce (Minimum Guaranteed Returns) Bill",
          "Senate Bills No. 17 of 2025",
          "Sen. Veronica Maina", "Agriculture", "at_2nd_reading", 2025),
    (147, "The Kenya Roads (Amendment) (No. 3) Bill",
          "National Assembly Bills No. 34 of 2025",
          "The Senate Majority Leader", "Roads & Housing", "at_2nd_reading", 2025),
    (148, "The Environmental Management and Coordination (Amendment) Bill",
          "National Assembly Bills No. 66 of 2023",
          "Sen. Crystal Asige (Co-Sponsor)", "Land & Environment", "at_2nd_reading", 2023),
    (149, "The Autism Management Bill",
          "Senate Bills No. 19 of 2025",
          "Sen. Karen Nyamu", "Health", "at_2nd_reading", 2025),
    (150, "The Assisted Reproductive Technology Bill",
          "National Assembly Bills No. 61 of 2022",
          "Sen. Catherine Mumma (Co-Sponsor)", "Health", "at_2nd_reading", 2022),
    (151, "The Public Service Internship Bill",
          "National Assembly Bills No. 63 of 2022",
          "The Senate Majority Leader", "Labour & Social Welfare", "at_2nd_reading", 2022),
    (152, "The Basic Education (Amendment) Bill",
          "National Assembly Bills No. 59 of 2023",
          "The Senate Majority Leader", "Education", "at_2nd_reading", 2023),
    (153, "The Mining (Amendment) Bill",
          "Senate Bills No. 22 of 2025",
          "Sen. Karen Nyamu", "Land & Environment", "at_2nd_reading", 2025),
    (154, "The Division of Revenue Bill",
          "National Assembly Bills No. 2 of 2026",
          "The Senate Majority Leader", "Finance & Budget", "at_2nd_reading", 2026),
]


_SOURCE_URL = "https://parliament.go.ke/sites/default/files/2026-03/Bills%20Tracker%20updated%20as%20at%2019.03.2026.pdf"
_AS_AT_DATE = "19 March 2026"

# True  = Senate passed WITH amendments
# False = Senate passed WITHOUT amendments
# None  = not yet at that stage / negatived / withdrawn
_SENATE_AMENDMENT = {
    1: True,  2: True,  3: True,  4: True,  5: True,
    6: False, 8: True,  10: False,11: True, 12: True,
    13: True, 14: True, 16: True, 17: True, 18: True,
    19: True, 20: True, 22: True, 23: False,24: True,
    25: True, 27: True, 29: True, 30: True, 36: False,
    37: True, 38: True, 39: False,40: True, 43: True,
    45: False,46: True, 47: True, 48: True, 49: True,
    50: True, 51: True, 52: True, 53: False,54: True,
    55: True, 56: False,57: False,58: True, 59: True,
    60: True, 61: True, 62: True, 63: True, 64: True,
    65: True, 69: True, 71: True, 73: True, 74: True,
    76: True, 77: True, 78: True, 80: True, 88: True,
    90: True, 91: True, 92: True, 94: True, 97: True,
    98: True, 100: True,101: True,102: True,106: True,
    107: True,109: True,111: True,112: True,117: False,
    121: True,123: True,125: True,126: True,131: True,
    132: False,133: True,134: True,135: True,
}

_WOMEN_FIRST_NAMES = {
    "Crystal", "Gloria", "Hamida", "Karen", "Joyce",
    "Tabitha", "Beatrice", "Esther", "Catherine",
    "Veronica", "Beth", "Fatuma", "Peris", "Mariam", "Margaret",
}

# Year each assented bill was signed into law (used for time-to-law analysis).
_ASSENT_YEARS = {
    2: 2022, 6: 2023, 8: 2023, 16: 2023, 20: 2025,
    23: 2023, 24: 2026, 29: 2023, 30: 2024, 37: 2024,
    38: 2024, 45: 2023, 47: 2024, 50: 2023, 54: 2024,
    55: 2024, 56: 2023, 57: 2023, 58: 2025, 59: 2025,
    60: 2024, 63: 2024, 64: 2024, 65: 2025, 71: 2024,
    76: 2025, 91: 2024, 92: 2024, 97: 2025, 109: 2025,
    126: 2025, 131: 2025, 133: 2025, 134: 2025, 135: 2025,
}

# Plain-English one-sentence summary for each bill.
_BILL_SUMMARIES = {
    1:   "Establishes a regulatory framework for vocational and technical training institutions including governance and quality standards.",
    2:   "Allocates additional conditional grants to county governments for the 2021/22 financial year.",
    3:   "Amends parliamentary powers legislation to strengthen freedom of speech and protection of parliamentary proceedings.",
    4:   "Amends the classes of natural resource transactions that must be ratified by Parliament.",
    5:   "Provides a legislative framework for the progressive realisation of economic and social rights guaranteed under Article 43.",
    6:   "Amends the IEBC Act to address governance and operational reforms following the 2022 general election.",
    7:   "Would have required government entities to settle supplier invoices within set timelines; negatived at Senate.",
    8:   "Creates uniform licensing procedures across all 47 counties to reduce business registration costs and complexity.",
    9:   "Proposed to establish a county-level printer's office for official publications; withdrawn.",
    10:  "Amends the Employment Act to strengthen worker protections including maternity and paternity leave entitlements.",
    11:  "Establishes a framework for delivery of agricultural and livestock extension services to farmers.",
    12:  "Provides a legal framework for production, processing, marketing, and development of Kenya's mung bean industry.",
    13:  "Creates a legal and regulatory ecosystem to support, promote, and facilitate the growth of startups in Kenya.",
    14:  "Modernises the governance, marketing, and regulation of Kenya's tea industry.",
    15:  "Proposed amendments to the Konza Technopolis Authority Act; negatived at Senate.",
    16:  "Appropriates funds from the national Equalization Fund to finance basic services in marginalised areas.",
    17:  "Strengthens inclusive education rights and support mechanisms for learners with disabilities in Kenya's schools.",
    18:  "Establishes a comprehensive framework for the revival and development of Kenya's cotton industry from farming to ginning.",
    19:  "Provides a statutory framework to define, address, and resolve boundary disputes between counties.",
    20:  "Aligns the Persons with Disabilities Act with the Constitution and strengthens enforcement of disability rights.",
    21:  "Proposes amendments to heritage and museums legislation; still at Senate committee stage.",
    22:  "Recognises Kenyan Sign Language as an official language and mandates its promotion across public services.",
    23:  "Divides revenue between the national and county governments for the 2023/24 financial year.",
    24:  "Provides a comprehensive framework for the governance, production, processing, marketing, and development of Kenya's coffee industry.",
    25:  "Establishes a livestock identification and traceability system and dedicated enforcement mechanisms to combat livestock theft.",
    26:  "Proposes amendments to the Agriculture and Food Authority Act; awaiting Senate committee consideration.",
    27:  "Establishes an administrative board and disbursement framework for the national Equalization Fund.",
    28:  "Proposes constitutional amendments; still at 2nd reading in the Senate.",
    29:  "Allocates the equitable share of national revenue to each of the 47 counties for 2023/24.",
    30:  "Establishes a legal framework for maternal, newborn, child, and adolescent health services across Kenya.",
    31:  "Proposes a county-level hall of fame recognition programme; still at Senate committee stage.",
    32:  "Would have regulated rice production and marketing; withdrawn before passage.",
    33:  "Proposed amendments to the Law of Succession Act; negatived at Senate.",
    34:  "Proposes to amend the procedures counties must follow when raising own-source revenue; at 2nd reading.",
    35:  "Provides a legal framework for community health services including the role of community health promoters; at 2nd reading.",
    36:  "Amends the County Governments Act to strengthen devolution governance and administrative structures.",
    37:  "Amends the PFM Act to strengthen fiscal responsibility and financial reporting at national and county levels.",
    38:  "Provides additional conditional grants to county governments for a specific financial year.",
    39:  "Establishes support mechanisms and social protection for girls who become pregnant while still in school.",
    40:  "A second appropriation from the national Equalization Fund for the financial year; in mediation.",
    41:  "Would have amended the list of national public holidays; withdrawn.",
    42:  "Proposes a legal framework for electronic health information systems and digital health data governance; at 2nd reading.",
    43:  "Establishes an independent service board for county assembly staff to professionalise county legislatures.",
    44:  "Proposes regulation of the real estate sector including licensing of agents and developers; at 2nd reading.",
    45:  "Amends the Climate Change Act to strengthen Kenya's climate governance and NDC implementation.",
    46:  "Establishes a comprehensive food and animal feed safety regulatory framework; in mediation.",
    47:  "Amends the Water Act to address regulatory gaps and improve governance of water resources.",
    48:  "Further amends the Parliamentary Powers and Privileges Act to update procedural rules.",
    49:  "Regulates the boda boda motorcycle transport industry including licensing, safety standards, and insurance requirements.",
    50:  "Amends county public finance legislation to improve fiscal management and accountability at the devolved level.",
    51:  "Further amends the PFM Act to strengthen public financial accountability mechanisms.",
    52:  "Provides legal protections and designated trading spaces for street vendors and hawkers in Kenyan towns.",
    53:  "Amends the Energy Act to update regulatory provisions governing Kenya's energy sector.",
    54:  "Amends the Facilities Improvement Fund Act to improve disbursement and oversight of health facility funds.",
    55:  "Establishes a legal framework for primary healthcare as the foundation of universal health coverage.",
    56:  "Provides a framework for digital health systems including electronic medical records and health data governance.",
    57:  "Establishes the Social Health Authority (SHA) to replace NHIF and manage universal health coverage funding.",
    58:  "Provides a comprehensive framework for regulating Kenya's sugar industry including production, milling, and marketing.",
    59:  "Establishes a national property rating system to standardise land and building valuation across all counties.",
    60:  "Establishes a modern legal framework for meteorological services, weather forecasting, and climate data management.",
    61:  "Amends the Public Service Values and Principles Act to strengthen ethical conduct and accountability in the public service.",
    62:  "Amends the NCA Act to strengthen regulation and standards in Kenya's construction industry.",
    63:  "Amends the Statutory Instruments Act to improve parliamentary scrutiny of subsidiary legislation.",
    64:  "Establishes a comprehensive framework to prevent and manage conflicts of interest among public servants.",
    65:  "Establishes a Gambling Control Authority and modern regulatory framework for all forms of gambling in Kenya.",
    66:  "Proposes amendments to wildlife conservation and management legislation; at 2nd reading.",
    67:  "Proposes establishment of an authority to develop Kenya's nuts and oil crops sector; in Senate committee.",
    68:  "A second bill proposing wildlife conservation amendments; at 2nd reading.",
    69:  "Requires prioritisation of Kenyan goods, services, and workers in public contracts and key economic sectors.",
    70:  "Proposed constitutional amendments; withdrawn.",
    71:  "Amends the Affordable Housing Act to refine the housing levy mechanism and fund administration.",
    72:  "Proposes amendments to co-operative societies legislation; still in Senate committee.",
    73:  "Establishes a national framework for early childhood education including teacher qualifications and standards.",
    74:  "Creates a national fire and rescue services framework to replace colonial-era legislation.",
    75:  "Amends drug control legislation to update penalties and enforcement mechanisms; at 2nd reading.",
    76:  "Divides revenue between national and county governments for 2024/25; passed after contentious mediation.",
    77:  "Amends cancer control legislation to expand screening access, treatment, and recognition of caregiver rights.",
    78:  "Establishes clearer procedures for how the Senate and National Assembly interact on shared legislation; in mediation.",
    79:  "A National Assembly version amending the Statutory Instruments Act; at 2nd reading.",
    80:  "Amends electoral laws affecting county governments including ward demarcation procedures.",
    81:  "Proposes strengthened oversight mechanisms for county governments by county assemblies; in Senate committee.",
    82:  "Establishes a framework for civic education at the county level; in Senate committee.",
    83:  "Would have created a county statistics framework; withdrawn.",
    84:  "Requires free provision of sanitary towels in public schools to address period poverty among girls; at 2nd reading.",
    85:  "Proposed amendments to election offences legislation; withdrawn.",
    86:  "A comprehensive standalone statutory instruments bill; in Senate committee.",
    87:  "Proposed election amendments; withdrawn.",
    88:  "Amends the Intergovernmental Relations Act to strengthen cooperation mechanisms between national and county governments.",
    89:  "Proposed political party amendments; withdrawn.",
    90:  "Establishes a defined pension scheme for county assembly members and staff.",
    91:  "Amends land legislation to address gaps in land administration and strengthen security of tenure.",
    92:  "Further amends the IEBC Act to implement electoral reform recommendations from post-2022 election reviews.",
    93:  "Proposes constitutional amendments; at 2nd reading.",
    94:  "Provides additional conditional grants to county governments for 2023/24; in mediation.",
    95:  "Proposes a dedicated development fund for each ward across Kenya's 47 counties; at 2nd reading.",
    96:  "Proposes omnibus amendments to environment and land laws; in Senate committee.",
    97:  "Allocates the equitable share of national revenue to each of the 47 counties for 2024/25.",
    98:  "Comprehensive amendments to political parties legislation covering governance, financing, and party discipline.",
    99:  "Further amends the PFM Act; at 2nd reading.",
    100: "Amends election offences legislation; in mediation between the Senate and National Assembly.",
    101: "Amends electoral legislation ahead of the 2027 general elections; at the National Assembly.",
    102: "Establishes a framework to support Kenya's creative economy including arts, music, film, and craft industries.",
    103: "Proposes measures for livestock disease control and improved animal welfare standards; at 2nd reading.",
    104: "Proposed amendments to sports sector legislation; in Senate committee.",
    105: "Proposes a framework for removing errant county government state officers from office; at 2nd reading.",
    106: "Amends tobacco control legislation to align with Kenya's obligations under the WHO FCTC.",
    107: "Establishes a comprehensive national disaster risk management system; in mediation.",
    108: "Regulates public fundraising appeals including harambees and online fundraising; in Senate committee.",
    109: "Amends the Division of Revenue Act to revise the national-county revenue sharing formula.",
    110: "Proposes county governance amendments; at 2nd reading.",
    111: "Establishes county-level library services and a national public library management framework.",
    112: "Provides a framework for managing labour migration and protecting Kenyan workers employed abroad.",
    113: "Proposes a national street naming and property addressing system for better urban planning; at 2nd reading.",
    114: "Further amendments to sports sector legislation; in Senate committee.",
    115: "Proposes constitutional amendments; at 2nd reading.",
    116: "Proposes establishment of a county attorney's office to provide legal advice to county governments; in committee.",
    117: "Amends multiple business laws to improve Kenya's ease-of-doing-business ranking and reduce red tape.",
    118: "Omnibus amendments to county governance legislation for 2024; at 2nd reading.",
    119: "Provides for the formal employment and remuneration of community health promoters; at 2nd reading.",
    120: "Establishes a regulatory framework for health products, medical devices, and technologies in Kenya; at 2nd reading.",
    121: "Amends the Konza Technopolis Authority framework to accelerate development of the technology park.",
    122: "Third PFM amendment bill; at 2nd reading.",
    123: "Fourth PFM amendment bill strengthening financial accountability and reporting requirements.",
    124: "Amends procurement legislation to improve transparency and efficiency in public procurement; in committee.",
    125: "Comprehensive legislation for co-operative societies to replace outdated co-operatives framework.",
    126: "Provides additional conditional grants to county governments for the 2024/25 financial year.",
    127: "Further amendments to county revenue raising procedures; at 2nd reading.",
    128: "Amends public audit legislation to strengthen financial oversight and auditor independence; at 2nd reading.",
    129: "Second major PFM amendment bill; at 2nd reading.",
    130: "Additional county allocations for 2024/25 financial year; at 2nd reading.",
    131: "Divides revenue between national and county governments for 2025/26; passed after mediation.",
    132: "Amends social protection legislation to expand coverage for vulnerable and marginalised groups.",
    133: "Appropriates Equalization Fund resources for the 2025/26 financial year.",
    134: "Second batch of additional conditional grants to county governments for 2025/26.",
    135: "Allocates the equitable share of national revenue to each of the 47 counties for 2025/26.",
    136: "Proposes amendments to seeds and plant varieties legislation; in Senate committee.",
    137: "Amends the Kenya National Council for Population and Development Act; in committee.",
    138: "Establishes a framework for promoting, preserving, and developing Kenya's diverse cultural heritage; at 2nd reading.",
    139: "Proposes constitutional amendments for 2025; at 2nd reading.",
    140: "Proposes regulation of electronic equipment disposal and e-waste management; in Senate committee.",
    141: "Proposed energy sector amendments; withdrawn.",
    142: "Proposes amendments to health sector legislation; at 2nd reading.",
    143: "Second constitutional amendment bill for 2025; at 2nd reading.",
    144: "Omnibus county governance amendments for 2025; at 2nd reading.",
    145: "Amends the NCA Act for 2025 to update construction industry regulation; at 2nd reading.",
    146: "Proposes guaranteed minimum returns for agricultural producers to reduce price volatility; at 2nd reading.",
    147: "Third amendment bill for Kenya's roads legislation; at 2nd reading.",
    148: "Amends the Environmental Management and Co-ordination Act; at 2nd reading.",
    149: "Provides for the diagnosis, support, treatment, and management of autism spectrum disorder in Kenya; at 2nd reading.",
    150: "Regulates assisted reproductive technology including IVF, surrogacy, and gamete donation in Kenya; at 2nd reading.",
    151: "Establishes a structured internship programme for graduates seeking entry into the public service; at 2nd reading.",
    152: "Proposes amendments to basic education legislation; at 2nd reading.",
    153: "Amends mining legislation to address gaps in mineral rights administration and benefit-sharing; at 2nd reading.",
    154: "Divides revenue between national and county governments for the 2026/27 financial year.",
}

# Kenya Kwanza (ruling coalition) and Azimio la Umoja (opposition) parties.
_KK_PARTIES = {
    "United Democratic Alliance", "UDA",
    "Amani National Congress", "ANC",
    "Ford Kenya", "FORD-Kenya", "FORD-KENYA",
    "Maendeleo Chap Chap", "MCC",
    "KANU",
    "Chama Cha Mashinani", "CCM",
    "Pamoja African Alliance",
}
_AZIMIO_PARTIES = {
    "Orange Democratic Movement", "ODM",
    "Wiper Democratic Movement", "Wiper",
    "Jubilee",
    "Narc Kenya", "NARC-Kenya", "NARC-K",
    "United Progressive Alliance",
}

def _classify_coalition(party: str) -> str:
    if not party:
        return "Other/Nominated"
    p = party.strip()
    for kk in _KK_PARTIES:
        if kk.lower() in p.lower():
            return "Kenya Kwanza"
    for az in _AZIMIO_PARTIES:
        if az.lower() in p.lower():
            return "Azimio"
    return "Other/Nominated"

# Institutional sponsor patterns → senator surname fragment used to fetch the
# actual holder's photo and party info.  Keep lowercase, no punctuation.
_INSTITUTIONAL_SPONSORS = {
    "majority leader": "cheruiyot",   # Aaron Kipkirui Cheruiyot
    "minority leader": "madzayo",     # Stewart Madzayo (Kilifi)
}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_bills_list():
    return [
        {
            "number":         b[0],
            "title":          b[1],
            "bill_ref":       b[2],
            "sponsor":        b[3],
            "committee":      b[4],
            "status":         b[5],
            "status_label":   STATUS_LABELS[b[5]],
            "year":           b[6],
            "senate_amended": _SENATE_AMENDMENT.get(b[0]),
            "assent_year":    _ASSENT_YEARS.get(b[0]),
            "summary":        _BILL_SUMMARIES.get(b[0], ""),
        }
        for b in _BILLS_RAW
    ]


def _bill_stats(bills):
    status_counts = Counter(b["status"] for b in bills)
    return status_counts, {
        "total":         len(bills),
        "assented":      status_counts["assented"],
        "at_na":         status_counts["at_na"],
        "active_senate": status_counts["at_2nd_reading"] + status_counts["at_cowt"],
        "in_mediation":  status_counts["in_mediation"],
        "negatived":     status_counts["negatived"],
        "withdrawn":     status_counts["withdrawn"],
    }


def _parse_sponsors(sponsor_str):
    """Return list of individual senator names; skip institutional sponsors."""
    if any(x in sponsor_str for x in ["Majority Leader", "Minority Leader", "Chairperson,"]):
        return []
    parts = re.split(r"\s*&\s*", sponsor_str)
    result = []
    for p in parts:
        p = re.sub(r"\s*\(.*?\)", "", p).strip()
        if p and "Sen." in p:
            result.append(p)
    return result


# ── Views ─────────────────────────────────────────────────────────────────────

def bills_tracker(request):
    """Senate Bills Tracker — 13th Parliament (as at 19 March 2026)."""
    bills = _make_bills_list()
    _, stats = _bill_stats(bills)

    return render(request, "scorecard/bills.html", {
        "bills":         bills,
        "stats":         stats,
        "committees":    sorted({b["committee"] for b in bills}),
        "years":         sorted({b["year"]      for b in bills}),
        "status_labels": STATUS_LABELS,
        "as_at_date":    _AS_AT_DATE,
        "source_url":    _SOURCE_URL,
    })


def bills_analytics(request):  # noqa: C901
    """Bills data-analytics dashboard — 13th Parliament."""
    from collections import defaultdict
    from scorecard.models import Senator

    bills = _make_bills_list()
    status_counts, stats = _bill_stats(bills)
    total = stats["total"]

    # ── Pipeline order / labels ──────────────────────────────────────────────
    pipeline_order = [
        "at_2nd_reading", "at_cowt", "at_na",
        "in_mediation", "presidential_memo", "assented",
        "negatived", "withdrawn",
    ]
    pipeline_labels = {
        "at_2nd_reading":    "At Second Reading",
        "at_cowt":           "At Committee (Senate)",
        "at_na":             "At National Assembly",
        "in_mediation":      "In Mediation",
        "presidential_memo": "Presidential Memorandum",
        "assented":          "Assented into Law",
        "negatived":         "Negatived",
        "withdrawn":         "Withdrawn",
    }

    # ── Funnel ───────────────────────────────────────────────────────────────
    survived = total - status_counts["negatived"] - status_counts["withdrawn"]
    cleared_senate = (
        status_counts["at_na"] + status_counts["in_mediation"]
        + status_counts.get("presidential_memo", 0) + status_counts["assented"]
    )
    funnel = [
        {"label": "Bills Introduced",        "count": total,          "pct": 100.0},
        {"label": "Not Negatived/Withdrawn",  "count": survived,       "pct": round(survived / total * 100, 1)},
        {"label": "Cleared the Senate",       "count": cleared_senate, "pct": round(cleared_senate / total * 100, 1)},
        {"label": "Assented into Law",        "count": status_counts["assented"],
         "pct": round(status_counts["assented"] / total * 100, 1)},
    ]

    # ── Year-over-year ───────────────────────────────────────────────────────
    year_map = {}
    for b in bills:
        y = b["year"]
        if y not in year_map:
            year_map[y] = {"assented": 0, "active": 0, "lapsed": 0}
        if b["status"] == "assented":
            year_map[y]["assented"] += 1
        elif b["status"] in ("negatived", "withdrawn"):
            year_map[y]["lapsed"] += 1
        else:
            year_map[y]["active"] += 1
    years_sorted = sorted(year_map)

    # ── Committee performance ────────────────────────────────────────────────
    comm_map = {}
    for b in bills:
        c = b["committee"]
        if c not in comm_map:
            comm_map[c] = {"total": 0, "assented": 0, "active": 0, "lapsed": 0}
        comm_map[c]["total"] += 1
        if b["status"] == "assented":
            comm_map[c]["assented"] += 1
        elif b["status"] in ("negatived", "withdrawn"):
            comm_map[c]["lapsed"] += 1
        else:
            comm_map[c]["active"] += 1
    for v in comm_map.values():
        v["assent_rate"] = round(v["assented"] / v["total"] * 100, 1) if v["total"] else 0
    committee_list = sorted(comm_map.items(), key=lambda x: x[1]["total"], reverse=True)

    # ── Bill origin ──────────────────────────────────────────────────────────
    senate_bills = [b for b in bills if "Senate Bills" in b["bill_ref"]]
    na_bills     = [b for b in bills if "National Assembly" in b["bill_ref"]]
    s_assented   = sum(1 for b in senate_bills if b["status"] == "assented")
    n_assented   = sum(1 for b in na_bills     if b["status"] == "assented")

    # ── Top individual sponsors ──────────────────────────────────────────────
    sponsor_ctr = Counter()
    for b in bills:
        for name in _parse_sponsors(b["sponsor"]):
            sponsor_ctr[name] += 1
    top_sponsors_raw = sponsor_ctr.most_common(15)

    # ── NEW: Cohort completion ────────────────────────────────────────────────
    cohort = {}
    for b in bills:
        y = str(b["year"])
        if y not in cohort:
            cohort[y] = {"total": 0, "assented": 0, "active": 0, "lapsed": 0}
        cohort[y]["total"] += 1
        if b["status"] == "assented":
            cohort[y]["assented"] += 1
        elif b["status"] in ("negatived", "withdrawn"):
            cohort[y]["lapsed"] += 1
        else:
            cohort[y]["active"] += 1
    cohort_labels = sorted(cohort)
    for c in cohort.values():
        c["assent_rate"] = round(c["assented"] / c["total"] * 100, 1) if c["total"] else 0

    # ── NEW: National Assembly dynamics ──────────────────────────────────────
    cleared = [b for b in bills if b["status"] in ("at_na", "in_mediation", "presidential_memo", "assented")]
    pres_memo_count = status_counts.get("presidential_memo", 0)
    na_dynamics = {
        "cleared_senate":    len(cleared),
        "assented":          status_counts["assented"],
        "pending_na":        status_counts["at_na"],
        "in_mediation":      status_counts["in_mediation"],
        "presidential_memo": pres_memo_count,
        "assent_rate":       round(status_counts["assented"] / len(cleared) * 100, 1) if cleared else 0,
    }

    # ── NEW: Amendment analysis ───────────────────────────────────────────────
    known_amend   = [b for b in bills if b["senate_amended"] is not None]
    amended_bills = [b for b in known_amend if b["senate_amended"]]
    clean_bills   = [b for b in known_amend if not b["senate_amended"]]
    am_assented   = sum(1 for b in amended_bills if b["status"] == "assented")
    cl_assented   = sum(1 for b in clean_bills   if b["status"] == "assented")
    amendment_stats = {
        "known":               len(known_amend),
        "amended":             len(amended_bills),
        "clean":               len(clean_bills),
        "amended_pct":         round(len(amended_bills) / len(known_amend) * 100, 1) if known_amend else 0,
        "amended_assent_rate": round(am_assented / len(amended_bills) * 100, 1) if amended_bills else 0,
        "clean_assent_rate":   round(cl_assented / len(clean_bills) * 100, 1) if clean_bills else 0,
    }

    # ── NEW: Women vs men vs leadership ──────────────────────────────────────
    def _is_women(sponsor):
        return any(n in sponsor for n in _WOMEN_FIRST_NAMES)

    def _is_leadership(sponsor):
        return "Majority Leader" in sponsor or "Chairperson," in sponsor

    women_bills      = [b for b in bills if _is_women(b["sponsor"])]
    leadership_bills = [b for b in bills if _is_leadership(b["sponsor"])]
    men_bills        = [b for b in bills if not _is_women(b["sponsor"]) and not _is_leadership(b["sponsor"])]

    def _gstat(grp):
        n = len(grp)
        a = sum(1 for b in grp if b["status"] == "assented")
        return {"total": n, "assented": a, "assent_rate": round(a / n * 100, 1) if n else 0}

    gender_stats = {
        "women":      _gstat(women_bills),
        "men":        _gstat(men_bills),
        "leadership": _gstat(leadership_bills),
    }

    # ── NEW: Stalled bills (introduced ≤ 2023, still active in Senate) ────────
    stalled = sorted(
        [b for b in bills if b["year"] <= 2023 and b["status"] in ("at_2nd_reading", "at_cowt")],
        key=lambda x: x["year"],
    )

    # ── NEW: Committee × Year heatmap ─────────────────────────────────────────
    heatmap_data = defaultdict(lambda: defaultdict(int))
    for b in bills:
        heatmap_data[b["committee"]][str(b["year"])] += 1
    heatmap_years = [str(y) for y in sorted({b["year"] for b in bills})]
    heatmap_comms = sorted(heatmap_data.keys())
    all_cells     = [heatmap_data[c][y] for c in heatmap_comms for y in heatmap_years]
    heatmap_max   = max(all_cells) if all_cells else 1

    # ── NEW: Sponsor success rates (sponsors with ≥ 2 bills) ─────────────────
    sponsor_detail = defaultdict(lambda: {"total": 0, "assented": 0})
    for b in bills:
        for name in _parse_sponsors(b["sponsor"]):
            sponsor_detail[name]["total"] += 1
            if b["status"] == "assented":
                sponsor_detail[name]["assented"] += 1

    sponsor_success = sorted(
        [
            {
                "name":     name,
                "total":    d["total"],
                "assented": d["assented"],
                "rate":     round(d["assented"] / d["total"] * 100, 1),
            }
            for name, d in sponsor_detail.items()
            if d["total"] >= 2
        ],
        key=lambda x: (-x["total"], -x["rate"]),
    )

    # ── NEW: Senator cross-link ───────────────────────────────────────────────
    senator_lookup = {}
    try:
        for s in Senator.objects.values("senator_id", "name"):
            full  = s["name"].strip().lower()
            parts = full.split()
            senator_lookup[full] = s["senator_id"]
            for i in range(len(parts)):
                frag = " ".join(parts[i:])
                if len(frag) > 3 and frag not in senator_lookup:
                    senator_lookup[frag] = s["senator_id"]
    except Exception:
        pass

    def _find_senator_id(sponsor_str):
        clean = re.sub(r"Sen\.\s*", "", sponsor_str)
        clean = re.sub(r"\s*\(.*?\)", "", clean).strip().lower()
        if clean in senator_lookup:
            return senator_lookup[clean]
        parts = clean.split()
        for i in range(len(parts)):
            frag = " ".join(parts[i:])
            if frag in senator_lookup and len(frag) > 4:
                return senator_lookup[frag]
        return None

    for item in sponsor_success:
        item["senator_id"] = _find_senator_id(item["name"])

    top_sponsors = [
        {"name": s[0], "count": s[1], "senator_id": _find_senator_id(s[0])}
        for s in top_sponsors_raw
    ]

    # ── NEW: County Legislative Output ───────────────────────────────────────
    county_lookup: dict = {}
    try:
        for s in Senator.objects.select_related("county_fk").values(
            "senator_id", "name", "county_fk__name", "county_fk__slug"
        ):
            full  = s["name"].strip().lower()
            parts = full.split()
            cname = s["county_fk__name"]
            county_lookup[full] = cname
            for i in range(len(parts)):
                frag = " ".join(parts[i:])
                if len(frag) > 3 and frag not in county_lookup:
                    county_lookup[frag] = cname
    except Exception:
        pass

    def _find_county(sponsor_str: str):
        clean = re.sub(r"Sen\.\s*", "", sponsor_str)
        clean = re.sub(r"\s*\(.*?\)", "", clean).strip().lower()
        if clean in county_lookup:
            return county_lookup[clean]
        parts = clean.split()
        for i in range(len(parts)):
            frag = " ".join(parts[i:])
            if frag in county_lookup and len(frag) > 4:
                return county_lookup[frag]
        return None

    county_bills: dict = defaultdict(lambda: {"total": 0, "assented": 0, "active": 0, "lapsed": 0})
    for b in bills:
        counties_seen: set = set()
        for name in _parse_sponsors(b["sponsor"]):
            cty = _find_county(name)
            if cty and cty not in counties_seen:
                counties_seen.add(cty)
                county_bills[cty]["total"] += 1
                if b["status"] == "assented":
                    county_bills[cty]["assented"] += 1
                elif b["status"] in ("negatived", "withdrawn"):
                    county_bills[cty]["lapsed"] += 1
                else:
                    county_bills[cty]["active"] += 1
    for v in county_bills.values():
        v["assent_rate"] = round(v["assented"] / v["total"] * 100, 1) if v["total"] else 0
    county_list = sorted(county_bills.items(), key=lambda x: x[1]["total"], reverse=True)

    # ── NEW: Parliament-end risk ─────────────────────────────────────────────
    # 13th Parliament: Sept 2022 → est. Sept 2027.  Bills active for 2+ years face
    # lapsing risk — especially those still inside the Senate.
    def _risk(b):
        yr, st = b["year"], b["status"]
        if yr <= 2022 and st in ("at_2nd_reading", "at_cowt"):
            return "critical"   # 3+ years, not past first hurdles
        if yr <= 2022:
            return "high"       # old bill, at least cleared Senate
        if yr == 2023 and st in ("at_2nd_reading", "at_cowt"):
            return "medium"     # 2+ years, stuck in Senate
        return "low"            # recent or already at NA/mediation

    at_risk = sorted(
        [
            {**b, "risk": _risk(b)}
            for b in bills
            if b["year"] <= 2023 and b["status"] not in ("assented", "negatived", "withdrawn")
        ],
        key=lambda x: ({"critical": 0, "high": 1, "medium": 2, "low": 3}[x["risk"]], x["year"]),
    )
    risk_counts = {k: sum(1 for b in at_risk if b["risk"] == k) for k in ("critical", "high", "medium", "low")}

    # ── NEW: Stage bottleneck analysis ───────────────────────────────────────
    active_stages = ["at_2nd_reading", "at_cowt", "at_na", "in_mediation"]
    stage_bottleneck = []
    for stage in active_stages:
        sb = [b for b in bills if b["status"] == stage]
        n  = len(sb)
        if n == 0:
            avg_yr, early_n, early_pct = 0, 0, 0
        else:
            avg_yr    = round(sum(b["year"] for b in sb) / n, 1)
            early_n   = sum(1 for b in sb if b["year"] <= 2022)
            early_pct = round(early_n / n * 100)
        stage_bottleneck.append({
            "stage":      stage,
            "label":      pipeline_labels[stage],
            "count":      n,
            "avg_year":   avg_yr,
            "early_n":    early_n,
            "early_pct":  early_pct,
            "pct_total":  round(n / total * 100, 1),
        })

    # Transition yield — of bills that finished Senate (cleared OR failed), what % cleared?
    senate_resolved = cleared_senate + status_counts["negatived"] + status_counts["withdrawn"]
    senate_yield = round(cleared_senate / senate_resolved * 100, 1) if senate_resolved else 0
    # Of bills that cleared Senate, what % are now assented?
    na_yield = round(status_counts["assented"] / cleared_senate * 100, 1) if cleared_senate else 0
    transition_yields = {
        "senate_yield": senate_yield,
        "na_yield":     na_yield,
        "senate_resolved": senate_resolved,
    }

    # ── NEW: Party / coalition analysis ──────────────────────────────────────
    senator_party_map:     dict = {}
    senator_coalition_map: dict = {}
    senator_region_map:    dict = {}
    senator_image_map:     dict = {}
    no_longer_serving:     set  = set()

    def _senator_name_index(name: str, val, target: dict):
        full  = name.strip().lower()
        parts = full.split()
        target[full] = val
        for i in range(len(parts)):
            frag = " ".join(parts[i:])
            if len(frag) > 3 and frag not in target:
                target[frag] = val

    try:
        for s in Senator.objects.select_related("county_fk").values(
            "senator_id", "name", "party", "county_fk__region",
            "is_no_longer_serving",
        ):
            party     = s["party"] or ""
            coalition = _classify_coalition(party)
            region    = (s["county_fk__region"] or "other").replace("_", " ").title()
            _senator_name_index(s["name"], party,     senator_party_map)
            _senator_name_index(s["name"], coalition, senator_coalition_map)
            _senator_name_index(s["name"], region,    senator_region_map)
            if s["is_no_longer_serving"]:
                full = s["name"].strip().lower()
                for i in range(len(full.split())):
                    no_longer_serving.add(" ".join(full.split()[i:]))
    except Exception:
        pass

    try:
        for s in Senator.objects.only("name", "image", "image_url"):
            img = s.display_image_url
            if img:
                _senator_name_index(s.name, img, senator_image_map)
    except Exception:
        pass

    def _lookup(sponsor_str: str, mapping: dict):
        clean = re.sub(r"Sen\.\s*", "", sponsor_str)
        clean = re.sub(r"\s*\(.*?\)", "", clean).strip().lower()
        if clean in mapping:
            return mapping[clean]
        # Try every suffix fragment (≥ 4 chars — fixes off-by-one vs index builder)
        parts = clean.split()
        for i in range(len(parts)):
            frag = " ".join(parts[i:])
            if frag in mapping and len(frag) >= 4:
                return mapping[frag]
        # Last-resort: surname alone (≥ 3 chars)
        if parts and len(parts[-1]) >= 3 and parts[-1] in mapping:
            return mapping[parts[-1]]
        # Institutional roles → resolve to the actual senator's data
        lower = sponsor_str.lower()
        for role_pattern, senator_frag in _INSTITUTIONAL_SPONSORS.items():
            if role_pattern in lower:
                if senator_frag in mapping:
                    return mapping[senator_frag]
                for i in range(len(senator_frag.split())):
                    f = " ".join(senator_frag.split()[i:])
                    if f in mapping and len(f) >= 4:
                        return mapping[f]
        return None

    # Aggregate bills by coalition
    coalition_agg: dict = defaultdict(lambda: {"total": 0, "assented": 0, "active": 0, "lapsed": 0})
    for b in bills:
        coa = _lookup(b["sponsor"], senator_coalition_map) or "Multiple/Other"
        coalition_agg[coa]["total"] += 1
        if b["status"] == "assented":
            coalition_agg[coa]["assented"] += 1
        elif b["status"] in ("negatived", "withdrawn"):
            coalition_agg[coa]["lapsed"] += 1
        else:
            coalition_agg[coa]["active"] += 1
    for v in coalition_agg.values():
        v["assent_rate"] = round(v["assented"] / v["total"] * 100, 1) if v["total"] else 0
    coalition_list = sorted(coalition_agg.items(), key=lambda x: x[1]["total"], reverse=True)

    # ── NEW: Regional analysis ────────────────────────────────────────────────
    region_agg: dict = defaultdict(lambda: {"total": 0, "assented": 0, "active": 0, "lapsed": 0})
    for b in bills:
        rgn = _lookup(b["sponsor"], senator_region_map) or "National / Multiple"
        region_agg[rgn]["total"] += 1
        if b["status"] == "assented":
            region_agg[rgn]["assented"] += 1
        elif b["status"] in ("negatived", "withdrawn"):
            region_agg[rgn]["lapsed"] += 1
        else:
            region_agg[rgn]["active"] += 1
    for v in region_agg.values():
        v["assent_rate"] = round(v["assented"] / v["total"] * 100, 1) if v["total"] else 0
    region_list = sorted(region_agg.items(), key=lambda x: x[1]["total"], reverse=True)

    # ── NEW: Time-to-law analysis ─────────────────────────────────────────────
    timed_bills = [b for b in bills if b["status"] == "assented" and b.get("assent_year")]
    for b in timed_bills:
        b["years_to_assent"]   = b["assent_year"] - b["year"]
        b["sponsor_party"]     = _lookup(b["sponsor"], senator_party_map)     or ""
        b["sponsor_coalition"] = _lookup(b["sponsor"], senator_coalition_map) or ""
        b["sponsor_image"]     = _lookup(b["sponsor"], senator_image_map)     or ""
    if timed_bills:
        avg_ttl   = round(sum(b["years_to_assent"] for b in timed_bills) / len(timed_bills), 1)
        fastest   = min(timed_bills, key=lambda x: x["years_to_assent"])
        slowest   = max(timed_bills, key=lambda x: x["years_to_assent"])
        ttl_dist  = sorted(Counter(b["years_to_assent"] for b in timed_bills).items())
        by_assent_year = {}
        for b in timed_bills:
            ay = str(b["assent_year"])
            by_assent_year.setdefault(ay, []).append(b["years_to_assent"])
        assent_yr_labels = sorted(by_assent_year)
        assent_yr_avgs   = [round(sum(by_assent_year[y]) / len(by_assent_year[y]), 1) for y in assent_yr_labels]
        assent_yr_counts = [len(by_assent_year[y]) for y in assent_yr_labels]
    else:
        avg_ttl = fastest = slowest = None
        ttl_dist = assent_yr_labels = assent_yr_avgs = assent_yr_counts = []

    time_to_law = {
        "avg_years":    avg_ttl,
        "fastest_title": fastest["title"]  if fastest else "",
        "fastest_years": fastest["years_to_assent"] if fastest else 0,
        "slowest_title": slowest["title"]  if slowest else "",
        "slowest_years": slowest["years_to_assent"] if slowest else 0,
        "dist_labels":  [f"{y} yr{'s' if y!=1 else ''}" for y, _ in ttl_dist],
        "dist_counts":  [c for _, c in ttl_dist],
    }

    # ── NEW: Senator status + party/image for stalled bills ─────────────────
    for b in stalled:
        raw_sponsor = b["sponsor"].lower()
        b["sponsor_left"]     = any(
            frag in no_longer_serving
            for frag in raw_sponsor.split()
            if len(frag) > 3
        )
        b["sponsor_party"]     = _lookup(b["sponsor"], senator_party_map)     or ""
        b["sponsor_coalition"] = _lookup(b["sponsor"], senator_coalition_map) or ""
        b["sponsor_image"]     = _lookup(b["sponsor"], senator_image_map)     or ""

    # ── NEW: Policy domain clustering ────────────────────────────────────────
    _DOMAIN_RULES = [
        ("Finance/Budget", ["division of revenue", "county allocation", "pfm", "public finance management",
                            "equalization fund", "appropriation", "public audit", "county revenue",
                            "national rating", "facilities improvement fund"]),
        ("Health",         ["health", "medical", "hospital", "cancer", "maternal", "newborn", "autism",
                            "reproductive technology", "pharmacy", "disease", "hiv"]),
        ("Agriculture",    ["agri", "livestock", "cotton", "coffee", "tea", "mung", "seed", "sugar",
                            "rice", "nuts and oil", "food and feed", "crop", "veterinary"]),
        ("Elections",      ["election", "iebc", "political part", "electoral"]),
        ("Environment",    ["environment", "climate change", "energy", "water", "wildlife",
                            "meteorology", "waste", "electronic equipment", "mining"]),
        ("Education",      ["education", "school", "learning", "learner", "vocational", "training",
                            "early childhood"]),
        ("Housing/Infra",  ["housing", "road", "construction", "nca", "fire and rescue",
                            "technopolis", "konza"]),
        ("Trade/Industry", ["startup", "local content", "cooperat", "creative economy",
                            "business laws", "public procurement", "motorcycle", "national transport"]),
        ("Labour",         ["employment", "labour", "migration", "internship"]),
        ("Legal/Rights",   ["conflict of interest", "narcotic", "gambling", "tobacco",
                            "disability", "sign language", "succession", "assisted reproductive",
                            "heritage", "prevention of livestock theft"]),
        ("Social",         ["social protection", "street vendor", "community health", "child",
                            "culture", "sport", "public holiday", "library", "fundraising",
                            "persons with"]),
        ("Governance",     ["county government", "county assembly", "public service", "oversight",
                            "intergovernmental", "parliamentary", "parliament", "statutory instrument",
                            "civic education", "county hall", "county statistics", "county ward",
                            "county boundaries", "county laws", "bicameral", "houses of parliament"]),
    ]

    def _get_domain(title: str) -> str:
        t = title.lower()
        for dom, keywords in _DOMAIN_RULES:
            if any(k in t for k in keywords):
                return dom
        return "Other"

    for b in bills:
        b["domain"] = _get_domain(b["title"])

    domain_map: dict = defaultdict(lambda: {"total": 0, "assented": 0, "active": 0, "lapsed": 0})
    for b in bills:
        d = b["domain"]
        domain_map[d]["total"] += 1
        if b["status"] == "assented":
            domain_map[d]["assented"] += 1
        elif b["status"] in ("negatived", "withdrawn"):
            domain_map[d]["lapsed"] += 1
        else:
            domain_map[d]["active"] += 1
    for v in domain_map.values():
        v["assent_rate"] = round(v["assented"] / v["total"] * 100, 1) if v["total"] else 0
    domain_list = sorted(domain_map.items(), key=lambda x: x[1]["total"], reverse=True)

    # ── NEW: Co-sponsorship effect ────────────────────────────────────────────
    co_bills   = [b for b in bills if "(Co-Sponsor)" in b["sponsor"]]
    solo_bills = [b for b in bills if "(Co-Sponsor)" not in b["sponsor"]]
    cosponsor_stats = {
        "co":   _gstat(co_bills),
        "solo": _gstat(solo_bills),
    }

    # ── NEW: Amendment rate by bill origin ────────────────────────────────────
    sb_known  = [b for b in senate_bills if b["senate_amended"] is not None]
    nab_known = [b for b in na_bills     if b["senate_amended"] is not None]
    sb_am_pct  = round(sum(1 for b in sb_known  if b["senate_amended"]) / len(sb_known)  * 100, 1) if sb_known  else 0
    nab_am_pct = round(sum(1 for b in nab_known if b["senate_amended"]) / len(nab_known) * 100, 1) if nab_known else 0
    amendment_by_origin = {
        "sb_amended_pct":  sb_am_pct,
        "nab_amended_pct": nab_am_pct,
        "sb_total":        len(sb_known),
        "nab_total":       len(nab_known),
        "sb_amended":      sum(1 for b in sb_known  if b["senate_amended"]),
        "nab_amended":     sum(1 for b in nab_known if b["senate_amended"]),
        "insight": (
            "The Senate amends a higher proportion of National Assembly bills than its own — acting as a revising chamber."
            if nab_am_pct > sb_am_pct else
            "The Senate revises its own bills at a similar or higher rate than it revises National Assembly bills."
        ),
    }

    # ── NEW: Mediation deep-dive ──────────────────────────────────────────────
    mediation_bills = sorted(
        [b for b in bills if b["status"] == "in_mediation"],
        key=lambda x: x["year"],
    )
    for b in mediation_bills:
        age = 2026 - b["year"]
        b["years_pending"] = age
        b["med_risk"] = "critical" if age >= 3 else "high" if age >= 2 else "medium"

    # ── Key insights ──────────────────────────────────────────────────────────
    most_active_comm  = committee_list[0]
    best_assent_comm  = max(comm_map.items(), key=lambda x: x[1]["assent_rate"])
    top_sponsor_name  = top_sponsors[0]["name"] if top_sponsors else "—"
    top_sponsor_count = top_sponsors[0]["count"] if top_sponsors else 0
    pct_senate_origin = round(len(senate_bills) / total * 100)

    insights = [
        {"icon": "scale",       "value": f"{round(status_counts['assented']/total*100,1)}%",
         "label": "of bills become law",
         "sub":   f"{status_counts['assented']} of {total} bills assented", "color": "emerald"},
        {"icon": "folder-open", "value": most_active_comm[0],
         "label": "most active committee",
         "sub":   f"{most_active_comm[1]['total']} bills handled", "color": "blue"},
        {"icon": "trophy",      "value": best_assent_comm[0],
         "label": "highest assent rate",
         "sub":   f"{best_assent_comm[1]['assent_rate']}% of its bills signed", "color": "amber"},
        {"icon": "user-check",  "value": top_sponsor_name,
         "label": "top individual sponsor",
         "sub":   f"{top_sponsor_count} bills introduced", "color": "red"},
        {"icon": "landmark",    "value": f"{pct_senate_origin}%",
         "label": "Senate-originated",
         "sub":   f"{len(senate_bills)} Senate vs {len(na_bills)} NA bills", "color": "violet"},
        {"icon": "clock",       "value": str(len(stalled)),
         "label": "bills stalled 2+ years",
         "sub":   "Introduced ≤ 2023, still in Senate", "color": "orange"},
    ]

    # ── Chart.js payload ──────────────────────────────────────────────────────
    chart_data = {
        "pipeline": {
            "labels": [pipeline_labels[k] for k in pipeline_order],
            "values": [status_counts.get(k, 0) for k in pipeline_order],
        },
        "years": {
            "labels":   [str(y) for y in years_sorted],
            "assented": [year_map[y]["assented"] for y in years_sorted],
            "active":   [year_map[y]["active"]   for y in years_sorted],
            "lapsed":   [year_map[y]["lapsed"]   for y in years_sorted],
        },
        "committees": {
            "labels":       [c[0] for c in committee_list],
            "assented":     [c[1]["assented"] for c in committee_list],
            "active":       [c[1]["active"]   for c in committee_list],
            "lapsed":       [c[1]["lapsed"]   for c in committee_list],
            "assent_rates": [c[1]["assent_rate"] for c in committee_list],
        },
        "origin": {
            "senate_total":    len(senate_bills),
            "na_total":        len(na_bills),
            "senate_assented": s_assented,
            "na_assented":     n_assented,
        },
        "sponsors": {
            "labels": [s["name"] for s in top_sponsors],
            "values": [s["count"] for s in top_sponsors],
        },
        "cohort": {
            "labels":      cohort_labels,
            "assented":    [cohort[y]["assented"] for y in cohort_labels],
            "active":      [cohort[y]["active"]   for y in cohort_labels],
            "lapsed":      [cohort[y]["lapsed"]   for y in cohort_labels],
            "assent_rate": [cohort[y]["assent_rate"] for y in cohort_labels],
        },
        "na_dynamics": {
            "labels": ["Assented into Law", "Pending at Nat. Assembly",
                       "In Mediation", "Presidential Memorandum"],
            "values": [na_dynamics["assented"], na_dynamics["pending_na"],
                       na_dynamics["in_mediation"], na_dynamics["presidential_memo"]],
        },
        "amendment": {
            "amended":             amendment_stats["amended"],
            "clean":               amendment_stats["clean"],
            "amended_assent_rate": amendment_stats["amended_assent_rate"],
            "clean_assent_rate":   amendment_stats["clean_assent_rate"],
        },
        "gender": {
            "labels":   ["Women Senators", "Men Senators", "Senate Leadership"],
            "totals":   [gender_stats["women"]["total"],       gender_stats["men"]["total"],       gender_stats["leadership"]["total"]],
            "assented": [gender_stats["women"]["assented"],    gender_stats["men"]["assented"],    gender_stats["leadership"]["assented"]],
            "rates":    [gender_stats["women"]["assent_rate"], gender_stats["men"]["assent_rate"], gender_stats["leadership"]["assent_rate"]],
        },
        "sponsor_success": {
            "labels":   [s["name"].replace("Sen. ", "") for s in sponsor_success[:12]],
            "total":    [s["total"]    for s in sponsor_success[:12]],
            "assented": [s["assented"] for s in sponsor_success[:12]],
        },
        "county": {
            "labels":       [c[0] for c in county_list[:20]],
            "total":        [c[1]["total"]       for c in county_list[:20]],
            "assented":     [c[1]["assented"]    for c in county_list[:20]],
            "assent_rates": [c[1]["assent_rate"] for c in county_list[:20]],
        },
        "bottleneck": {
            "labels":      [s["label"]     for s in stage_bottleneck],
            "counts":      [s["count"]     for s in stage_bottleneck],
            "avg_years":   [s["avg_year"]  for s in stage_bottleneck],
            "early_pcts":  [s["early_pct"] for s in stage_bottleneck],
        },
        "domain": {
            "labels":       [d[0] for d in domain_list],
            "total":        [d[1]["total"]       for d in domain_list],
            "assented":     [d[1]["assented"]    for d in domain_list],
            "active":       [d[1]["active"]      for d in domain_list],
            "lapsed":       [d[1]["lapsed"]      for d in domain_list],
            "assent_rates": [d[1]["assent_rate"] for d in domain_list],
        },
        "coalition": {
            "labels":       [c[0] for c in coalition_list],
            "total":        [c[1]["total"]       for c in coalition_list],
            "assented":     [c[1]["assented"]    for c in coalition_list],
            "active":       [c[1]["active"]      for c in coalition_list],
            "lapsed":       [c[1]["lapsed"]      for c in coalition_list],
            "assent_rates": [c[1]["assent_rate"] for c in coalition_list],
        },
        "region": {
            "labels":       [r[0] for r in region_list],
            "total":        [r[1]["total"]       for r in region_list],
            "assented":     [r[1]["assented"]    for r in region_list],
            "assent_rates": [r[1]["assent_rate"] for r in region_list],
        },
        "ttl": {
            "dist_labels":    time_to_law["dist_labels"],
            "dist_counts":    time_to_law["dist_counts"],
            "assent_yr_labels": assent_yr_labels,
            "assent_yr_avgs":   assent_yr_avgs,
            "assent_yr_counts": assent_yr_counts,
        },
    }

    # ── Pre-process for templates (avoid variable dict lookups) ──────────────
    cohort_rows = [
        {"year": y, **cohort[y]}
        for y in cohort_labels
    ]

    heatmap_rows = [
        {
            "committee": comm,
            "cells": [heatmap_data[comm].get(y, 0) for y in heatmap_years],
            "total": sum(heatmap_data[comm].get(y, 0) for y in heatmap_years),
        }
        for comm in heatmap_comms
    ]

    toc_items = [
        ("1 · Funnel",          "s-funnel"),
        ("2 · Year Trend",      "s-yoy"),
        ("3 · Origin",          "s-origin"),
        ("4 · Committees",      "s-committees"),
        ("5 · Pipeline",        "s-pipeline"),
        ("6 · Top Sponsors",    "s-sponsors"),
        ("7 · Cohorts",         "s-cohort"),
        ("8 · NA Dynamics",     "s-na"),
        ("9 · Amendments",      "s-amendments"),
        ("10 · Success Rate",   "s-success"),
        ("11 · Women Senators", "s-gender"),
        ("12 · Stalled Bills",  "s-stalled"),
        ("13 · Heatmap",        "s-heatmap"),
        ("14 · County Output",    "s-county"),
        ("15 · Parliament Risk",  "s-risk"),
        ("16 · Bottlenecks",      "s-bottleneck"),
        ("17 · Policy Domains",    "s-domains"),
        ("18 · Co-Sponsorship",    "s-cosponsor"),
        ("19 · Origin × Amendment","s-amend-origin"),
        ("20 · Mediation Dive",    "s-mediation"),
        ("21 · Coalition Output",  "s-coalition"),
        ("22 · Region Output",     "s-region"),
        ("23 · Time to Law",       "s-ttl"),
    ]

    return render(request, "scorecard/bills_analytics.html", {
        "stats":                stats,
        "funnel":               funnel,
        "committee_list":       committee_list,
        "top_sponsors":         top_sponsors,
        "sponsor_success":      sponsor_success,
        "insights":             insights,
        "as_at_date":           _AS_AT_DATE,
        "source_url":           _SOURCE_URL,
        "total":                total,
        "na_dynamics":          na_dynamics,
        "amendment_stats":      amendment_stats,
        "gender_stats":         gender_stats,
        "stalled":              stalled,
        "heatmap_rows":         heatmap_rows,
        "heatmap_years":        heatmap_years,
        "heatmap_max":          heatmap_max,
        "cohort_rows":          cohort_rows,
        "toc_items":            toc_items,
        "county_list":          county_list,
        "at_risk":              at_risk,
        "risk_counts":          risk_counts,
        "stage_bottleneck":     stage_bottleneck,
        "transition_yields":    transition_yields,
        "domain_list":          domain_list,
        "cosponsor_stats":      cosponsor_stats,
        "amendment_by_origin":  amendment_by_origin,
        "mediation_bills":      mediation_bills,
        "coalition_list":       coalition_list,
        "region_list":          region_list,
        "time_to_law":          time_to_law,
        "timed_bills":          sorted(timed_bills, key=lambda x: x["years_to_assent"]),
        "chart_data":           chart_data,
    })
