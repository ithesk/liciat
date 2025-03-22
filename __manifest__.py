{
    'name': 'Gestión de Licitaciones',
    'version': '1.0',
    'category': 'Sales/Licitaciones',
    'summary': 'Módulo para gestionar licitaciones y propuestas',
    'description': """
        Gestión de Licitaciones
        ======================
        Este módulo permite:
        * Crear y gestionar licitaciones
        * Generar propuestas para licitaciones
        * Seguimiento de procesos de licitación
        * Reportes detallados
    """,
    'author': 'Axedev',
    'website': 'https://www.ithesk.com',
    'depends': ['base', 'mail', 'product', 'sale', 'account'],
    'data': [
         'security/tender_security.xml',
         'security/ir.model.access.csv',
          'views/tender_views.xml',
          'views/proposal_views.xml',
          'views/menu_views.xml',
          'views/government_document_views.xml',
          'views/government_bidding_data_views.xml',
          'data/tender_sequences.xml',
          'views/supplier_quote_views.xml',
        # 'reports/tender_report.xml',
        # 'reports/proposal_report.xml',
        # 'wizard/generate_proposal_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'tender_management/static/src/js/tender_frontend.js',
            # 'tender_management/static/src/css/tender_style.css',
        ],
    },
    'demo': [],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}