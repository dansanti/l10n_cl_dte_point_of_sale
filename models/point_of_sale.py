# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from lxml import etree
from lxml.etree import Element, SubElement
from odoo import SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
import time
import math

import xml.dom.minidom
import pytz
import socket
import collections
import logging

_logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    import OpenSSL
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except:
    _logger.warning('Cannot import OpenSSL library')

try:
    from io import BytesIO
except:
    _logger.warning("no se ha cargado io")

# ejemplo de suds
import traceback as tb
import suds.metrics as metrics

try:
    from suds.client import Client
except:
    pass

try:
    import urllib3
except:
    pass

try:
    urllib3.disable_warnings()
except:
    pass

try:
    pool = urllib3.PoolManager()
except:
    pass

try:
    import textwrap
except:
    pass

try:
    import xmltodict
except ImportError:
    _logger.info('Cannot import xmltodict library')

try:
    import dicttoxml
    dicttoxml.set_debug(False)
except ImportError:
    _logger.info('Cannot import dicttoxml library')

try:
    import pdf417gen
except ImportError:
    _logger.info('Cannot import pdf417gen library')

try:
    import base64
except ImportError:
    _logger.info('Cannot import base64 library')

try:
    import hashlib
except ImportError:
    _logger.info('Cannot import hashlib library')

# timbre patrón. Permite parsear y formar el
# ordered-dict patrón corespondiente al documento
timbre  = """<TED version="1.0"><DD><RE>99999999-9</RE><TD>11</TD><F>1</F>\
<FE>2000-01-01</FE><RR>99999999-9</RR><RSR>\
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</RSR><MNT>10000</MNT><IT1>IIIIIII\
</IT1><CAF version="1.0"><DA><RE>99999999-9</RE><RS>YYYYYYYYYYYYYYY</RS>\
<TD>10</TD><RNG><D>1</D><H>1000</H></RNG><FA>2000-01-01</FA><RSAPK><M>\
DJKFFDJKJKDJFKDJFKDJFKDJKDnbUNTAi2IaDdtAndm2p5udoqFiw==</M><E>Aw==</E></RSAPK>\
<IDK>300</IDK></DA><FRMA algoritmo="SHA1withRSA">\
J1u5/1VbPF6ASXkKoMOF0Bb9EYGVzQ1AMawDNOy0xSuAMpkyQe3yoGFthdKVK4JaypQ/F8\
afeqWjiRVMvV4+s4Q==</FRMA></CAF><TSTED>2014-04-24T12:02:20</TSTED></DD>\
<FRMT algoritmo="SHA1withRSA">jiuOQHXXcuwdpj8c510EZrCCw+pfTVGTT7obWm/\
fHlAa7j08Xff95Yb2zg31sJt6lMjSKdOK+PQp25clZuECig==</FRMT></TED>"""
result = xmltodict.parse(timbre)

server_url = {'SIICERT':'https://maullin.sii.cl/DTEWS/','SII':'https://palena.sii.cl/DTEWS/'}

BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''

# hardcodeamos este valor por ahora
import os
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace('/models','/static/xsd/')

connection_status = {
    '0': 'Upload OK',
    '1': 'El Sender no tiene permiso para enviar',
    '2': 'Error en tamaño del archivo (muy grande o muy chico)',
    '3': 'Archivo cortado (tamaño <> al parámetro size)',
    '5': 'No está autenticado',
    '6': 'Empresa no autorizada a enviar archivos',
    '7': 'Esquema Invalido',
    '8': 'Firma del Documento',
    '9': 'Sistema Bloqueado',
    'Otro': 'Error Interno.',
}

class POSL(models.Model):
    _inherit = 'pos.order.line'

    pos_order_line_id = fields.Integer(
            string="POS Line ID",
            readonly=True,
        )

class POS(models.Model):
    _inherit = 'pos.order'

    def _get_document_class_id(self):
        if self.sequence_id:
            return self.sequence_id.sii_document_class_id.id
        return self.env['sii.document_class']

    signature = fields.Char(
            string="Signature",
        )
    sequence_id = fields.Many2one(
            'ir.sequence',
            string='Sequencia de Boleta',
            states={'draft': [('readonly', False)]},
        )
    document_class_id = fields.Many2one(
            'sii.document_class',
            related="sequence_id.sii_document_class_id",
            string='Document Type',
            copy=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    sii_batch_number = fields.Integer(
            copy=False,
            string='Batch Number',
            readonly=True,
            help='Batch number for processing multiple invoices together',
        )
    sii_barcode = fields.Char(
            copy=False,
            string='SII Barcode',
            readonly=True,
            help='SII Barcode Name',
        )
    sii_barcode_img = fields.Binary(
            copy=False,
            string=_('SII Barcode Image'),
            help='SII Barcode Image in PDF417 format',
        )
    sii_message = fields.Text(
            string='SII Message',
            copy=False,
        )
    sii_xml_request = fields.Text(
            string='SII XML Request',
            copy=False,
        )
    sii_xml_response = fields.Text(
            string='SII XML Response',
            copy=False,
        )
    sii_send_ident = fields.Text(
            string='SII Send Identification',
            copy=False,
        )
    sii_result = fields.Selection(
            [
                    ('', 'n/a'),
                    ('NoEnviado', 'No Enviado'),
                    ('EnCola','En cola de envío'),
                    ('Enviado', 'Enviado'),
                    ('Aceptado', 'Aceptado'),
                    ('Rechazado', 'Rechazado'),
                    ('Reparo', 'Reparo'),
                    ('Proceso', 'Proceso'),
                    ('Reenviar', 'Reenviar'),
                    ('Anulado', 'Anulado')
            ],
            string='Resultado',
            readonly=True,
            states={'draft': [('readonly', False)]},
            copy=False,
            help="SII request result",
            default = '',
        )
    canceled = fields.Boolean(
            string="Canceled?",
        )
    sii_send_file_name = fields.Char(
            string="Send File Name",
        )
    responsable_envio = fields.Many2one(
            'res.users',
        )
    sii_document_number = fields.Integer(
            string="Folio de documento",
            copy=False,
        )
    referencias = fields.One2many(
            'pos.order.referencias',
            'order_id',
            string="References",
            readonly=True,
            states={'draft': [('readonly', False)]},
        )

    @api.model
    def _amount_line_tax(self, line, fiscal_position_id):
        taxes = line.tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
        if fiscal_position_id:
            taxes = fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
        cur = line.order_id.pricelist_id.currency_id
        taxes = taxes.compute_all(line.price_unit, cur, line.qty, product=line.product_id, partner=line.order_id.partner_id or False, discount=line.discount)['taxes']
        return sum(tax.get('amount', 0.0) for tax in taxes)

    def split_cert(self, cert):
        certf, j = '', 0
        for i in range(0, 29):
            certf += cert[76 * i:76 * (i + 1)] + '\n'
        return certf

    def create_template_envio(self, RutEmisor, RutReceptor, FchResol, NroResol,
                              TmstFirmaEnv, EnvioDTE,signature_d,SubTotDTE):
        xml = '''<SetDTE ID="SetDoc">
<Caratula version="1.0">
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<RutReceptor>{2}</RutReceptor>
<FchResol>{3}</FchResol>
<NroResol>{4}</NroResol>
<TmstFirmaEnv>{5}</TmstFirmaEnv>
{6}</Caratula>{7}
</SetDTE>
'''.format(RutEmisor, signature_d['subject_serial_number'], RutReceptor,
           FchResol, NroResol, TmstFirmaEnv, SubTotDTE, EnvioDTE)
        return xml

    def time_stamp(self, formato='%Y-%m-%dT%H:%M:%S'):
        tz = pytz.timezone('America/Santiago')
        return datetime.now(tz).strftime(formato)

    def xml_validator(self, some_xml_string, validacion='doc'):
        if validacion == 'bol':
            return True
        validacion_type = {
            'doc': 'DTE_v10.xsd',
            'env': 'EnvioDTE_v10.xsd',
            'env_boleta': 'EnvioBOLETA_v11.xsd',
            'recep' : 'Recibos_v10.xsd',
            'env_recep' : 'EnvioRecibos_v10.xsd',
            'env_resp': 'RespuestaEnvioDTE_v10.xsd',
            'sig': 'xmldsignature_v10.xsd'
        }
        xsd_file = xsdpath+validacion_type[validacion]
        try:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            xml_doc = etree.fromstring(some_xml_string)
            result = xmlschema.validate(xml_doc)
            if not result:
                xmlschema.assert_(xml_doc)
            return result
        except AssertionError as e:
            _logger.info(etree.tostring(xml_doc))
            raise UserError(_('XML Malformed Error:  %s') % e.args)

    def get_seed(self, company_id):
        return self.env['account.invoice'].get_seed(company_id)

    def create_template_seed(self, seed):
        return self.env['account.invoice'].create_template_seed(seed)

    def sign_seed(self, message, privkey, cert):
        return self.env['account.invoice'].sign_seed(message, privkey, cert)

    def get_token(self, seed_file, company_id):
        return self.env['account.invoice'].get_token(seed_file, company_id)

    def create_template_doc(self, doc):
        xml = '''<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
{}
</DTE>'''.format(doc)
        return xml

    def create_template_env(self, doc):
        xml = '''<EnvioDTE xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd" \
version="1.0">
{}
</EnvioDTE>'''.format(doc)
        return xml

    def create_template_env_boleta(self, doc):
        xml = '''<EnvioBOLETA xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioBOLETA_v11.xsd" \
version="1.0">
{}
</EnvioBOLETA>'''.format(doc)
        return xml

    def get_digital_signature_pem(self, comp_id):
        obj = user = self[0].responsable_envio if self else False
        if not obj:
            obj = user = self.env.user
        if not obj.cert:
            obj = comp_id or self.env.user.company_id
            if not obj or not obj.cert or not user.id in obj.authorized_users_ids.ids:
                obj = self.env['res.users'].search([("authorized_users_ids","=", user.id)])
            if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert,
            'rut_envia': obj.subject_serial_number
            }
        return signature_data

    def get_digital_signature(self, comp_id):
        obj = user = self[0].responsable_envio if self else False
        if not obj:
            obj = user = self.env.user
        if not obj.cert:
            obj = comp_id or self.env.user.company_id
            if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                obj = self.env['res.users'].search([("authorized_users_ids","=", user.id)])
            if not obj or not obj.cert:
                if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                    return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert}
        return signature_data

    def get_resolution_data(self, comp_id):
        resolution_data = {
            'dte_resolution_date': comp_id.dte_resolution_date,
            'dte_resolution_number': comp_id.dte_resolution_number}
        return resolution_data

    @api.multi
    def get_xml_file(self):
        return {
            'type' : 'ir.actions.act_url',
            'url': '/download/xml/boleta/%s' % (self.id ),
            'target': 'self',
        }

    def get_folio(self):
        # saca el folio directamente de la secuencia
        return int(self.sii_document_number)

    def format_vat(self, value):
        ''' Se Elimina el 0 para prevenir problemas con el sii, ya que las muestras no las toma si va con
        el 0 , y tambien internamente se generan problemas'''
        if not value or value=='' or value == 0:
            value ="CL666666666"
            #@TODO opción de crear código de cliente en vez de rut genérico
        rut = value[:10] + '-' + value[10:]
        rut = rut.replace('CL0','').replace('CL','')
        return rut

    def pdf417bc(self, ted):
        bc = pdf417gen.encode(
            ted,
            security_level=5,
            columns=13,
        )
        image = pdf417gen.render_image(
            bc,
            padding=15,
            scale=1,
        )
        return image

    def digest(self, data):
        sha1 = hashlib.new('sha1', data)
        return sha1.digest()

    def _acortar_str(self, texto, size=1):
        c = 0
        cadena = ""
        while c < size and c < len(texto):
            cadena += texto[c]
            c += 1
        return cadena

    @api.model
    def _process_order(self, order):
        lines = []
        for l in order['lines']:
            l[2]['pos_order_line_id'] = int(l[2]['id'])
            lines.append(l)
        order['lines'] = lines
        order_id = super(POS,self)._process_order(order)
        order_id.sequence_number = order['sequence_number'] #FIX odoo bug
        if order.get('orden_numero', False) and order.get('sequence_id', False):
            order_id.sequence_id = order['sequence_id'].get('id', False)
            if order_id.sequence_id and  order_id.sequence_id.sii_document_class_id.sii_code == 39 and order['orden_numero'] > 0:
                order_id.session_id.numero_ordenes = order['orden_numero']
                if order.get('force_sii_document_number'):
                    order_id.session_id.start_number = order['sii_document_number']
            elif order_id.sequence_id and order_id.sequence_id.sii_document_class_id.sii_code == 41 and order['orden_numero'] > 0:
                order_id.session_id.numero_ordenes_exentas = order['orden_numero']
                if order.get('force_sii_document_number'):
                    order_id.session_id.start_number_exentas = order['sii_document_number']
            order_id.sii_document_number = order['sii_document_number']
            sign = self.get_digital_signature(self.env.user.company_id)
            if (order_id.session_id.caf_files or order_id.session_id.caf_files_exentas) and sign:
                order_id.signature = order['signature']
                order_id._timbrar()
                #cuando se usa otro folio se pasa esta variable(desde JS)
                #debemos actualizar el siguiente folio de la secuencia en base al nuevo folio sumarle 1
                #caso contrario hacer el proceso normal
                if order.get('force_sii_document_number'):
                    order_id.sequence_id.sudo().write({'number_next': order_id.sii_document_number+1})
                else:
                    order_id.sequence_id.next_by_id()#consumo Folio
        return order_id

    def _prepare_invoice(self):
        result = super(POS, self)._prepare_invoice()
        journal_document_class_id = self.env['account.journal.sii_document_class'].search(
                [
                    ('journal_id','=', self.sale_journal.id),
                    ('sii_document_class_id.sii_code', 'in', ['33']),
                ],
            )
        if not journal_document_class_id:
            raise UserError("Por favor defina Secuencia de Facturas para el Journal del POS")
        available_turn_ids = self.company_id.company_activities_ids
        turn_issuer = False
        for turn in available_turn_ids:
            turn_issuer = turn
        result.update({
            'turn_issuer' : turn_issuer.id,
            'activity_description': self.partner_id.activity_description.id,
            'ticket':  self.session_id.config_id.ticket,
            'sii_document_class_id': journal_document_class_id.sii_document_class_id.id,
            'journal_document_class_id': journal_document_class_id.id,
            'responsable_envio': self.env.uid,
        })
        return result

    @api.multi
    def do_validate(self):
        for order in self:
            order.sii_result = 'NoEnviado'
            order.responsable_envio = self.env.user.id
            #if not order.invoice_id:
            order._timbrar()

    @api.multi
    def do_dte_send_order(self):
        invs = ids = []
        for order in self:
            if not order.invoice_id:
                if order.sii_result not in [False, '', 'NoEnviado']:
                    raise UserError("El documento %s ya ha sido enviado o está en cola de envío" % order.sii_document_number)
                order.responsable_envio = self.env.user.id
        self.do_dte_send()

    def _es_boleta(self, id_doc=False):
        if id_doc and id_doc in [35, 38, 39, 41, 70, 71]:
            return True
        elif id_doc:
            return False

        if self.document_class_id.sii_code in [35, 38, 39, 41, 70, 71]:
            return True
        return False

    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.company_id.company_activities_ids:
            giros_emisor.extend([{'Acteco': turn.code}])
        return giros_emisor

    def _id_doc(self, taxInclude=False, MntExe=0):
        util_model = self.env['cl.utils']
        fields_model = self.env['ir.fields.converter']
        from_zone = pytz.UTC
        to_zone = pytz.timezone('America/Santiago')
        date_order = util_model._change_time_zone(datetime.strptime(self.date_order, DTF), from_zone, to_zone).strftime(DTF)
        IdDoc= collections.OrderedDict()
        IdDoc['TipoDTE'] = self.document_class_id.sii_code
        IdDoc['Folio'] = self.get_folio()
        IdDoc['FchEmis'] = date_order[:10]
        if self._es_boleta():
            IdDoc['IndServicio'] = 3 #@TODO agregar las otras opciones a la fichade producto servicio
        else:
            IdDoc['TpoImpresion'] = "T"
            IdDoc['MntBruto'] = 1
            IdDoc['FmaPago'] = 1
        #if self.tipo_servicio:
        #    Encabezado['IdDoc']['IndServicio'] = 1,2,3,4
        # todo: forma de pago y fecha de vencimiento - opcional
        if not taxInclude:
        	IdDoc['IndMntNeto'] = 2
        #if self._es_boleta():
            #Servicios periódicos
        #    IdDoc['PeriodoDesde'] =
        #    IdDoc['PeriodoHasta'] =
        return IdDoc

    def _emisor(self):
        Emisor= collections.OrderedDict()
        Emisor['RUTEmisor'] = self.format_vat(self.company_id.vat)
        if self._es_boleta():
            Emisor['RznSocEmisor'] = self.company_id.partner_id.name
            Emisor['GiroEmisor'] = self._acortar_str(self.company_id.activity_description.name, 80)
        else:
            Emisor['RznSoc'] = self.company_id.partner_id.name
            Emisor['GiroEmis'] = self._acortar_str(self.company_id.activity_description.name, 80)
            Emisor['Telefono'] = self.company_id.phone or ''
            Emisor['CorreoEmisor'] = self.company_id.dte_email
            Emisor['item'] = self._giros_emisor()
        if self.sale_journal.sucursal_id:
            Emisor['Sucursal'] = self.sale_journal.sucursal_id.name
            Emisor['CdgSIISucur'] = self.sale_journal.sucursal_id.sii_code
        Emisor['DirOrigen'] = self.company_id.street + ' ' +(self.company_id.street2 or '')
        Emisor['CmnaOrigen'] = self.company_id.city_id.name or ''
        Emisor['CiudadOrigen'] = self.company_id.city or ''
        return Emisor

    def _receptor(self):
        Receptor = collections.OrderedDict()
        #Receptor['CdgIntRecep']
        Receptor['RUTRecep'] = self.format_vat(self.partner_id.vat)
        Receptor['RznSocRecep'] = self._acortar_str(self.partner_id.name or "Usuario Anonimo", 100)
        if self.partner_id.phone:
            Receptor['Contacto'] = self.partner_id.phone
        if self.partner_id.dte_email and not self._es_boleta():
            Receptor['CorreoRecep'] = self.partner_id.dte_email
        if self.partner_id.street:
            Receptor['DirRecep'] = self.partner_id.street+ ' ' + (self.partner_id.street2 or '')
        if self.partner_id.city_id:
            Receptor['CmnaRecep'] = self.partner_id.city_id.name
        if self.partner_id.city:
            Receptor['CiudadRecep'] = self.partner_id.city
        return Receptor

    def _totales(self, MntExe=0, no_product=False, taxInclude=False):
        Totales = collections.OrderedDict()
        amount_total = amount_total = int(round(self.amount_total, 0))
        if amount_total < 0:
            amount_total *= -1
        if self.document_class_id.sii_code == 34 :#@TODO Boletas exentas
            Totales['MntExe'] = amount_total
            if  no_product:
                Totales['MntExe'] = 0
        else :
            amount_untaxed =  self.amount_total - self.amount_tax
            if amount_untaxed < 0:
                amount_untaxed *= -1
            if MntExe < 0:
                MntExe *=-1
            Neto = amount_untaxed - MntExe
            if not taxInclude and not self._es_boleta():
                IVA = False
                for l in self.lines:
                    for t in l.tax_ids:
                        if t.sii_code in [14, 15]:
                            IVA = True
                            IVAAmount = round(t.amount,2)
                if IVA :
                    Totales['MntNeto'] = int(round((Neto), 0))
            if MntExe > 0:
                Totales['MntExe'] = int(round( MntExe))
            if not taxInclude and not self._es_boleta():
                if IVA:
                    if not self._es_boleta():
                        Totales['TasaIVA'] = IVAAmount
                    iva = int(round(self.amount_tax, 0))
                    if iva < 0:
                        iva *= -1
                    Totales['IVA'] = iva
                if no_product:
                    Totales['MntNeto'] = 0
                    Totales['IVA'] = 0
            #if IVA and IVA.tax_id.sii_code in [15]:
            #    Totales['ImptoReten'] = collections.OrderedDict()
            #    Totales['ImptoReten']['TpoImp'] = IVA.tax_id.sii_code
            #    Totales['ImptoReten']['TasaImp'] = round(IVA.tax_id.amount,2)
            #    Totales['ImptoReten']['MontoImp'] = int(round(IVA.amount))
        if no_product:
            amount_total = 0
        Totales['MntTotal'] = amount_total

        #Totales['MontoNF']
        #Totales['TotalPeriodo']
        #Totales['SaldoAnterior']
        #Totales['VlrPagar']
        return Totales

    def _encabezado(self, MntExe=0, no_product=False, taxInclude=False):
        Encabezado = collections.OrderedDict()
        Encabezado['IdDoc'] = self._id_doc(taxInclude, MntExe)
        Encabezado['Emisor'] = self._emisor()
        Encabezado['Receptor'] = self._receptor()
        Encabezado['Totales'] = self._totales(MntExe, no_product, taxInclude)
        return Encabezado

    @api.multi
    def get_barcode(self, no_product=False):
        util_model = self.env['cl.utils']
        fields_model = self.env['ir.fields.converter']
        from_zone = pytz.UTC
        to_zone = pytz.timezone('America/Santiago')
        date_order = util_model._change_time_zone(datetime.strptime(self.date_order, DTF), from_zone, to_zone).strftime(DTF)
        ted = False
        folio = self.get_folio()
        result['TED']['DD']['RE'] = self.format_vat(self.company_id.vat)
        result['TED']['DD']['TD'] = self.document_class_id.sii_code
        result['TED']['DD']['F']  = folio
        result['TED']['DD']['FE'] = date_order[:10]
        result['TED']['DD']['RR'] = self.format_vat(self.partner_id.vat)
        result['TED']['DD']['RSR'] = self._acortar_str(self.partner_id.name or 'Usuario Anonimo',40)
        amount_total = int(round(self.amount_total))
        if amount_total < 0:
            amount_total *= -1
        result['TED']['DD']['MNT'] = amount_total
        if no_product:
            result['TED']['DD']['MNT'] = 0
        lines = self.lines
        sorted(lines, key=lambda e: e.pos_order_line_id)
        result['TED']['DD']['IT1'] = self._acortar_str(lines[0].product_id.with_context(display_default_code=False, lang='es_CL').name,40)
        resultcaf = self.sequence_id.get_caf_file(folio)
        result['TED']['DD']['CAF'] = resultcaf['AUTORIZACION']['CAF']
        dte = result['TED']['DD']
        timestamp = date_order.replace(' ','T')
        #if date( int(timestamp[:4]), int(timestamp[5:7]), int(timestamp[8:10])) < date(int(self.date[:4]), int(self.date[5:7]), int(self.date[8:10])):
        #    raise UserError("La fecha de timbraje no puede ser menor a la fecha de emisión del documento")
        dte['TSTED'] = timestamp
        dicttoxml.set_debug(False)
        ddxml = '<DD>'+dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).decode().replace(
            '<key name="@version">1.0</key>','',1).replace(
            '><key name="@version">1.0</key>',' version="1.0">',1).replace(
            '><key name="@algoritmo">SHA1withRSA</key>',
            ' algoritmo="SHA1withRSA">').replace(
            '<key name="#text">','').replace(
            '</key>','').replace('<CAF>','<CAF version="1.0">')+'</DD>'
        keypriv = resultcaf['AUTORIZACION']['RSASK'].replace('\t','')
        root = etree.XML( ddxml )
        ddxml = etree.tostring(root)
        frmt = self.env['account.invoice'].signmessage(ddxml, keypriv)
        ted = (
            '''<TED version="1.0">{}<FRMT algoritmo="SHA1withRSA">{}\
</FRMT></TED>''').format(ddxml.decode(), frmt)
        if self.signature and ted != self.signature:
            _logger.warning(ted)
            _logger.warning(self.signature)
            _logger.warning("¡La firma del pos es distinta a la del Backend!")
        self.sii_barcode = ted
        image = False
        if ted:
            barcodefile = BytesIO()
            image = self.pdf417bc(ted)
            image.save(barcodefile,'PNG')
            data = barcodefile.getvalue()
            self.sii_barcode_img = base64.b64encode(data)
        ted  += '<TmstFirma>{}</TmstFirma>'.format(timestamp)
        return ted

    def _invoice_lines(self):
        line_number = 1
        invoice_lines = []
        no_product = False
        MntExe = 0
        for line in self.lines:
            if line.product_id.default_code == 'NO_PRODUCT':
                no_product = True
            lines = collections.OrderedDict()
            lines['NroLinDet'] = line_number
            if line.product_id.default_code and not no_product:
                lines['CdgItem'] = collections.OrderedDict()
                lines['CdgItem']['TpoCodigo'] = 'INT1'
                lines['CdgItem']['VlrCodigo'] = line.product_id.default_code
            taxInclude = False
            for t in line.tax_ids:
                taxInclude = t.price_include
                if t.amount == 0 or t.sii_code in [0]:#@TODO mejor manera de identificar exento de afecto
                    lines['IndExe'] = 1
                    MntExe += int(round(line.price_subtotal_incl, 0))
            #if line.product_id.type == 'events':
            #   lines['ItemEspectaculo'] =
#            if self._es_boleta():
#                lines['RUTMandante']
            lines['NmbItem'] = self._acortar_str(line.product_id.name,80) #
            lines['DscItem'] = self._acortar_str(line.name, 1000) #descripción más extenza
            if line.product_id.default_code:
                lines['NmbItem'] = self._acortar_str(line.product_id.name.replace('['+line.product_id.default_code+'] ',''),80)
            #lines['InfoTicket']
            qty = round(line.qty, 4)
            if qty < 0:
                qty *= -1
            if not no_product:
                lines['QtyItem'] = qty
            if qty == 0 and not no_product:
                lines['QtyItem'] = 1
                #raise UserError("NO puede ser menor que 0")
            if not no_product:
                lines['UnmdItem'] = line.product_id.uom_id.name[:4]
                lines['PrcItem'] = round(line.price_unit, 4)
            if line.discount > 0:
                lines['DescuentoPct'] = line.discount
                lines['DescuentoMonto'] = int(round((((line.discount / 100) * lines['PrcItem'])* qty)))
            if not no_product and not taxInclude:
                price = int(round(line.price_subtotal, 0))
            elif not no_product :
                price = int(round(line.price_subtotal_incl,0))
            if price < 0:
                price *= -1
            lines['MontoItem'] = price
            if no_product:
                lines['MontoItem'] = 0
            line_number += 1
            invoice_lines.extend([{'Detalle': lines}])
        return {
                'invoice_lines': invoice_lines,
                'MntExe':MntExe,
                'no_product':no_product,
                'tax_include': taxInclude,
                }

    def _dte(self):
        dte = collections.OrderedDict()
        invoice_lines = self._invoice_lines()
        dte['Encabezado'] = self._encabezado(invoice_lines['MntExe'], invoice_lines['no_product'], invoice_lines['tax_include'])
        lin_ref = 1
        ref_lines = []
        if 'referencias' in self and  self.referencias :
            for ref in self.referencias:
                ref_line = {}
                ref_line = collections.OrderedDict()
                ref_line['NroLinRef'] = lin_ref
                if not self._es_boleta():
                    if  ref.sii_referencia_TpoDocRef:
                        ref_line['TpoDocRef'] = ref.sii_referencia_TpoDocRef.sii_code
                        ref_line['FolioRef'] = ref.origen
                    ref_line['FchRef'] = ref.fecha_documento or datetime.strftime(datetime.now(), '%Y-%m-%d')
                if ref.sii_referencia_CodRef not in ['','none', False]:
                    ref_line['CodRef'] = ref.sii_referencia_CodRef
                ref_line['RazonRef'] = ref.motivo
                if self._es_boleta():
                    ref_line['CodVndor'] = self.user_id.id
                    ref_lines['CodCaja'] = self.location_id.name
                ref_lines.extend([{'Referencia':ref_line}])
                lin_ref += 1
        dte['item'] = invoice_lines['invoice_lines']
        dte['reflines'] = ref_lines
        dte['TEDd'] = self.get_barcode(invoice_lines['no_product'])
        return dte

    def _dte_to_xml(self, dte):
        ted = dte['Documento ID']['TEDd']
        dte['Documento ID']['TEDd'] = ''
        xml = dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).decode() \
            .replace('<item>','').replace('</item>','')\
            .replace('<reflines>','').replace('</reflines>','')\
            .replace('<TEDd>','').replace('</TEDd>','')\
            .replace('</Documento_ID>','\n'+ted+'\n</Documento_ID>')
        return xml

    def _timbrar(self):
        signature_d = self.get_digital_signature(self.company_id)
        if not signature_d:
            raise UserError(_('''There is no Signer Person with an \
        authorized signature for you in the system. Please make sure that \
        'user_signature_key' module has been installed and enable a digital \
        signature, for you or make the signer to authorize you to use his \
        signature.'''))
        certp = signature_d['cert'].replace(
            BC, '').replace(EC, '').replace('\n', '')
        folio = self.get_folio()
        dte = collections.OrderedDict()
        doc_id_number = "F{}T{}".format(folio, self.document_class_id.sii_code)
        doc_id = '<Documento ID="{}">'.format(doc_id_number)
        dte['Documento ID'] = self._dte()
        xml = self._dte_to_xml(dte)
        root = etree.XML( xml )
        xml_pret = etree.tostring(root, pretty_print=True).decode().replace(
'<Documento_ID>', doc_id).replace('</Documento_ID>', '</Documento>')
        envelope_efact = self.create_template_doc(xml_pret)
        type = 'bol'
        einvoice = self.env['account.invoice'].sign_full_xml(
                envelope_efact,
                signature_d['priv_key'],
                self.split_cert(certp),
                doc_id_number,
                type,
            )
        self.sii_xml_request = einvoice

    @api.multi
    def do_dte_send(self, n_atencion=None):
        dicttoxml.set_debug(False)
        DTEs = {}
        clases = {}
        company_id = False
        for inv in self.with_context(lang='es_CL'):
            try:
                signature_d = self.get_digital_signature(inv.company_id)
            except:
                raise UserError(_('''There is no Signer Person with an \
            authorized signature for you in the system. Please make sure that \
            'user_signature_key' module has been installed and enable a digital \
            signature, for you or make the signer to authorize you to use his \
            signature.'''))
            certp = signature_d['cert'].replace(
                BC, '').replace(EC, '').replace('\n', '')
            #@TODO Mejarorar esto en lo posible
            if not inv.document_class_id.sii_code in clases:
                clases[inv.document_class_id.sii_code] = []
            clases[inv.document_class_id.sii_code].extend([{
                                                'id':inv.id,
                                                'envio': inv.sii_xml_request,
                                                'sii_document_number':inv.sii_document_number
                                            }])
            DTEs.update(clases)
            if not company_id:
                company_id = inv.company_id
            elif company_id.id != inv.company_id.id:
                raise UserError("Está combinando compañías, no está permitido hacer eso en un envío")
            company_id = inv.company_id

        file_name = ""
        dtes={}
        SubTotDTE = {}
        documentos = {}
        resol_data = self.get_resolution_data(company_id)
        signature_d = self.get_digital_signature(company_id)
        RUTEmisor = self.format_vat(company_id.vat)

        for id_class_doc, classes in clases.items():
            NroDte = 0
            documentos[id_class_doc] = ''
            for documento in classes:
                documentos[id_class_doc] += '\n' + documento['envio']
                NroDte += 1
                file_name += 'F' + str(int(documento['sii_document_number'])) + 'T' + str(id_class_doc)
            SubTotDTE[id_class_doc] = '<SubTotDTE>\n<TpoDTE>' + str(id_class_doc) + '</TpoDTE>\n<NroDTE>'+str(NroDte)+'</NroDTE>\n</SubTotDTE>\n'
        file_name += ".xml"
        # firma del sobre
        RUTRecep = "60803000-K" # RUT SII
        for id_class_doc, documento in documentos.items():
            dtes = self.create_template_envio(
                RUTEmisor,
                RUTRecep,
                resol_data['dte_resolution_date'],
                resol_data['dte_resolution_number'],
                self.time_stamp(),
                documento,
                signature_d,
                SubTotDTE[id_class_doc] )
            env = 'env'
            if self._es_boleta(id_class_doc):
                envio_dte  = self.create_template_env_boleta(dtes)
                env = 'env_boleta'
            else:
                envio_dte  = self.create_template_env(dtes)
            envio_dte = self.env['account.invoice'].sign_full_xml(
                    envio_dte,
                    signature_d['priv_key'],
                    certp,
                    'SetDoc',
                    env,
                )
            for inv in self:
                if inv.document_class_id.sii_code == id_class_doc:
                    inv.sii_xml_request = envio_dte
                    inv.sii_send_file_name = file_name

    def _get_send_status(self, track_id, signature_d,token):
        url = server_url[self.company_id.dte_service_provider] + 'QueryEstUp.jws?WSDL'
        _server = Client(url)
        rut = self.format_vat(self.company_id.vat)
        respuesta = _server.service.getEstUp(rut[:8], str(rut[-1]),track_id,token)
        self.sii_message = respuesta
        resp = xmltodict.parse(respuesta)
        status = False
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "-11":
            if resp['SII:RESPUESTA']['SII:RESP_HDR']['ERR_CODE'] == "2":
                status =  {'warning':{'title':_('Estado -11'), 'message': _("Estado -11: Espere a que sea aceptado por el SII, intente en 5s más")}}
            else:
                status =  {'warning':{'title':_('Estado -11'), 'message': _("Estado -11: error 1Algo a salido mal, revisar carátula")}}
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.sii_result = "Proceso"
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.sii_result = "Rechazado"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCH":
            self.sii_result = "Rechazado"
            _logger.warning(resp)
            status = {'warning':{'title':_('Error RCT'), 'message': _(resp['SII:RESPUESTA']['GLOSA'])}}
        return status

    def _get_dte_status(self, signature_d, token):
        url = server_url[self.company_id.dte_service_provider] + 'QueryEstDte.jws?WSDL'
        _server = Client(url)
        receptor = self.format_vat(self.partner_id.vat)
        util_model = self.env['cl.utils']
        from_zone = pytz.UTC
        to_zone = pytz.timezone('America/Santiago')
        date_order = util_model._change_time_zone(datetime.strptime(self.date_order, DTF), from_zone, to_zone).strftime(DTF)[:10]
        date_invoice = datetime.strptime(date_order, "%Y-%m-%d").strftime("%d-%m-%Y")
        rut = signature_d['subject_serial_number']
        amount = int(self.amount_total)
        if amount < 0:
            amount *= -1
        respuesta = _server.service.getEstDte(rut[:8],
                                      str(rut[-1]),
                                      self.company_id.vat[2:-1],
                                      self.company_id.vat[-1],
                                      receptor[:8],
                                      receptor[-1],
                                      str(self.document_class_id.sii_code),
                                      str(self.sii_document_number),
                                      date_invoice,
                                      str(amount),
                                      token)
        self.sii_message = respuesta
        resp = xmltodict.parse(respuesta)
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == '2':
            status = {'warning':{'title':_("Error code: 2"), 'message': _(resp['SII:RESPUESTA']['SII:RESP_HDR']['GLOSA'])}}
            return status
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.sii_result = "Proceso"
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.sii_result = "Rechazado"
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['REPARO'] == "1":
                self.sii_result = "Reparo"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.sii_result = "Rechazado"

    @api.multi
    def ask_for_dte_status(self):
        try:
            signature_d = self.get_digital_signature_pem(
                self.company_id)
            seed = self.get_seed(self.company_id)
            template_string = self.create_template_seed(seed)
            seed_firmado = self.sign_seed(
                template_string, signature_d['priv_key'],
                signature_d['cert'])
            token = self.get_token(seed_firmado,self.company_id)
        except:
            _logger.warning(connection_status)
            raise UserError(connection_status)
        if not self.sii_send_ident:
            raise UserError('No se ha enviado aún el documento, aún está en cola de envío interna en odoo')
        if self.sii_result == 'Enviado':
            status = self._get_send_status(self.sii_send_ident, signature_d, token)
            if self.sii_result != 'Proceso':
                return status
        return self._get_dte_status(signature_d, token)

    def _create_account_move_line(self, session=None, move=None):
        # Tricky, via the workflow, we only have one id in the ids variable
        """Create a account move line of order grouped by products or not."""
        IrProperty = self.env['ir.property']
        ResPartner = self.env['res.partner']

        if session and not all(session.id == order.session_id.id for order in self):
            raise UserError(_('Selected orders do not have the same session!'))

        grouped_data = {}
        have_to_group_by = session and session.config_id.group_by or False
        rounding_method = session and session.config_id.company_id.tax_calculation_rounding_method
        document_class_id = False
        for order in self.filtered(lambda o: not o.account_move or o.state == 'paid'):
            if order.document_class_id:
                document_class_id = order.document_class_id

            current_company = order.sale_journal.company_id
            account_def = IrProperty.get(
                'property_account_receivable_id', 'res.partner')
            order_account = order.partner_id.property_account_receivable_id.id or account_def and account_def.id
            partner_id = ResPartner._find_accounting_partner(order.partner_id).id or False
            if move is None:
                # Create an entry for the sale
                journal_id = self.env['ir.config_parameter'].sudo().get_param(
                    'pos.closing.journal_id_%s' % current_company.id, default=order.sale_journal.id)
                move = self._create_account_move(
                    order.session_id.start_at, order.name, int(journal_id), order.company_id.id)

            def insert_data(data_type, values):
                # if have_to_group_by:

                # 'quantity': line.qty,
                # 'product_id': line.product_id.id,
                values.update({
                    'partner_id': partner_id,
                    'move_id': move.id,
                })
                key = self._get_account_move_line_group_data_type_key(data_type, values)
                if not key:
                    return

                grouped_data.setdefault(key, [])

                if have_to_group_by:
                    if not grouped_data[key]:
                        grouped_data[key].append(values)
                    else:
                        current_value = grouped_data[key][0]
                        current_value['quantity'] = current_value.get('quantity', 0.0) + values.get('quantity', 0.0)
                        current_value['credit'] = current_value.get('credit', 0.0) + values.get('credit', 0.0)
                        current_value['debit'] = current_value.get('debit', 0.0) + values.get('debit', 0.0)
                else:
                    grouped_data[key].append(values)

            # because of the weird way the pos order is written, we need to make sure there is at least one line,
            # because just after the 'for' loop there are references to 'line' and 'income_account' variables (that
            # are set inside the for loop)
            # TOFIX: a deep refactoring of this method (and class!) is needed
            # in order to get rid of this stupid hack
            assert order.lines, _('The POS order must have lines when calling this method')
            # Create an move for each order line
            cur = order.pricelist_id.currency_id
            # Create an move for each order line
            taxes = {}
            cur = order.pricelist_id.currency_id
            Afecto = 0
            Exento = 0
            Taxes = 0
            for line in order.lines:
                amount = line.price_subtotal
                # Search for the income account
                if line.product_id.property_account_income_id.id:
                    income_account = line.product_id.property_account_income_id.id
                elif line.product_id.categ_id.property_account_income_categ_id.id:
                    income_account = line.product_id.categ_id.property_account_income_categ_id.id
                else:
                    raise UserError(_('Please define income '
                                      'account for this product: "%s" (id:%d).')
                                    % (line.product_id.name, line.product_id.id))

                name = line.product_id.name
                if line.notice:
                    # add discount reason in move
                    name = name + ' (' + line.notice + ')'

                # Create a move for the line for the order line
                insert_data('product', {
                    'name': name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(line),
                    'credit': ((amount > 0) and amount) or 0.0,
                    'debit': ((amount < 0) and -amount) or 0.0,
                    'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids)],
                    'partner_id': partner_id
                })

                # Create the tax lines
                line_taxes = line.tax_ids_after_fiscal_position.filtered(lambda t: t.company_id.id == current_company.id)
                line_amount = line.price_unit * (100.0-line.discount) / 100.0
                line_amount *= line.qty
                line_amount = int(round(line_amount))
                if not line_taxes:
                    Exento += line_amount
                    continue
                for t in line_taxes:
                    taxes.setdefault(t, 0)
                    taxes[t] += line_amount
                    if t.amount > 0:
                        Afecto += amount
                    else:
                        Exento += amount
                pending_line = line
            #el Cálculo se hace sumando todos los valores redondeados, luego se cimprueba si hay descuadre de $1 y se agrega como línea de ajuste
            for t, value in taxes.items():
                tax = t.compute_all(value , cur, 1)['taxes'][0]
                insert_data('tax', {
                    'name': _('Tax') + ' ' + tax['name'],
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                    'account_id': tax['account_id'] or income_account,
                    'credit': int(round(((tax['amount']>0) and tax['amount']) or 0.0)),
                    'debit': int(round(((tax['amount']<0) and -tax['amount']) or 0.0)),
                    'tax_line_id': tax['id'],
                    'partner_id': partner_id
                })
                if t.amount > 0:
                    t_amount = int(round(tax['amount']))
                    Taxes += t_amount
            dif = ( order.amount_total - (Exento + Afecto + Taxes))
            if dif != 0:
                insert_data('product', {
                    'name': name,
                    'quantity': (1 * dif),
                    'product_id': pending_line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(line),
                    'credit': ((dif>0) and dif) or 0.0,
                    'debit': ((dif<0) and -dif) or 0.0,
                    'tax_ids': [(6, 0, pending_line.tax_ids_after_fiscal_position.ids)],
                    'partner_id': partner_id
                })

            #@TODO testear si esto ya repara los problemas de redondeo original de odoo
            # round tax lines per order
            #if rounding_method == 'round_globally':
            #    for group_key, group_value in grouped_data.items():
            #        if group_key[0] == 'tax':
            #            for line in group_value:
            #                line['credit'] = cur.round(line['credit'])
            #                line['debit'] = cur.round(line['debit'])

            # counterpart
            insert_data('counter_part', {
                'name': _("Trade Receivables"),  # order.name,
                'account_id': order_account,
                'credit': ((order.amount_total < 0) and -order.amount_total) or 0.0,
                'debit': ((order.amount_total > 0) and order.amount_total) or 0.0,
                'partner_id': partner_id
            })

            order.write({'state':'done', 'account_move': move.id})

        all_lines = []
        for group_key, group_data in grouped_data.items():
            for value in group_data:
                all_lines.append((0, 0, value),)
        if move:  # In case no order was changed
            move.sudo().write(
                    {
                            'line_ids':all_lines,
                            'document_class_id':  (document_class_id.id if document_class_id else False ),
                    }
                )
            move.sudo().post()
        return True

    @api.multi
    def action_pos_order_paid(self):
        if not self.test_paid():
            raise UserError(_("Order is not paid."))
        if self.sequence_id and not self.sii_xml_request:
            if (not self.sii_document_number or self.sii_document_number == 0) and not self.signature:
                self.sii_document_number = self.sequence_id.next_by_id()
            self.do_validate()
        self.write({'state': 'paid'})
        return self.create_picking()

    @api.depends('statement_ids', 'lines.price_subtotal_incl', 'lines.discount')
    def _compute_amount_all(self):
        for order in self:
            order.amount_paid = order.amount_return = order.amount_tax = 0.0
            currency = order.pricelist_id.currency_id
            order.amount_paid = sum(payment.amount for payment in order.statement_ids)
            order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.statement_ids)
            order.amount_tax = currency.round(sum(self._amount_line_tax(line, order.fiscal_position_id) for line in order.lines))
            amount_total = currency.round(sum(line.price_subtotal_incl for line in order.lines))
            order.amount_total = amount_total

    @api.multi
    def exento(self):
        exento = 0
        for l in self.lines:
            if l.tax_ids.amount == 0:
                exento += l.price_subtotal
        return exento if exento > 0 else (exento * -1)

    @api.multi
    def print_nc(self):
        """ Print NC
        """
        return self.env.ref('l10n_cl_dte_point_of_sale.action_print_nc').report_action(self)

    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        report_string = "%s %s" % (self.document_class_id.name, self.sii_document_number)
        return report_string

class Referencias(models.Model):
    _name = 'pos.order.referencias'

    origen = fields.Char(
            string="Origin",
        )
    sii_referencia_TpoDocRef =  fields.Many2one(
            'sii.document_class',
            string="SII Reference Document Type",
        )
    sii_referencia_CodRef = fields.Selection(
            [
                    ('1','Anula Documento de Referencia'),
                    ('2','Corrige texto Documento Referencia'),
                    ('3','Corrige montos')
            ],
            string="SII Reference Code",
        )
    motivo = fields.Char(
            string="Motivo",
        )
    order_id = fields.Many2one(
            'pos.order',
            ondelete='cascade',
            index=True,
            copy=False,
            string="Documento",
        )
    fecha_documento = fields.Date(
            string="Fecha Documento",
            required=True,
        )
