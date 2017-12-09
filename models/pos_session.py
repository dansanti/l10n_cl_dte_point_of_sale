# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import json
import base64
import xmltodict

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = "pos.session"

    journal_document_class_id = fields.Many2one(
            'account.journal.sii_document_class',
            string='Documents Type',
        )
    start_number = fields.Integer(
            string='Folio comienzo',
        )
    caf_file = fields.Char(
            invisible=True,
        )
    numero_ordenes = fields.Integer(
            string="Número de ordenes",
            default=0,
        )

    @api.model
    def create(self, values):
        pos_config = values.get('config_id') or self.env.context.get('default_config_id')
        config_id = self.browse(pos_config)
        if not config_id:
            raise UserError(_("You should assign a Point of Sale to your session."))
        if config_id.journal_document_class_id:
            sequence = config_id.journal_document_class_id.sequence_id
            start_number = sequence.number_next_actual
            sequence.update_next_by_caf()
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual
            values.update({
                'start_number': start_number,
                'journal_document_class_id': config_id.journal_document_class_id.id,
                'caf_file': self.get_caf_string(sequence),
            })
        return super(PosSession, self).create(values)

    @api.model
    def get_caf_string(self, sequence=None):
        if not sequence:
            sequence = self.journal_document_class_id.sequence_id
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
