# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import json
import base64
import xmltodict

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = "pos.session"

    secuencia_boleta = fields.Many2one(
            'ir.sequence',
            string='Documents Type',
        )
    secuencia_boleta_exenta = fields.Many2one(
            'ir.sequence',
            string='Documents Type',
        )
    start_number = fields.Integer(
            string='Folio Inicio',
        )
    start_number_exentas = fields.Integer(
            string='Folio Inicio Exentas',
        )
    numero_ordenes = fields.Integer(
            string="Número de órdenes",
            default=0,
        )
    numero_ordenes_exentas = fields.Integer(
            string="Número de órdenes exentas",
            default=0,
        )
    caf_files = fields.Char(
            invisible=True,
        )
    caf_files_exentas = fields.Char(
            invisible=True,
        )

    @api.model
    def create(self, values):
        pos_config = values.get('config_id') or self.env.context.get('default_config_id')
        config_id = self.env['pos.config'].browse(pos_config)
        if not config_id:
            raise UserError(_("You should assign a Point of Sale to your session."))
        if config_id.secuencia_boleta:
            sequence = config_id.secuencia_boleta
            start_number = sequence.number_next_actual
            sequence.update_next_by_caf()
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual
            values.update({
                'start_number': start_number,
                'secuencia_boleta': config_id.secuencia_boleta.id,
                'caf_files': self.get_caf_string(sequence),
            })
        if config_id.secuencia_boleta_exenta:
            sequence = config_id.secuencia_boleta_exenta
            start_number = sequence.number_next_actual
            sequence.update_next_by_caf()
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual
            values.update({
                'start_number_exentas': start_number,
                'secuencia_boleta_exenta': config_id.secuencia_boleta_exenta.id,
                'caf_files_exentas': self.get_caf_string(sequence),
            })
        return super(PosSession, self).create(values)

    @api.model
    def get_caf_string(self, sequence=None):
        if not sequence:
            sequence = self.secuencia_boleta
            if not sequence:
                return
        folio = sequence.number_next_actual
        caffiles = sequence.get_caf_files()
        if not caffiles:
            return
        caffs = []
        for caffile in caffiles:
            caffs += [caffile.decode_caf()]
        if caffs:
            return json.dumps(caffs, ensure_ascii=False)
        msg = '''El folio de este documento: {} está fuera de rango \
del CAF vigente (desde {} hasta {}). Solicite un nuevo CAF en el sitio \
www.sii.cl'''.format(folio, folio_inicial, folio_final)
        raise UserError(_(msg))
