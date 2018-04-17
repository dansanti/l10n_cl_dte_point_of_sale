# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_left_numbers(self):
        for rec in self:
            if rec.secuencia_boleta:
                rec.left_number = rec.secuencia_boleta.get_qty_available()
            if rec.secuencia_boleta_exenta:
                rec.left_number_exenta = rec.secuencia_boleta_exenta.get_qty_available()

    secuencia_boleta = fields.Many2one(
            'ir.sequence',
            string='Secuencia Boleta',
        )
    secuencia_boleta_exenta = fields.Many2one(
            'ir.sequence',
            string='Secuencia Boleta Exenta',
        )
    ticket = fields.Boolean(
            string="¿Facturas en Formato Ticket?",
            default=False,
        )
    next_number = fields.Integer(
            related="secuencia_boleta.number_next_actual",
            string="Next Number",
        )
    next_number_exenta = fields.Integer(
            related="secuencia_boleta_exenta.number_next_actual",
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
    )

    @api.one
    @api.constrains('marcar','secuencia_boleta', 'secuencia_boleta_exenta', 'iface_invoicing')
    def _check_document_type(self):
        if self.marcar == 'boleta' and not self.secuencia_boleta:
            raise ValidationError("Al marcar por defecto Boletas, "
                                  "debe seleccionar la Secuencia de Boletas, "
                                  "por favor verifique su configuracion")
        elif self.marcar == 'boleta_exenta' and not self.secuencia_boleta_exenta:
            raise ValidationError("Al marcar por defecto Boletas Exentas, "
                                  "debe seleccionar la Secuencia de Boletas Exentas, "
                                  "por favor verifique su configuracion")
        elif self.marcar == 'factura' and not self.iface_invoicing:
            raise ValidationError("Al marcar por defecto Facturas, "
                                  "debe activar el check de Facturacion, "
                                  "por favor verifique su configuracion")
