from odoo import SUPERUSER_ID
from odoo import models, http, api
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
import logging
_logger = logging.getLogger(__name__)

class Boleta(http.Controller):

    @http.route(['/boleta'], type='http', auth="public", website=True)
    def input_document(self, **post):
        if not 'boleta' in post:
            return request.website.render('l10n_cl_dte_point_of_sale.website_layout_input')
        return request.redirect('/boleta/%s' %(post['boleta']))

    @http.route(['/boleta/<int:folio>'], type='http', auth="public", website=True)
    def download_document(self, folio=None, **post):
        if 'otra_boleta' in post:
            return request.redirect('/boleta/%s' %(post['otra_boleta']))
        Model = request.registry['pos.order']
        cr, uid, context = request.cr, request.uid, request.context
        res = Model.search(cr, SUPERUSER_ID, [('sii_document_number', '=', folio ),
                                              ('document_class_id.sii_code', 'in', [39, 41] )],
                                            limit=1,
                                            context=context)
        orders  = Model.browse(cr, SUPERUSER_ID, res, context=context)
        values = {
            'docs': orders,
        }
        return request.website.render('l10n_cl_dte_point_of_sale.website_layout', values)
