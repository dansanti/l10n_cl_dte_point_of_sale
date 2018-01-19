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

    secuencia_boleta = fields.Many2one(
            'account.journal.sii_document_class',
            string='Documents Type',
        )
    secuencia_boleta_exenta = fields.Many2one(
            'account.journal.sii_document_class',
            string='Documents Type',
        )
    start_number = fields.Integer(
            string='Folio Inicio',
        )
    start_number_exentas = fields.Integer(
            string='Folio Inicio Exentas',
        )
    numero_ordenes = fields.Integer(
            string="Número de ordenes",
            default=0,
        )
    numero_ordenes_exentas = fields.Integer(
            string="Número de ordenes exentas",
            default=0,
        )
    caf_files = fields.Char(
            invisible=True,
        )
    caf_files_exentas = fields.Char(
            invisible=True,
        )

    def create(self, cr, uid, values, context=None):
        context = dict(context or {})
        pos_config = values.get('config_id', False) or context.get('default_config_id', False)
        jobj = self.pool.get('pos.config')
        config_id = jobj.browse(cr, uid, pos_config, context=context)
        context.update({'company_id': config_id.company_id.id})
        is_pos_user = self.pool['res.users'].has_group(cr, uid, 'point_of_sale.group_pos_user')
        if config_id.secuencia_boleta:
            sequence = config_id.secuencia_boleta.sequence_id
            start_number = sequence.number_next_actual
            sequence.update_next_by_caf()
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual
            values.update({
                'start_number': start_number,
                'secuencia_boleta': config_id.secuencia_boleta.id,
                'caf_files': self.get_caf_string(cr, uid, sequence, context=context),
            })
        if config_id.secuencia_boleta_exenta:
            sequence = config_id.secuencia_boleta_exenta.sequence_id
            start_number = sequence.number_next_actual
            sequence.update_next_by_caf(cr, uid, context=context)
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual
            values.update({
                'start_number_exentas': start_number,
                'secuencia_boleta_exenta': config_id.secuencia_boleta_exenta.id,
                'caf_files_exentas': self.get_caf_string(cr, uid, sequence, context=context),
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
