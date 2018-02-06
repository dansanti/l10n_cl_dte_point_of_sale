# -*- coding: utf-8 -*-

from odoo import models, api, fields, tools
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import _

class ResUsers(models.Model):

    _inherit = 'res.users'
    
    pos_config_ids = fields.Many2many('pos.config', 'pos_config_users_rel', 
        'user_id', 'config_id', u'TPV permitidos')
    
    @api.multi
    def write(self, values):
        res = super(ResUsers, self).write(values)
        # clear caches linked to the users
        if 'pos_config_ids' in values:
            self.env['ir.model.access'].call_cache_clearing_methods()
            self.env['ir.rule'].clear_caches()
            self.has_group.clear_cache(self)
        return res
    
    @api.model
    def get_all_warehouse(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        user = self.sudo().browse(user_id)
        warehouse_recs = self.env['stock.warehouse'].browse()
        for config in user.pos_config_ids:
            if config.warehouse_id:
                warehouse_recs |= config.warehouse_id
        return warehouse_recs
    
    @api.model
    def get_all_location(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        user = self.sudo().browse(user_id)
        location_recs = self.env['stock.location'].browse()
        for config in user.pos_config_ids:
            if config.stock_location_id:
                location_recs  |= config.stock_location_id
            warehouse = config.warehouse_id
            if warehouse.lot_stock_id:
                location_recs |= warehouse.lot_stock_id
            if warehouse.wh_input_stock_loc_id:
                location_recs |= warehouse.wh_input_stock_loc_id
            if warehouse.wh_qc_stock_loc_id:
                location_recs |= warehouse.wh_qc_stock_loc_id
            if warehouse.wh_output_stock_loc_id:
                location_recs |= warehouse.wh_output_stock_loc_id
            if warehouse.wh_pack_stock_loc_id:
                location_recs |= warehouse.wh_pack_stock_loc_id
        return location_recs
    
    @api.model
    def get_all_picking_type(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        user = self.sudo().browse(user_id)
        picking_type_recs = self.env['stock.picking.type']
        for config in user.pos_config_ids:
            if config.picking_type_id:
                picking_type_recs |= config.picking_type_id
            if config.warehouse_id:
                picking_type_recs |= config.warehouse_id.pick_type_id
                picking_type_recs |= config.warehouse_id.pack_type_id
                picking_type_recs |= config.warehouse_id.out_type_id
                picking_type_recs |= config.warehouse_id.in_type_id
                picking_type_recs |= config.warehouse_id.int_type_id
        return picking_type_recs