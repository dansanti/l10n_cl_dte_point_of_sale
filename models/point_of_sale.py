# -*- coding: utf-8 -*-

from openerp import fields, models, api, _
from openerp.exceptions import UserError
from datetime import datetime, timedelta
import logging
from lxml import etree
from lxml.etree import Element, SubElement
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

import xml.dom.minidom
import pytz


import socket
import collections

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

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

_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    _logger.info('Cannot import xmltodict library')

try:
    import dicttoxml
except ImportError:
    _logger.info('Cannot import dicttoxml library')

try:
    from elaphe import barcode
except ImportError:
    _logger.info('Cannot import elaphe library')

try:
    import M2Crypto
except ImportError:
    _logger.info('Cannot import M2Crypto library')

try:
    import base64
except ImportError:
    _logger.info('Cannot import base64 library')

try:
    import hashlib
except ImportError:
    _logger.info('Cannot import hashlib library')

try:
    import cchardet
except ImportError:
    _logger.info('Cannot import cchardet library')

try:
    from SOAPpy import SOAPProxy
except ImportError:
    _logger.info('Cannot import SOOAPpy')

try:
    from signxml import xmldsig, methods
except ImportError:
    _logger.info('Cannot import signxml')

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

server_url = {'SIIHOMO':'https://maullin.sii.cl/DTEWS/','SII':'https://palena.sii.cl/DTEWS/'}

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
'''
Extensión del modelo de datos para contener parámetros globales necesarios
 para todas las integraciones de factura electrónica.
 @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
 @version: 2016-06-11
'''
class POSL(models.Model):
    _inherit = 'pos.order.line'
    pos_order_line_id = fields.Integer(string="POS Line ID", readonly=True)

class POS(models.Model):
    _inherit = 'pos.order'

    signature = fields.Char(string="Signature")
    available_journal_document_class_ids = fields.Many2many(
        'account.journal.sii_document_class',
        #compute='_get_available_journal_document_class',
        string='Available Journal Document Classes')

    sii_document_class_id = fields.Many2one(
        'sii.document_class',
        related='journal_document_class_id.sii_document_class_id',
        string='Document Type',
        copy=False,
        readonly=True,
        store=True)
    journal_document_class_id = fields.Many2one(
        'account.journal.sii_document_class',
        'Documents Type',
        readonly=True,
        store=True,
        states={'draft': [('readonly', False)]})
    sii_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True,
        help='Batch number for processing multiple invoices together')

    sii_barcode = fields.Char(
        copy=False,
        string=_('SII Barcode'),
        readonly=True,
        help='SII Barcode Name')

    sii_barcode_img = fields.Binary(
        copy=False,
        string=_('SII Barcode Image'),
        help='SII Barcode Image in PDF417 format')

    sii_message = fields.Text(
        string='SII Message',
        copy=False)
    sii_xml_request = fields.Text(
        string='SII XML Request',
        copy=False)
    sii_xml_response = fields.Text(
        string='SII XML Response',
        copy=False)
    sii_send_ident = fields.Text(
        string='SII Send Identification',
        copy=False)
    sii_result = fields.Selection([
        ('', 'n/a'),
        ('NoEnviado', 'No Enviado'),
        ('EnCola','En cola de envío'),
        ('Enviado', 'Enviado'),
        ('Aceptado', 'Aceptado'),
        ('Rechazado', 'Rechazado'),
        ('Reparo', 'Reparo'),
        ('Proceso', 'Proceso'),
        ('Reenviar', 'Reenviar'),
        ('Anulado', 'Anulado')],
        'Resultado',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        help="SII request result",
        default = '')
    canceled = fields.Boolean(string="Canceled?")
    sii_send_file_name = fields.Char(string="Send File Name")
    responsable_envio = fields.Many2one('res.users')
    sii_document_number = fields.Integer(string="Folio de documento")

    def split_cert(self, cert):
        certf, j = '', 0
        for i in range(0, 29):
            certf += cert[76 * i:76 * (i + 1)] + '\n'
        return certf

    '''
    Funcion que permite crear una plantilla para el EnvioDTE
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
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

    '''
    Funcion auxiliar para conversion de codificacion de strings
     proyecto experimentos_dte
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2014-12-01
    '''
    def convert_encoding(self, data, new_coding = 'UTF-8'):
        encoding = cchardet.detect(data)['encoding']
        if new_coding.upper() != encoding.upper():
            data = data.decode(encoding, data).encode(new_coding)
        return data

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

    '''
    Funcion usada en autenticacion en SII
    Obtencion de la semilla desde el SII.
    Basada en función de ejemplo mostrada en el sitio edreams.cl
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2015-04-01
    '''
    def get_seed(self, company_id):
        #En caso de que haya un problema con la validación de certificado del sii ( por una mala implementación de ellos)
        #esto omite la validacion
        try:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        url = server_url[company_id.dte_service_provider] + 'CrSeed.jws?WSDL'
        ns = 'urn:'+server_url[company_id.dte_service_provider] + 'CrSeed.jws'
        _server = SOAPProxy(url, ns)
        root = etree.fromstring(_server.getSeed())
        semilla = root[0][0].text
        return semilla

    '''
    Funcion usada en autenticacion en SII
    Creacion de plantilla xml para realizar el envio del token
    Previo a realizar su firma
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def create_template_seed(self, seed):
        xml = u'''<getToken>
<item>
<Semilla>{}</Semilla>
</item>
</getToken>
'''.format(seed)
        return xml

    '''
    Funcion usada en autenticacion en SII
    Creacion de plantilla xml para envolver el DTE
    Previo a realizar su firma (1)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def create_template_doc(self, doc):
        xml = '''<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
{}
</DTE>'''.format(doc)
        return xml

    '''
    Funcion usada en autenticacion en SII
    Creacion de plantilla xml para envolver el Envio de DTEs
    Previo a realizar su firma (2da)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def create_template_env(self, doc):
        xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<EnvioDTE xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd" \
version="1.0">
{}
</EnvioDTE>'''.format(doc)
        return xml

    def create_template_env_boleta(self, doc):
        xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<EnvioBOLETA xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioBOLETA_v11.xsd" \
version="1.0">
{}
</EnvioBOLETA>'''.format(doc)
        return xml

    '''
    Funcion usada en autenticacion en SII
    Insercion del nodo de firma (1ra) dentro del DTE
    Una vez firmado.
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def create_template_doc1(self, doc, sign):
        xml = doc.replace('</DTE>', '') + sign + '</DTE>'
        return xml

    '''
    Funcion usada en autenticacion en SII
    Insercion del nodo de firma (2da) dentro del DTE
    Una vez firmado.
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def create_template_env1(self, doc, sign):
        xml = doc.replace('</EnvioDTE>', '') + sign + '</EnvioDTE>'
        return xml

    def append_sign_recep(self, doc, sign):
        xml = doc.replace('</Recibo>', '') + sign + '</Recibo>'
        return xml

    def append_sign_env_recep(self, doc, sign):
        xml = doc.replace('</EnvioRecibos>', '') + sign + '</EnvioRecibos>'
        return xml

    def append_sign_env_resp(self, doc, sign):
        xml = doc.replace('</RespuestaDTE>', '') + sign + '</RespuestaDTE>'
        return xml

    def append_sign_env_bol(self, doc, sign):
        xml = doc.replace('</EnvioBOLETA>', '') + sign + '</EnvioBOLETA>'
        return xml

    '''
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def sign_seed(self, message, privkey, cert):
        doc = etree.fromstring(message)
        signed_node = xmldsig(
            doc, digest_algorithm=u'sha1').sign(
            method=methods.enveloped, algorithm=u'rsa-sha1',
            key=privkey.encode('ascii'),
            cert=cert)
        msg = etree.tostring(
            signed_node, pretty_print=True).replace('ds:', '')
        return msg

    '''
    Funcion usada en autenticacion en SII
    Obtencion del token a partir del envio de la semilla firmada
    Basada en función de ejemplo mostrada en el sitio edreams.cl
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def get_token(self, seed_file,company_id):
        url = server_url[company_id.dte_service_provider] + 'GetTokenFromSeed.jws?WSDL'
        ns = 'urn:'+ server_url[company_id.dte_service_provider] +'GetTokenFromSeed.jws'
        _server = SOAPProxy(url, ns)
        tree = etree.fromstring(seed_file)
        ss = etree.tostring(tree, pretty_print=True, encoding='iso-8859-1')
        respuesta = etree.fromstring(_server.getToken(ss))
        token = respuesta[0][0].text
        return token

    def ensure_str(self,x, encoding="utf-8", none_ok=False):
        if none_ok is True and x is None:
            return x
        if not isinstance(x, str):
            x = x.decode(encoding)
        return x

    def long_to_bytes(self, n, blocksize=0):
        """long_to_bytes(n:long, blocksize:int) : string
        Convert a long integer to a byte string.
        If optional blocksize is given and greater than zero, pad the front of the
        byte string with binary zeros so that the length is a multiple of
        blocksize.
        """
        # after much testing, this algorithm was deemed to be the fastest
        s = b''
        n = long(n)  # noqa
        import struct
        pack = struct.pack
        while n > 0:
            s = pack(b'>I', n & 0xffffffff) + s
            n = n >> 32
        # strip off leading zeros
        for i in range(len(s)):
            if s[i] != b'\000'[0]:
                break
        else:
            # only happens when n == 0
            s = b'\000'
            i = 0
        s = s[i:]
        # add back some pad bytes.  this could be done more efficiently w.r.t. the
        # de-padding being done above, but sigh...
        if blocksize > 0 and len(s) % blocksize:
            s = (blocksize - len(s) % blocksize) * b'\000' + s
        return s

    def sign_full_xml(self, message, privkey, cert, uri, type='doc'):
        doc = etree.fromstring(message)
        string = etree.tostring(doc[0])
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        digest = base64.b64encode(self.digest(mess))
        reference_uri='#'+uri
        signed_info = Element("SignedInfo")
        c14n_method = SubElement(signed_info, "CanonicalizationMethod", Algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        sign_method = SubElement(signed_info, "SignatureMethod", Algorithm='http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        reference = SubElement(signed_info, "Reference", URI=reference_uri)
        transforms = SubElement(reference, "Transforms")
        SubElement(transforms, "Transform", Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        digest_method = SubElement(reference, "DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
        digest_value = SubElement(reference, "DigestValue")
        digest_value.text = digest
        signed_info_c14n = etree.tostring(signed_info,method="c14n",exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        if type in ['doc','recep']:
            att = 'xmlns="http://www.w3.org/2000/09/xmldsig#"'
        else:
            att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        #@TODO Find better way to add xmlns:xsi attrib
        signed_info_c14n = signed_info_c14n.replace("<SignedInfo>","<SignedInfo " + att + ">")
        sig_root = Element("Signature",attrib={'xmlns':'http://www.w3.org/2000/09/xmldsig#'})
        sig_root.append(etree.fromstring(signed_info_c14n))
        signature_value = SubElement(sig_root, "SignatureValue")
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        import OpenSSL
        from OpenSSL.crypto import *
        type_ = FILETYPE_PEM
        key=OpenSSL.crypto.load_privatekey(type_,privkey.encode('ascii'))
        signature= OpenSSL.crypto.sign(key,signed_info_c14n,'sha1')
        signature_value.text =textwrap.fill(base64.b64encode(signature),64)
        key_info = SubElement(sig_root, "KeyInfo")
        key_value = SubElement(key_info, "KeyValue")
        rsa_key_value = SubElement(key_value, "RSAKeyValue")
        modulus = SubElement(rsa_key_value, "Modulus")
        key = load_pem_private_key(privkey.encode('ascii'),password=None, backend=default_backend())
        modulus.text =  textwrap.fill(base64.b64encode(self.long_to_bytes(key.public_key().public_numbers().n)),64)
        exponent = SubElement(rsa_key_value, "Exponent")
        exponent.text = self.ensure_str(base64.b64encode(self.long_to_bytes(key.public_key().public_numbers().e)))
        x509_data = SubElement(key_info, "X509Data")
        x509_certificate = SubElement(x509_data, "X509Certificate")
        x509_certificate.text = '\n'+textwrap.fill(cert,64)
        msg = etree.tostring(sig_root)
        msg = msg if self.xml_validator(msg, 'sig') else ''
        if type in ['doc', 'bol']:
            fulldoc = self.create_template_doc1(message, msg)
        if type=='env':
            fulldoc = self.create_template_env1(message,msg)
        if type=='recep':
            fulldoc = self.append_sign_recep(message,msg)
        if type=='env_recep':
            fulldoc = self.append_sign_env_recep(message,msg)
        if type=='env_resp':
            fulldoc = self.append_sign_env_resp(message,msg)
        if type=='env_boleta':
            fulldoc = self.append_sign_env_bol(message,msg)
        fulldoc = fulldoc if self.xml_validator(fulldoc, type) else ''
        return fulldoc

    @api.multi
    def get_digital_signature_pem(self, comp_id):
        obj = user = self[0].responsable_envio
        if not obj:
            obj = user = self.env.user
        if not obj.cert:
            obj = self.env['res.users'].search([("authorized_users_ids","=", user.id)])
            if not obj or not obj.cert:
                obj = self.env['res.company'].browse([comp_id.id])
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

    @api.multi
    def get_digital_signature(self, comp_id):
        obj = user = self[0].responsable_envio
        if not obj:
            obj = user = self.env.user
        if not obj.cert:
            obj = self.env['res.users'].search([("authorized_users_ids","=", user.id)])
            if not obj or not obj.cert:
                obj = self.env['res.company'].browse([comp_id.id])
                if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                    return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert}
        return signature_data

    '''
    Funcion usada en SII
    Toma los datos referentes a la resolución SII que autoriza a
    emitir DTE
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def get_resolution_data(self, comp_id):
        resolution_data = {
            'dte_resolution_date': comp_id.dte_resolution_date,
            'dte_resolution_number': comp_id.dte_resolution_number}
        return resolution_data

    @api.multi
    def send_xml_file(self, envio_dte=None, file_name="envio",company_id=False, sii_result='NoEnviado', doc_ids=''):
        if not company_id.dte_service_provider:
            raise UserError(_("Not Service provider selected!"))
        try:
            signature_d = self.get_digital_signature_pem(
                company_id)
            seed = self.get_seed(company_id)
            template_string = self.create_template_seed(seed)
            seed_firmado = self.sign_seed(
                template_string, signature_d['priv_key'],
                signature_d['cert'])
            token = self.get_token(seed_firmado,company_id)
        except:
            _logger.info('error')
            return

        url = 'https://palena.sii.cl'
        if company_id.dte_service_provider == 'SIIHOMO':
            url = 'https://maullin.sii.cl'
        post = '/cgi_dte/UPL/DTEUpload'
        headers = {
            'Accept': 'image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/vnd.ms-powerpoint, application/ms-excel, application/msword, */*',
            'Accept-Language': 'es-cl',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; YComp 5.0.2.4)',
            'Referer': '{}'.format(company_id.website),
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
            'Cookie': 'TOKEN={}'.format(token),
        }
        params = collections.OrderedDict()
        params['rutSender'] = signature_d['subject_serial_number'][:8]
        params['dvSender'] = signature_d['subject_serial_number'][-1]
        params['rutCompany'] = company_id.vat[2:-1]
        params['dvCompany'] = company_id.vat[-1]
        params['archivo'] = (file_name,envio_dte,"text/xml")
        multi  = urllib3.filepost.encode_multipart_formdata(params)
        headers.update({'Content-Length': '{}'.format(len(multi[0]))})
        response = pool.request_encode_body('POST', url+post, params, headers)
        retorno = {'sii_xml_response': response.data, 'sii_result': 'NoEnviado','sii_send_ident':''}
        if response.status != 200:
            return retorno
        respuesta_dict = xmltodict.parse(response.data)
        if respuesta_dict['RECEPCIONDTE']['STATUS'] != '0':
            _logger.info(connection_status[respuesta_dict['RECEPCIONDTE']['STATUS']])
        else:
            retorno.update({'sii_result': 'Enviado','sii_send_ident':respuesta_dict['RECEPCIONDTE']['TRACKID']})
        return retorno

    '''
    Funcion para descargar el xml en el sistema local del usuario
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-05-01
    '''
    @api.multi
    def get_xml_file(self):
        filename = (self.document_number+'.xml').replace(' ','')
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=account.invoice\
&field=sii_xml_request&id=%s&filename=%s' % (self.id,filename),
            'target': 'self',
        }

    '''
    Funcion para descargar el folio tomando el valor desde la secuencia
    correspondiente al tipo de documento.
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-05-01
    '''
    def get_folio(self):
        # saca el folio directamente de la secuencia
        return int(self.sii_document_number)

    '''
         Se Retorna el CAF que corresponda a la secuencia, independiente del estado
         ya que si se suben 2 CAF y uno está por terminar y se hace un evío masivo
         Deja fuera Los del antiguo CAF, que son válidos aún, porque no se han enviado; y arroja Error
         de que la secuencia no está en el rango del CAF
    '''
    def get_caf_file(self):
        caffiles = self.journal_document_class_id.sequence_id.dte_caf_ids
        if not caffiles:
            raise UserError(_('''There is no CAF file available or in use \
for this Document. Please enable one.'''))
        folio = self.get_folio()
        for caffile in caffiles:
            post = base64.b64decode(caffile.caf_file)
            post = xmltodict.parse(post.replace(
                '<?xml version="1.0"?>','',1))
            folio_inicial = post['AUTORIZACION']['CAF']['DA']['RNG']['D']
            folio_final = post['AUTORIZACION']['CAF']['DA']['RNG']['H']
            #if folio in range(int(folio_inicial), (int(folio_final)+1)):
            return post
        if folio > int(folio_final):
            msg = '''El folio de este documento: {} está fuera de rango \
del CAF vigente (desde {} hasta {}). Solicite un nuevo CAF en el sitio \
www.sii.cl'''.format(folio, folio_inicial, folio_final)
            # defino el status como "spent"
            caffile.status = 'spent'
            raise UserError(_(msg))
        return False

    def format_vat(self, value):
        ''' Se Elimina el 0 para prevenir problemas con el sii, ya que las muestras no las toma si va con
        el 0 , y tambien internamente se generan problemas'''
        if not value or value=='' or value == 0:
            value ="CL666666666"
            #@TODO opción de crear código de cliente en vez de rut genérico
        rut = value[:10] + '-' + value[10:]
        rut = rut.replace('CL0','').replace('CL','')
        return rut

    '''
    Funcion creacion de imagen pdf417 basada en biblioteca elaphe
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-05-01
    '''
    def pdf417bc(self, ted):
        bc = barcode(
            'pdf417',
            ted,
            options = dict(
                compact = False,
                eclevel = 5,
                columns = 13,
                rowmult = 2,
                rows = 3
            ),
            margin=20,
            scale=1
        )
        return bc

    '''
    Funcion usada en SII
    para firma del timbre (dio errores de firma para el resto de los doc)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2015-03-01
    '''
    def digest(self, data):
        sha1 = hashlib.new('sha1', data)
        return sha1.digest()

    '''
    Funcion usada en SII
    para firma del timbre (dio errores de firma para el resto de los doc)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2015-03-01
    '''
    def signrsa(self, MESSAGE, KEY, digst=''):
        KEY = KEY.encode('ascii')
        rsa = M2Crypto.EVP.load_key_string(KEY)
        rsa.reset_context(md='sha1')
        rsa_m = rsa.get_rsa()
        rsa.sign_init()
        rsa.sign_update(MESSAGE)
        FRMT = base64.b64encode(rsa.sign_final())
        if digst == '':
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64eDigesncode(rsa_m.e)}
        else:
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64encode(rsa_m.e),
                'digest': base64.b64encode(self.digest(MESSAGE))}

    '''
    Funcion usada en SII
    para firma del timbre (dio errores de firma para el resto de los doc)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2015-03-01
    '''
    def signmessage(self, MESSAGE, KEY, pubk='', digst=''):
        rsa = M2Crypto.EVP.load_key_string(KEY)
        rsa.reset_context(md='sha1')
        rsa_m = rsa.get_rsa()
        rsa.sign_init()
        rsa.sign_update(MESSAGE)
        FRMT = base64.b64encode(rsa.sign_final())
        if digst == '':
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64encode(rsa_m.e)}
        else:
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64encode(rsa_m.e),
                'digest': base64.b64encode(self.digest(MESSAGE))}

    @api.onchange('journal_id', 'partner_id', 'turn_issuer','invoice_turn')
    def _get_available_journal_document_class(self, default=None):
        for inv in self:
            invoice_type = 'out_invoice'
            document_class_ids = []
            document_class_id = False

            inv.available_journal_document_class_ids = self.env[
                'account.journal.sii_document_class']
            if invoice_type in [
                    'out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
                operation_type = inv.get_operation_type(invoice_type)

                if inv.use_documents:
                    letter_ids = inv.get_valid_document_letters(
                        inv.partner_id.id, operation_type, inv.company_id.id,
                        inv.turn_issuer.vat_affected, invoice_type)

                    domain = [
                        ('journal_id', '=', inv.journal_id.id),
                        '|', ('sii_document_class_id.document_letter_id',
                              'in', letter_ids),
                             ('sii_document_class_id.document_letter_id', '=', False)]

                    # If document_type in context we try to serch specific document
                    # document_type = self._context.get('document_type', False)
                    # en este punto document_type siempre es falso.
                    # TODO: revisar esta opcion
                    #document_type = self._context.get('document_type', False)
                    #if document_type:
                    #    document_classes = self.env[
                    #        'account.journal.sii_document_class'].search(
                    #        domain + [('sii_document_class_id.document_type', '=', document_type)])
                    #    if document_classes.ids:
                    #        # revisar si hay condicion de exento, para poner como primera alternativa estos
                    #        document_class_id = self.get_document_class_default(document_classes)
                    if invoice_type  in [ 'in_refund', 'out_refund']:
                        domain += [('sii_document_class_id.document_type','in',['debit_note','credit_note'] )]
                    else:
                        domain += [('sii_document_class_id.document_type','in',['invoice','invoice_in'] )]

                    # For domain, we search all documents
                    document_classes = self.env[
                        'account.journal.sii_document_class'].search(domain)
                    document_class_ids = document_classes.ids

                    # If not specific document type found, we choose another one
                    if not document_class_id and document_class_ids:
                        # revisar si hay condicion de exento, para poner como primera alternativa estos
                        # to-do: manejar más fino el documento por defecto.
                        document_class_id = inv.get_document_class_default(document_classes)
                # incorporado nuevo, para la compra
                if operation_type == 'purchase':
                    inv.available_journals = []

            inv.available_journal_document_class_ids = document_class_ids
            if not inv.journal_document_class_id or default:
                if default:
                    for dc in document_classes:
                        if dc.sii_document_class_id.id == default:
                            document_class_id = dc.id
                inv.journal_document_class_id = document_class_id

    @api.multi
    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        """
        self.ensure_one()
        rel_invoices = self.search([
            ('number', '=', self.origin),
            ('state', 'not in',
                ['draft', 'proforma', 'proforma2', 'cancel'])])
        return rel_invoices

    def _acortar_str(self, texto, size=1):
        c = 0
        cadena = ""
        while c < size and c < len(texto):
            cadena += texto[c]
            c += 1
        return cadena

    @api.multi
    def action_paid(self):
        for o in self:
            if not o.invoice_id:
                consumo_folio = o.journal_document_class_id.sequence_id.next_by_id()
                if not o.sii_document_number:
                    o.sii_document_number = consumo_folio
                    o._timbrar()
        super(POS,self).action_paid()

    @api.model
    def _process_order(self, order):
        from datetime import timedelta, datetime
        from dateutil import parser
        offset = timedelta(hours=3)
        lines = []
        for l in order['lines']:
            l[2]['pos_order_line_id'] = int(l[2]['id'])
            lines.append(l)
        order['lines'] = lines
        dt = parser.parse(order['creation_date'])
        #FIX: no restar horas, debe guardarse en UTC
#         order['creation_date'] = (dt - offset).strftime('%Y-%m-%dT%H:%M:%S')
        order_id = super(POS,self)._process_order(order)
        order_id = self.browse(order_id)
        order_id.sequence_number = order['sequence_number'] #FIX odoo bug
        if order['orden_numero']:
            order_id.journal_document_class_id = order_id.session_id.journal_document_class_id
            order_id.sii_document_number = order_id.sequence_number + order_id.session_id.start_number - 1
            order_id.signature = order['signature']
            order_id._timbrar()
        return order_id.id

    def action_invoice(self, cr, uid, ids, context=None):
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')
        inv_ids = []

        for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
            # Force company for all SUPERUSER_ID action
            company_id = order.company_id.id
            local_context = dict(context or {}, force_company=company_id, company_id=company_id)
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            acc = order.partner_id.property_account_receivable_id.id
            inv = {
                'name': order.name,
                'origin': order.name,
                'account_id': acc,
                'journal_id': order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'activity_description': order.partner_id.activity_description.id,
                'comment': order.note or '',
                'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
                'company_id': company_id,
                'user_id': uid,
                'ticket':  True,
                'available_journal_document_class_ids': order.pos_session.config.available_journal_document_class_ids.ids,
                'sii_document_class_id': order.journal_document_class_id.sii_document_class_id.id,
                'journal_document_class_id': order.journal_document_class_id.id,
                'responsable_envio': uid,
            }
            invoice = inv_ref.new(cr, uid, inv)
            invoice._onchange_partner_id()
            invoice.fiscal_position_id = order.fiscal_position_id

            inv = invoice._convert_to_write(invoice._cache)
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, SUPERUSER_ID, inv, context=local_context)

            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'}, context=local_context)
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=local_context)[0][1]
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                    'account_analytic_id': self._prepare_analytic_account(cr, uid, line, context=local_context),
                    'name': inv_name,
                }

                #Oldlin trick
                invoice_line = inv_line_ref.new(cr, SUPERUSER_ID, inv_line, context=local_context)
                invoice_line._onchange_product_id()
                invoice_line.invoice_line_tax_ids = [tax.id for tax in invoice_line.invoice_line_tax_ids if tax.company_id.id == company_id]
                fiscal_position_id = line.order_id.fiscal_position_id
                if fiscal_position_id:
                    invoice_line.invoice_line_tax_ids = fiscal_position_id.map_tax(invoice_line.invoice_line_tax_ids)
                invoice_line.invoice_line_tax_ids = [tax.id for tax in invoice_line.invoice_line_tax_ids]
                # We convert a new id object back to a dictionary to write to bridge between old and new api
                inv_line = invoice_line._convert_to_write(invoice_line._cache)
                inv_line.update(price_unit=line.price_unit, discount=line.discount)
                inv_line_ref.create(cr, SUPERUSER_ID, inv_line, context=local_context)
            inv_ref.compute_taxes(cr, SUPERUSER_ID, [inv_id], context=local_context)
            self.signal_workflow(cr, uid, [order.id], 'invoice')
            inv_ref.signal_workflow(cr, SUPERUSER_ID, [inv_id], 'validate')

        if not inv_ids: return {}

        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False
        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }

    @api.multi
    def do_validate(self):
        for order in self:
            order.sii_result = 'NoEnviado'
            order.responsable_envio = self.env.user.id
            if not order.invoice_id:
                order._timbrar()

    @api.multi
    def do_dte_send_order(self, n_atencion=None):
        invs = ids = []
        for order in self:
            if not order.to_invoice:
                if order.sii_result not in ['','NoEnviado']:
                    raise UserError("El documento %s ya ha sido enviado o está en cola de envío" % inv.sii_document_number)
                order.responsable_envio = self.env.user.id
                order.sii_result = 'EnCola'
                ids.append(order.id)
        if len(ids) > 0:
            if not isinstance(n_atencion, unicode):
                n_atencion = ''
            self.env['sii.cola_envio'].create({
                                        'doc_ids': ids,
                                        'model':'pos.order',
                                        'user_id':self.env.user.id,
                                        'tipo_trabajo':'envio',
                                        'n_atencion': n_atencion
                                        })

    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.company_id.company_activities_ids:
            giros_emisor.extend([{'Acteco': turn.code}])
        return giros_emisor

    def _id_doc(self, taxInclude=False, MntExe=0):
        util_model = self.env['cl.utils']
        fields_model = self.env['ir.fields.converter']
        from_zone = pytz.UTC
        if 'tz' in self.env.context:
            to_zone = pytz.timezone(self.env.context['tz'])
        else:
            to_zone = fields_model._input_tz()
        date_order = util_model._change_time_zone(datetime.strptime(self.date_order, DTF), from_zone, to_zone).strftime(DTF)
        IdDoc= collections.OrderedDict()
        IdDoc['TipoDTE'] = self.sii_document_class_id.sii_code
        IdDoc['Folio'] = self.get_folio()
        IdDoc['FchEmis'] = date_order[:10]
        IdDoc['IndServicio'] = 3 #@TODO agregar las otras opciones a la fichade producto servicio
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
        Emisor['RznSocEmisor'] = self.company_id.partner_id.name
        Emisor['GiroEmisor'] = self._acortar_str(self.company_id.activity_description.name, 80)
        if self.sale_journal.sii_code:
            Emisor['Sucursal'] = self.sale_journal.sucursal.name
            Emisor['CdgSIISucur'] = self.sale_journal.sii_code
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
        if self.sii_document_class_id.sii_code == 34 :#@TODO Boletas exentas
            Totales['MntExe'] = int(round(self.amount_total, 0))
            if  no_product:
                Totales['MntExe'] = 0
        else :
            amount_untaxed =  self.amount_total - self.amount_tax
            Neto = amount_untaxed - MntExe
            if not taxInclude:
                IVA = False
                for l in self.lines:
                    for t in l.tax_ids:
                        if t.sii_code in [14, 15]:
                            IVA = True
                if IVA and IVA > 0 :
                    Totales['MntNeto'] = int(round((Neto), 0))
            if MntExe > 0:
                Totales['MntExe'] = int(round( MntExe))
            if not taxInclude:
                if IVA:
                    Totales['IVA'] = int(round(self.amount_tax, 0))
                if no_product:
                    Totales['MntNeto'] = 0
                    Totales['IVA'] = 0
            #if IVA and IVA.tax_id.sii_code in [15]:
            #    Totales['ImptoReten'] = collections.OrderedDict()
            #    Totales['ImptoReten']['TpoImp'] = IVA.tax_id.sii_code
            #    Totales['ImptoReten']['TasaImp'] = round(IVA.tax_id.amount,2)
            #    Totales['ImptoReten']['MontoImp'] = int(round(IVA.amount))
        monto_total = int(round(self.amount_total, 0))
        if no_product:
            monto_total = 0
        Totales['MntTotal'] = monto_total

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
        Encabezado['Totales'] = self._totales(MntExe, no_product)
        return Encabezado

    @api.multi
    def get_barcode(self, no_product=False):
        util_model = self.env['cl.utils']
        fields_model = self.env['ir.fields.converter']
        from_zone = pytz.UTC
        if 'tz' in self.env.context:
            to_zone = pytz.timezone(self.env.context['tz'])
        else:
            to_zone = fields_model._input_tz()
        date_order = util_model._change_time_zone(datetime.strptime(self.date_order, DTF), from_zone, to_zone).strftime(DTF)
        ted = False
        folio = self.get_folio()
        result['TED']['DD']['RE'] = self.format_vat(self.company_id.vat)
        result['TED']['DD']['TD'] = self.sii_document_class_id.sii_code
        result['TED']['DD']['F']  = folio
        result['TED']['DD']['FE'] = date_order[:10]
        result['TED']['DD']['RR'] = self.format_vat(self.partner_id.vat)
        result['TED']['DD']['RSR'] = self._acortar_str(self.partner_id.name or 'Usuario Anonimo',40)
        result['TED']['DD']['MNT'] = int(round(self.amount_total))
        if no_product:
            result['TED']['DD']['MNT'] = 0
        lines = self.lines
        sorted(lines, key=lambda e: e.pos_order_line_id)
        result['TED']['DD']['IT1'] = self._acortar_str(lines[0].product_id.with_context(display_default_code=False).name,40)
        resultcaf = self.get_caf_file()
        result['TED']['DD']['CAF'] = resultcaf['AUTORIZACION']['CAF']
        dte = result['TED']['DD']
        dicttoxml.set_debug(False)
        ddxml = '<DD>'+dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).replace(
            '<key name="@version">1.0</key>','',1).replace(
            '><key name="@version">1.0</key>',' version="1.0">',1).replace(
            '><key name="@algoritmo">SHA1withRSA</key>',
            ' algoritmo="SHA1withRSA">').replace(
            '<key name="#text">','').replace(
            '</key>','').replace('<CAF>','<CAF version="1.0">')+'</DD>'
        ddxml = self.convert_encoding(ddxml, 'utf-8')
        keypriv = (resultcaf['AUTORIZACION']['RSASK']).encode(
            'latin-1').replace('\t','')
        keypub = (resultcaf['AUTORIZACION']['RSAPUBK']).encode(
            'latin-1').replace('\t','')
        #####
        ## antes de firmar, formatear
        root = etree.XML( ddxml )
        ##
        # formateo sin remover indents
        ddxml = etree.tostring(root)
        timestamp = self.time_stamp()
        ddxml = ddxml.replace('2014-04-24T12:02:20', date_order.replace(' ','T'))
        frmt = self.signmessage(ddxml, keypriv, keypub)['firma']
        ted = (
            '''<TED version="1.0">{}<FRMT algoritmo="SHA1withRSA">{}\
</FRMT></TED>''').format(ddxml, frmt)
        root = etree.XML(ted)
        if ted != self.signature:
            _logger.info(ted)
            _logger.info(self.signature)
            raise UserError("¡La firma del pos es distinta a la del Backend!")
        self.sii_barcode = ted
        image = False
        if ted:
            barcodefile = StringIO()
            image = self.pdf417bc(ted)
            image.save(barcodefile,'PNG')
            data = barcodefile.getvalue()
            self.sii_barcode_img = base64.b64encode(data)
        ted  += '<TmstFirma>{}</TmstFirma>'.format(date_order.replace(' ','T'))
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
            if not no_product:
                lines['QtyItem'] = qty
            if qty == 0 and not no_product:
                lines['QtyItem'] = 1
            elif qty < 0:
                raise UserError("NO puede ser menor que 0")
            if not no_product:
                lines['UnmdItem'] = line.product_id.uom_id.name[:4]
                lines['PrcItem'] = round(line.price_unit, 4)
            if line.discount > 0:
                lines['DescuentoPct'] = line.discount
                lines['DescuentoMonto'] = int(round((((line.discount / 100) * lines['PrcItem'])* qty)))
            if not no_product and MntExe > 0:
                lines['MontoItem'] = int(round(MntExe))
            elif not no_product and not taxInclude:
                lines['MontoItem'] = int(round(line.price_subtotal, 0))
            elif not no_product :
                lines['MontoItem'] = int(round(line.price_subtotal_incl,0))
            if no_product:
                lines['MontoItem'] = 0
            line_number += 1
            invoice_lines.extend([{'Detalle': lines}])
            if 'IndExe' in lines:
            	taxInclude = False
        return {
                'invoice_lines': invoice_lines,
                'MntExe':MntExe,
                'no_product':no_product,
                'tax_include': taxInclude,
                }

    def _dte(self, n_atencion=None):
        dte = collections.OrderedDict()
        invoice_lines = self._invoice_lines()
        dte['Encabezado'] = self._encabezado(invoice_lines['MntExe'], invoice_lines['no_product'], invoice_lines['tax_include'])
        lin_ref = 1
        ref_lines = []
        if self.company_id.dte_service_provider == 'SIIHOMO' and isinstance(n_atencion, unicode) and not self._es_boleta():
            ref_line = {}
            ref_line = collections.OrderedDict()
            ref_line['NroLinRef'] = lin_ref
            ref_line['TpoDocRef'] = "SET"
            ref_line['FolioRef'] = self.get_folio()
            ref_line['FchRef'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
            ref_line['RazonRef'] = "CASO "+n_atencion+"-" + str(self.sii_batch_number)
            lin_ref = 2
            ref_lines.extend([{'Referencia':ref_line}])
        if 'referencias' in self and  self.referencias :
            for ref in self.referencias:
                ref_line = {}
                ref_line = collections.OrderedDict()
                ref_line['NroLinRef'] = lin_ref
                if ref.sii_referencia_CodRef not in ['','none', False]:
                    ref_line['CodRef'] = ref.sii_referencia_CodRef
                ref_line['RazonRef'] = ref.motivo
                ref_line['CodVndor'] = self.seler_id.id
                ref_lines['CodCaja'] = self.journal_id.point_of_sale_id.name
                ref_lines.extend([{'Referencia':ref_line}])
        dte['item'] = invoice_lines['invoice_lines']
        dte['reflines'] = ref_lines
        dte['TEDd'] = self.get_barcode(invoice_lines['no_product'])
        return dte

    def _dte_to_xml(self, dte):
        ted = dte['Documento ID']['TEDd']
        dte['Documento ID']['TEDd'] = ''
        xml = dicttoxml.dicttoxml(
            dte, root=False, attr_type=False) \
            .replace('<item>','').replace('</item>','')\
            .replace('<reflines>','').replace('</reflines>','')\
            .replace('<TEDd>','').replace('</TEDd>','')\
            .replace('</Documento_ID>','\n'+ted+'\n</Documento_ID>')
        return xml

    @api.multi
    def _timbrar(self, n_atencion=None):
        try:
            signature_d = self.get_digital_signature(self.company_id)
        except:
            raise UserError(_('''There is no Signer Person with an \
        authorized signature for you in the system. Please make sure that \
        'user_signature_key' module has been installed and enable a digital \
        signature, for you or make the signer to authorize you to use his \
        signature.'''))
        certp = signature_d['cert'].replace(
            BC, '').replace(EC, '').replace('\n', '')
        folio = self.get_folio()
        dte = collections.OrderedDict()
        doc_id_number = "F{}T{}".format(folio, self.sii_document_class_id.sii_code)
        doc_id = '<Documento ID="{}">'.format(doc_id_number)
        dte['Documento ID'] = self._dte(n_atencion)
        xml = self._dte_to_xml(dte)
        root = etree.XML( xml )
        xml_pret = etree.tostring(root, pretty_print=True).replace(
'<Documento_ID>', doc_id).replace('</Documento_ID>', '</Documento>')
        envelope_efact = self.convert_encoding(xml_pret, 'ISO-8859-1')
        envelope_efact = self.create_template_doc(envelope_efact)
        type = 'bol'
        einvoice = self.sign_full_xml(
            envelope_efact, signature_d['priv_key'],
            self.split_cert(certp), doc_id_number, type)
        self.sii_xml_request = einvoice

    @api.multi
    def do_dte_send(self, n_atencion="612122"):
        dicttoxml.set_debug(False)
        DTEs = {}
        clases = {}
        company_id = False
        es_boleta = False
        for inv in self.with_context(lang='es_CL'):
            es_boleta = inv._es_boleta()
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
            if inv.company_id.dte_service_provider == 'SIIHOMO': #Retimbrar con número de atención y envío
                inv._timbrar(n_atencion)
            #@TODO Mejarorar esto en lo posible
            if not inv.sii_document_class_id.sii_code in clases:
                clases[inv.sii_document_class_id.sii_code] = []
            clases[inv.sii_document_class_id.sii_code].extend([{
                                                'id':inv.id,
                                                'envio': inv.sii_xml_request,
                                                'sii_batch_number': inv.sii_batch_number,
                                                'sii_document_number':inv.sii_document_number
                                            }])
            DTEs.update(clases)
            if not company_id:
                company_id = inv.company_id
            elif company_id.id != inv.company_id.id:
                raise UserError("Está combinando compañías, no está permitido hacer eso en un envío")
            company_id = inv.company_id
            #@TODO hacer autoreconciliación

        file_name = ""
        dtes={}
        SubTotDTE = ''
        resol_data = self.get_resolution_data(company_id)
        signature_d = self.get_digital_signature(company_id)
        RUTEmisor = self.format_vat(company_id.vat)
        for id_class_doc, classes in clases.iteritems():
            NroDte = 0
            for documento in classes:
                dtes.update({str(documento['sii_batch_number']): documento['envio']})
                NroDte += 1
                file_name += 'F' + str(int(documento['sii_document_number'])) + 'T' + str(id_class_doc)
            SubTotDTE += '<SubTotDTE>\n<TpoDTE>' + str(id_class_doc) + '</TpoDTE>\n<NroDTE>'+str(NroDte)+'</NroDTE>\n</SubTotDTE>\n'
        file_name += ".xml"
        documentos =""
        for key in sorted(dtes.iterkeys()):
            documentos += '\n'+dtes[key]
        # firma del sobre
        RUTRecep = "60803000-K" # RUT SII
        dtes = self.create_template_envio( RUTEmisor, RUTRecep,
            resol_data['dte_resolution_date'],
            resol_data['dte_resolution_number'],
            self.time_stamp(), documentos, signature_d,SubTotDTE )
        env = 'env'
        if es_boleta:
            envio_dte  = self.create_template_env_boleta(dtes)
            env = 'env_boleta'
        else:
            envio_dte  = self.create_template_env(dtes)
        envio_dte = self.sign_full_xml(
            envio_dte, signature_d['priv_key'], certp,
            'SetDoc', env)
        result = self.send_xml_file(envio_dte, file_name, company_id)
        for inv in self:
            inv.write({'sii_xml_response':result['sii_xml_response'],
                'sii_send_ident':result['sii_send_ident'],
                'sii_result': result['sii_result'],
                'sii_xml_request':envio_dte,
                'sii_send_file_name' : file_name,
                })

    def _get_send_status(self, track_id, signature_d,token):
        url = server_url[self.company_id.dte_service_provider] + 'QueryEstUp.jws?WSDL'
        ns = 'urn:'+ server_url[self.company_id.dte_service_provider] + 'QueryEstUp.jws'
        _server = SOAPProxy(url, ns)
        rut = self.format_vat(self.company_id.vat)
        respuesta = _server.getEstUp(rut[:8], str(rut[-1]),track_id,token)
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
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.sii_result = "Rechazado"
            _logger.info(resp)
            status = {'warning':{'title':_('Error RCT'), 'message': _(resp['SII:RESPUESTA']['GLOSA'])}}
        return status

    def _get_dte_status(self, signature_d, token):
        url = server_url[self.company_id.dte_service_provider] + 'QueryEstDte.jws?WSDL'
        ns = 'urn:'+ server_url[self.company_id.dte_service_provider] + 'QueryEstDte.jws'
        _server = SOAPProxy(url, ns)
        receptor = self.format_vat(self.partner_id.vat)
        date_invoice = datetime.strptime(self.date_invoice, "%Y-%m-%d").strftime("%d-%m-%Y")
        rut = signature_d['subject_serial_number']
        respuesta = _server.getEstDte(rut[:8], str(rut[-1]),
                self.company_id.vat[2:-1],self.company_id.vat[-1], receptor[:8],receptor[2:-1],str(self.sii_document_class_id.sii_code), str(self.sii_document_number),
                date_invoice, str(self.amount_total),token)
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
            _logger.info(connection_status)
            raise UserError(connection_status)
        if not self.sii_send_ident:
            raise UserError('No se ha enviado aún el documento, aún está en cola de envío interna en odoo')
        if self.sii_result == 'Enviado':
            status = self._get_send_status(self.sii_send_ident, signature_d, token)
            if self.sii_result != 'Proceso':
                return status
        return self._get_dte_status(signature_d, token)
