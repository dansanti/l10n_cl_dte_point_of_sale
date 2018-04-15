# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, installed_version):
    _logger.warning('Pre Migrating l10n_cl_fe from version %s to 11.0.0.7.7' % installed_version)

    cr.execute(
        "ALTER TABLE pos_order ADD COLUMN xml_temp VARCHAR, ADD COLUMN sii_xml_response_temp VARCHAR, ADD COLUMN sii_send_file_name_temp VARCHAR")
    cr.execute(
        "UPDATE pos_order set xml_temp=sii_xml_request, sii_xml_response_temp=sii_xml_response, sii_send_file_name_temp=sii_send_file_name")
