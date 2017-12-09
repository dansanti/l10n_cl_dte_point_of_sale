# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class masive_send_dte_wizard(models.TransientModel):
    _name = 'sii.dte.pos.masive_send.wizard'
    _description = 'SII Masive send Wizard'

    @api.model
    def _getIDs(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        return [(6, 0, active_ids)]

    documentos = fields.Many2many(
            'pos.order',
            string="Documentos",
            default=_getIDs,
        )

    @api.multi
    def confirm(self):
        self.documentos.do_dte_send_order()
        return UserError("Enviado")
