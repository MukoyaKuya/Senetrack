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
    ]
    
    for party_data in parties_to_add:
        Party.objects.get_or_create(
            name=party_data['name'],
            defaults={
                'logo': party_data['logo'],
                'history': party_data['history']
            }
        )

def remove_parties(apps, schema_editor):
    Party = apps.get_model('scorecard', 'Party')
    names = [
        'United Progressive Alliance',
        'Kenya Africa National Union',
        'Amani National Congress',
        'Kenya Union Party',
        'Democratic Action Party of Kenya'
    ]
    Party.objects.filter(name__in=names).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('scorecard', '0028_add_is_no_longer_serving_to_senator'),
    ]

    operations = [
        migrations.RunPython(add_parties, remove_parties),
    ]
