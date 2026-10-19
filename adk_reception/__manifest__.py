# -*- coding: utf-8 -*-
{
    'name': 'ADK Réception',
    'version': '18.0.1.0.0',
    'category': 'Operations/Reception',
    'summary': "Réception & sécurité : visiteurs avec photo et badge, badgeage employés, biens et marchandises, liste d'évacuation, tableau de bord temps réel — gratuit",
    'description': """
ADK Réception
=============
Module de gestion de la réception pour Odoo 18.

* Visiteurs : check-in / check-out horodatés, photo webcam, pièce d'identité, badge imprimable
* Fiches visiteurs et liste noire (accès refusé)
* Hôte notifié automatiquement à l'arrivée de son visiteur
* Badgeage des employés (QR code, NFC, matricule) avec retards et heures supplémentaires
* Suivi du matériel entrant/sortant
* Registre des biens et marchandises (colis, livraisons, retours)
* Tableau de bord temps réel et liste de sécurité des présents (évacuation)
* Exports PDF, Excel et CSV
""",
    'author': 'Kambeu Henang Ange Duval',
    'website': '',
    'support': 'duvalkambeu61@gmail.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'web',
    ],
    'data': [
        # 1. Sécurité
        'security/security.xml',
        'security/ir.model.access.csv',

        # 2. Séquences et données
        'data/ir_sequence_data.xml',
        'data/reception_data.xml',
        'data/cron_data.xml',

        # 3. Rapports
        'report/report_visit_badge_template.xml',
        'report/report_present_list_template.xml',
        'report/report_export_document.xml',
        'report/report_actions.xml',

        # 4. Vues métiers
        'views/reception_visitor_views.xml',
        'views/reception_visit_views.xml',
        'views/reception_employee_movement_views.xml',
        'views/reception_goods_views.xml',
        'views/reception_motif_views.xml',
        'views/reception_catalog_views.xml',
        'views/reception_config_views.xml',
        'views/reception_dashboard_views.xml',

        # 5. Wizards
        'wizard/reception_export_wizard_view.xml',

        # 6. Menus (chargé en dernier)
        'views/reception_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'adk_reception/static/src/scss/reception_dashboard.scss',
            'adk_reception/static/src/js/webcam_field.js',
            'adk_reception/static/src/xml/webcam_field.xml',
            'adk_reception/static/src/js/reception_dashboard.js',
            'adk_reception/static/src/xml/reception_dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.reception.png'],
}
