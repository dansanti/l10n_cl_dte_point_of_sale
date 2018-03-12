# -*- coding: utf-8 -*-

import pytz
from datetime import datetime

from odoo import models, api, fields
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import _

class ClUtils(models.AbstractModel):

    _name = 'cl.utils'
    _description = 'Utilidades Varias'
    
    @api.model
    def _change_time_zone(self, date, from_zone=None, to_zone=None):
        """
        Cambiar la informacion de zona horaria a la fecha
        En caso de no pasar la zona horaria destino, tomar la zona horaria del usuario
        @param date: Object datetime to convert according timezone in format '%Y-%m-%d %H:%M:%S'
        @return: datetime according timezone
        """
        assert isinstance(date, datetime), u'El parametro "date" debe ser tipo datetime'
        fields_model = self.env['ir.fields.converter']
        if not from_zone:
            #get timezone from user
            from_zone = fields_model._input_tz()
        #get UTC per Default
        if not to_zone:
            to_zone = pytz.UTC
        #si no hay informacion de zona horaria, establecer la zona horaria
        if not date.tzinfo:
            date = from_zone.localize(date)
        date = date.astimezone(to_zone)
        return date