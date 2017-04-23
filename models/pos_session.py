# -*- coding: utf-8 -*-

from openerp import fields, models, api, _, SUPERUSER_ID
from openerp.exceptions import UserError
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
        'Documents Type',)

    start_number = fields.Integer(
        string='Folio comienzo',
    )
    caf_file = fields.Char(
        invisible=True)
    numero_ordenes = fields.Integer(
        string="Número de ordenes",
        default=0)

    def create(self, cr, uid, values, context=None):
        context = dict(context or {})
        config_id = values.get('config_id', False) or context.get('default_config_id', False)
        jobj = self.pool.get('pos.config')
        pos_config = jobj.browse(cr, uid, config_id, context=context)
        context.update({'company_id': pos_config.company_id.id})
        is_pos_user = self.pool['res.users'].has_group(cr, uid, 'point_of_sale.group_pos_user')
        if pos_config.journal_document_class_id:
            sequence = pos_config.journal_document_class_id.sequence_id
            start_number = sequence.number_next_actual
            sequence.update_next_by_caf()
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual -1
            values.update({
                'start_number': start_number,
                'journal_document_class_id': pos_config.journal_document_class_id.id,
                'caf_file': self.get_caf_string(cr, uid, sequence, context=context),
            })
        return super(PosSession, self).create(cr, is_pos_user and SUPERUSER_ID or uid, values, context=context)

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
