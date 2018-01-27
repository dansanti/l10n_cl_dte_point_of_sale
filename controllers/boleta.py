# -*- coding: utf-8 -*-

import urllib

from odoo import models, http, api
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
from odoo.tools.misc import formatLang

class Boleta(http.Controller):

    @http.route(['/boleta'], type='http', auth="public", website=True)
    def input_document(self, **post):
        if not 'boleta' in post:
            return request.render('l10n_cl_dte_point_of_sale.boleta_layout')
        return request.redirect('/boleta/%s?%s' % (post['boleta'], urllib.parse.urlencode(post)))

    @http.route(['/boleta/<int:folio>'], type='http', auth="public", website=True)
    def view_document(self, folio=None, **post):
        if 'otra_boleta' in post:
            return request.redirect('/boleta/%s' %(post['otra_boleta']))
        Model = request.env['pos.order'].sudo()
        domain = [('sii_document_number', '=', int(folio))]
        #if post.get('date_invoice', ''):
        #    domain.append(('date_order','=',post.get('date_invoice', '')))
        #if post.get('amount_total', ''):
        #    domain.append(('amount_total','=',float(post.get('amount_total', ''))))
        if post.get('sii_codigo', ''):
            domain.append(('document_class_id.sii_code','=',int(post.get('sii_codigo', ''))))
        else:
            domain.append(('document_class_id.sii_code', 'in', [39, 41] ))
        orders = Model.search(domain, limit=1)
        if not orders:
            Model = request.env['account.invoice'].sudo()
            domain = [('sii_document_number', '=', folio)]
            if post.get('date_invoice', ''):
                domain.append(('date_invoice','=',post.get('date_invoice', '')))
            if post.get('amount_total', ''):
                domain.append(('amount_total','=',post.get('amount_total', '')))
            if post.get('sii_codigo', ''):
                domain.append(('sii_document_class_id.sii_code','=',int(post.get('sii_codigo', ''))))
            else:
                domain.append(('sii_document_class_id.sii_code', 'in', [39, 41] ))
            orders = Model.search(domain, limit=1)
        values = {
            'docs': orders,
            'formatLang': formatLang,
            'print_error': not bool(orders),
        }
        return request.render('l10n_cl_dte_point_of_sale.boleta_layout', values)

    @http.route(['/download/boleta'], type='http', auth="public", website=True)
    def download_boleta(self, **post):
        document = request.env[post['model']].sudo().browse(int(post['model_id']))
        file_name = document._get_printed_report_name()
        if document._name == 'account.invoice':
            pdf = request.env.ref('account.account_invoices').sudo().render_qweb_pdf([document.id])[0]
        else:
            pdf = request.env.ref('l10n_cl_dte_point_of_sale.action_report_pos_boleta_ticket').sudo().render_qweb_pdf([document.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=%s.pdf;' % file_name)
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
