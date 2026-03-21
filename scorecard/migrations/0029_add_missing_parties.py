from django.db import migrations

def add_parties(apps, schema_editor):
    Party = apps.get_model('scorecard', 'Party')
    
    parties_to_add = [
        {
            'name': 'United Progressive Alliance',
            'logo': 'parties/upa_logo.png',
            'history': 'The United Progressive Alliance (UPA) is a Kenyan political party with a bar of soap symbol and "Safisha Kenya" slogan.'
        },
        {
            'name': 'Kenya Africa National Union',
            'logo': 'parties/kanu_logo.png',
            'history': 'Kenya Africa National Union (KANU) is one of the oldest political parties in Kenya, symbolized by a rooster.'
        },
        {
            'name': 'Amani National Congress',
            'logo': 'parties/anc_logo.png',
            'history': 'Amani National Congress (ANC) is a political party in Kenya led by Musalia Mudavadi, symbolized by a lamp.'
        },
        {
            'name': 'Kenya Union Party',
            'logo': 'parties/favicon.png',
            'history': 'Kenya Union Party (KUP) is a political party in Kenya.'
        },
        {
            'name': 'Democratic Action Party of Kenya',
            'logo': 'parties/favicon.png',
            'history': 'Democratic Action Party of Kenya (DAP-K) is a political party in Kenya.'
        },
        # Variants found in Mombasa and other counties (typos/abbreviations)
        {
            'name': 'Orange Demographic County (ODM)',
            'logo': 'parties/lumina-enhanced-1773061990814_1.png', # Map to ODM logo
            'history': 'Variant/Typo for Orange Democratic Movement (ODM).'
        },
        {
            'name': 'Orange Demographic Movement',
            'logo': 'parties/lumina-enhanced-1773061990814_1.png', # Map to ODM logo
            'history': 'Variant/Typo for Orange Democratic Movement (ODM).'
        },
        {
            'name': 'Wiper Democratic Movement',
            'logo': 'parties/wiperlogo.png', # Map to Wiper logo
            'history': 'Variant for Wiper Democratic Movement - Kenya.'
        },
        {
            'name': 'Wiper Democratic Movement party',
            'logo': 'parties/wiperlogo.png', # Map to Wiper logo
            'history': 'Variant for Wiper Democratic Movement - Kenya.'
        },
        {
            'name': 'INDEPENDENT',
            'logo': 'parties/favicon.png', # Generic placeholder
            'history': 'Independent candidates not affiliated with any political party.'
        },
    ]
    
    for party_data in parties_to_add:
        # Use filter and exists to avoid potential sequence/get_or_create issues on some DBs
        if not Party.objects.filter(name=party_data['name']).exists():
            Party.objects.create(
                name=party_data['name'],
                logo=party_data['logo'],
                history=party_data['history']
            )

def remove_parties(apps, schema_editor):
    Party = apps.get_model('scorecard', 'Party')
    names = [
        'United Progressive Alliance',
        'Kenya Africa National Union',
        'Amani National Congress',
        'Kenya Union Party',
        'Democratic Action Party of Kenya',
        'Orange Demographic County (ODM)',
        'Orange Demographic Movement',
        'Wiper Democratic Movement',
        'Wiper Democratic Movement party',
        'INDEPENDENT'
    ]
    Party.objects.filter(name__in=names).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('scorecard', '0028_add_is_no_longer_serving_to_senator'),
    ]

    operations = [
        migrations.RunPython(add_parties, remove_parties),
    ]
