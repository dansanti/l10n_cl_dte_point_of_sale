# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)

class CreateActivity(models.Model):
    _inherit = 'sii.activity.description'

    def create_from_ui(self, cr, uid,  partner, context=None):
        obj = self.pool.get('sii.activity.description').create(cr, uid,
            {'name': partner['activity_description']}, context=context)
        return obj
