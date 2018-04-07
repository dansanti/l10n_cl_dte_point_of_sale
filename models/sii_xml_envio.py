# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.translate import _

class SIIXMLEnvio(models.Model):
    _inherit = 'sii.xml.envio'

    order_ids = fields.One2many(
            'pos.order',
            'sii_xml_request',
            string="Ordenes POS",
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
