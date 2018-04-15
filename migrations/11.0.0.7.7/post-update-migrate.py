# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, installed_version):
    _logger.warning('Post Migrating l10n_cl_fe from version %s to 11.0.0.7.7' % installed_version)

    cr.execute('ALTER TABLE sii_xml_envio ADD COLUMN order_temp INTEGER')
    cr.execute(
        "INSERT INTO sii_xml_envio (order_temp, xml_envio, company_id, sii_xml_response, state, name ) SELECT id, xml_temp, company_id, sii_xml_response_temp, sii_result, ('Folio_' || sii_document_number) as name FROM pos_order ai WHERE ai.xml_temp!=''")
    cr.execute(
        "ALTER TABLE pos_order DROP COLUMN xml_temp, DROP COLUMN sii_xml_response_temp, DROP COLUMN sii_send_file_name_temp")
    cr.execute("UPDATE pos_order ai SET sii_xml_request=sr.id FROM sii_xml_envio sr WHERE ai.id=sr.order_temp")
    cr.execute("ALTER TABLE sii_xml_envio DROP COLUMN order_temp")
