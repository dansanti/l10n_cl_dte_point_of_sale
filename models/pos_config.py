# -*- coding: utf-8 -*-

from openerp import fields, models, api, _
from openerp.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_left_numbers(self):
        for rec in self:
            if rec.secuencia_boleta:
                rec.left_number = rec.secuencia_boleta.sequence_id.get_qty_available()
            if rec.secuencia_boleta_exenta:
                rec.left_number_exenta = rec.secuencia_boleta_exenta.sequence_id.get_qty_available()

    secuencia_boleta = fields.Many2one(
            'account.journal.sii_document_class',
            string='Secuencia Boleta',
        )
    secuencia_boleta_exenta = fields.Many2one(
            'account.journal.sii_document_class',
            string='Secuencia Boleta Exenta',
        )
    ticket = fields.Boolean(
            string="¿Facturas en Formato Ticket?",
            default=False,
        )
    next_number = fields.Integer(
            related="secuencia_boleta.sequence_id.number_next_actual",
            string="Next Number",
        )
    next_number_exenta = fields.Integer(
            related="secuencia_boleta_exenta.sequence_id.number_next_actual",
            string="Next Number Exenta",
        )
    left_number = fields.Integer(
            compute="get_left_numbers",
            string="Folios restantes Boletas",
        )
    left_number_exenta = fields.Integer(
            compute="get_left_numbers",
            string="Folios restantes Boletas Exentas",
        )
    marcar = fields.Selection(
        [
            ('boleta', 'Boletas'),
            ('factura', 'Facturas'),
            ('boleta_exenta', 'Boletas Exentas'),
        ],
        string="Marcar por defecto",
        default='boleta',
    )
