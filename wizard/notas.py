# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError
import time
import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _name = "pos.order.refund"

    tipo_nota = fields.Many2one('sii.document_class', string="Tipo De nota", required=True, domain=[('document_type','in',['debit_note','credit_note']), ('dte','=',True)])
    filter_refund = fields.Selection([
                ('1','Anula Documento de Referencia'),
                ('2','Corrige texto Documento Referencia'),
                ('3','Corrige montos')
                ],
                default='1',
                string='Refund Method',
                required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled')
    motivo = fields.Char("Motivo")
    date_order = fields.Date(string="Fecha de Documento")

    @api.multi
    def confirm(self):
        """Create a copy of order  for refund order"""
        clone_list = []
        line_obj = self.env['pos.order.line']
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for order in self.env['pos.order'].browse(active_ids):
            current_session_ids = self.env['pos.session'].search( [
                ('state', '!=', 'closed'),
                ('user_id', '=', self.env.user.id)])
            if not current_session_ids:
                raise UserError(_('To return product(s), you need to open a session that will be used to register the refund.'))

            jdc_ob = self.env['account.journal.sii_document_class']
            journal_document_class_id = jdc_ob.search(
                    [
                        ('journal_id','=', order.sale_journal.id),
                        ('sii_document_class_id.sii_code', 'in', ['61']),
                    ])
            if not journal_document_class_id:
                raise UserError("Por favor defina Secuencia de Notas de Crédito para el Journal del POS")
            clone_id = order.copy( {
                'name': order.name + ' REFUND', # not used, name forced by create
                'session_id': current_session_ids[0].id,
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
                'journal_document_class_id': journal_document_class_id.id,
                'document_class_id': journal_document_class_id.sii_document_class_id.id,
                'sii_document_number': 0,
                'signature': False,
                'referencias':[[5,],[0,0, {
                    'origen': int(order.sii_document_number),
                    'sii_referencia_TpoDocRef': order.document_class_id.id,
                    'sii_referencia_CodRef': self.filter_refund,
                    'motivo': self.motivo,
                    'fecha_documento': self.date_order
                }]],
            })
            clone_list.append(clone_id.id)
        clone_list = self.env['pos.order'].browse(clone_list)
        for clone in clone_list:
            for order_line in clone.lines:
                order_line.write( {
                    'qty': -order_line.qty
                })
        abs = {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id':clone_list.id,
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        return abs
