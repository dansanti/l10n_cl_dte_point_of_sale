# -*- coding: utf-8 -*-

from openerp import fields, models, api, _
from openerp.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.onchange('journal_id', 'partner_id', 'turn_issuer','invoice_turn')
    def _get_available_journal_document_class(self, default=None):
        for inv in self:
            invoice_type = 'out_invoice'
            document_class_ids = []
            document_class_id = False

            inv.available_journal_document_class_ids = self.env[
                'account.journal.sii_document_class']

    def get_left_numbers(self):
        for r in self:
            if r.journal_document_class_id and r.journal_document_class_id.sequence_id and r.journal_document_class_id.sequence_id.dte_caf_ids:
                r.left_number = r.journal_document_class_id.sequence_id.get_qty_available()

    available_journal_document_class_ids = fields.Many2many(
        'account.journal.sii_document_class',
    #    compute='_get_available_journal_document_class',
        string='Available Journal Document Classes')

    sii_document_class_id = fields.Many2one(
        'sii.document_class',
        related='journal_document_class_id.sii_document_class_id',
        string='Document Type',
        copy=False,
        store=True)

    journal_document_class_id = fields.Many2one(
        'account.journal.sii_document_class',
        'Documents Type',)
    ticket = fields.Boolean(string="¿Facturas en Formato Ticket?", default=False)
    next_number = fields.Integer(
        related="journal_document_class_id.sequence_id.number_next_actual",
        string="Next Number")
    left_number = fields.Integer(
        compute="get_left_numbers",
        string="Left Available Numbers")
    marcar = fields.Selection(
        [
            ('boleta', 'Boletas'),
            ('factura', 'Facturas'),
        ],
        string="Marcar por defecto",
        default='boleta',
    )

    def get_valid_document_letters(
            self, cr, uid, partner_id, operation_type='sale',
            company_id=False, vat_affected='SI', invoice_type='out_invoice', context=None):
        if context is None:
            context = {}

        document_letter_obj = self.pool.get('sii.document_letter')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        partner = self.pool.get('res.partner').browse(
            cr, uid, partner_id, context=context)

        if not partner_id or not company_id or not operation_type:
            return []

        partner = partner.commercial_partner_id

        if not company_id:
            company_id = context.get('company_id', user.company_id.id)
        company = self.pool.get('res.company').browse(
            cr, uid, company_id, context)

        if operation_type == 'sale':
            issuer_responsability_id = company.partner_id.responsability_id.id
            receptor_responsability_id = partner.responsability_id.id
            if invoice_type == 'out_invoice':
                if vat_affected == 'SI':
                    domain = [
                        ('issuer_ids', '=', issuer_responsability_id),
                        ('receptor_ids', '=', receptor_responsability_id),
                        ('name', '!=', 'C')]
                else:
                    domain = [
                        ('issuer_ids', '=', issuer_responsability_id),
                        ('receptor_ids', '=', receptor_responsability_id),
                        ('name', '=', 'C')]
            else:
                # nota de credito de ventas
                domain = [
                    ('issuer_ids', '=', issuer_responsability_id),
                    ('receptor_ids', '=', receptor_responsability_id)]
        elif operation_type == 'purchase':
            issuer_responsability_id = partner.responsability_id.id
            receptor_responsability_id = company.partner_id.responsability_id.id
            if invoice_type == 'in_invoice':
                print('responsabilidad del partner')
                if issuer_responsability_id == self.pool.get(
                        'ir.model.data').get_object_reference(
                        cr, uid, 'l10n_cl_invoice', 'res_BH')[1]:
                    print('el proveedor es de segunda categoria y emite boleta de honorarios')
                else:
                    print('el proveedor es de primera categoria y emite facturas o facturas no afectas')
                domain = [
                    ('issuer_ids', '=', issuer_responsability_id),
                    ('receptor_ids', '=', receptor_responsability_id)]
            else:
                # nota de credito de compras
                domain = ['|',('issuer_ids', '=', issuer_responsability_id),
                              ('receptor_ids', '=', receptor_responsability_id)]
        else:
            raise except_orm(_('Operation Type Error'),
                             _('Operation Type Must be "Sale" or "Purchase"'))

        # TODO: fijar esto en el wizard, o llamar un wizard desde aca
        # if not company.partner_id.responsability_id.id:
        #     raise except_orm(_('You have not settled a tax payer type for your\
        #      company.'),
        #      _('Please, set your company tax payer type (in company or \
        #      partner before to continue.'))

        document_letter_ids = document_letter_obj.search(
            cr, uid, domain, context=context)
        return document_letter_ids
