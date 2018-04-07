# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class CreateActivity(models.Model):
    _inherit = 'sii.activity.description'

    @api.model
    def create_from_ui(self, partner):
        obj = self.env['sii.activity.description'].create({'name': partner['activity_description']})
        return obj.id
