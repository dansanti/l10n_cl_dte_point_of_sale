# -*- coding: utf-8 -*-
{
    "name": """Chile - Web Services de Documentos Tributarios Electrónicos Para Punto de Ventas\
    """,
    'version': '9.0.5.4.1',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Daniel Santibáñez Polanco',
    'website': 'https://globalresponse.cl',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Chile: API and GUI to access Electronic Invoicing webservices for Point of Sale.
""",
    'depends': [
        'l10n_cl_counties',
        'l10n_cl_invoice',
        'l10n_cl_dte_caf',
        'l10n_cl_dte',
        'user_signature_key',
        'account',
        'point_of_sale',
        'report',
        'l10n_cl_libro_compra_venta',
        'website',
        ],
    'external_dependencies': {
        'python': [
            'xmltodict',
            'dicttoxml',
            'pdf417gen',# v0.6 <=
            'M2Crypto',
            'base64',
            'hashlib',
            'cchardet',
            'suds',
            'urllib3',
            'SOAPpy',
            'signxml',
            'ast'
        ]
    },
    'data': [
        'wizard/notas.xml',
        'views/pos_dte.xml',
        'views/pos_config.xml',
        'views/pos_session.xml',
        'views/point_of_sale.xml',
        'views/bo_receipt.xml',
        'views/website_layout.xml',
        'wizard/masive_send_dte.xml',
#        'data/sequence.xml',
#        'data/cron.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/layout.xml',
        'static/src/xml/client.xml',
        'static/src/xml/payment.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
