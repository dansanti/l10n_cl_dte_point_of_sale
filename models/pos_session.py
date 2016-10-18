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
    caf_file = fields.Char( invisible=True)

    def create(self, cr, uid, values, context=None):
        context = dict(context or {})
        config_id = values.get('config_id', False) or context.get('default_config_id', False)
        jobj = self.pool.get('pos.config')
        pos_config = jobj.browse(cr, uid, config_id, context=context)
        context.update({'company_id': pos_config.company_id.id})
        is_pos_user = self.pool['res.users'].has_group(cr, uid, 'point_of_sale.group_pos_user')
        if pos_config.journal_document_class_id:
            sequence = pos_config.journal_document_class_id.sequence_id
            values.update({
                'start_number': sequence.number_next_actual,
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
        caffiles = sequence.dte_caf_ids
        if not caffiles:
            return
        for caffile in caffiles:
            post = base64.b64decode(caffile.caf_file)
            post = xmltodict.parse(post.replace(
                '<?xml version="1.0"?>','',1))
            folio_inicial = post['AUTORIZACION']['CAF']['DA']['RNG']['D']
            folio_final = post['AUTORIZACION']['CAF']['DA']['RNG']['H']
            if folio in range(int(folio_inicial), (int(folio_final)+1)):
                post = json.dumps(post, ensure_ascii=False)
                return post
        if folio > int(folio_final):
            msg = '''El folio de este documento: {} está fuera de rango \
del CAF vigente (desde {} hasta {}). Solicite un nuevo CAF en el sitio \
www.sii.cl'''.format(folio, folio_inicial, folio_final)
            caffile.status = 'spent'
            raise UserError(_(msg))
