from openerp import SUPERUSER_ID
from openerp import models, http, api
from openerp.http import request
from openerp.addons.web.controllers.main import serialize_exception, content_disposition
import logging
_logger = logging.getLogger(__name__)

class Boleta(http.Controller):

    @http.route(['/boleta/<int:folio>'], type='http', auth="public", website=True)
    def download_document(self, folio=None, **kw):
        Model = request.registry['pos.order']
        cr, uid, context = request.cr, request.uid, request.context
        res = Model.search(cr, SUPERUSER_ID, [('sii_document_number', '=', folio ),
                                              ('document_class_id.sii_code', 'in', [39, 41] )], context=context)
        orders  = Model.browse(cr, SUPERUSER_ID, res, context=context)
        values = {
            'docs': orders,
        }
        return request.website.render('l10n_cl_dte_point_of_sale.website_layout', values)
