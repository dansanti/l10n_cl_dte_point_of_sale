# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class masive_send_dte_wizard(models.TransientModel):
    _name = 'sii.dte.send_moves.wizard'
    _description = 'SII Masive send Wizard'

    @api.model
    def _getIDs(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        count = 1
        orden = ''
        coma = ''
        for id in active_ids:
            orden += coma + str(id)+":"+str(count)
            coma = ','
            count += 1
        return orden

    orden = fields.Char(
        'Orden',
        required=True,
        default=_getIDs
        )

    @api.multi
    def confirm(self):
        ordenes = self.orden.split(',')
        invs = self.env['account.invoice']
        active_ids = []
        for orden in ordenes:
            id, value =orden.split(':')
            id = int(id)
            inv = invs.browse(id)
            inv.write({'sii_batch_number':value})
            active_ids.extend([id])
        self.env['account.invoice'].browse(active_ids).do_dte_send_invoice()
        return UserError("Enviado")
