odoo.define('l10n_cl_dte_point_of_sale.DB', function (require) {
"use strict";

var DB = require('point_of_sale.DB');

DB.include({
    _partner_search_string: function(partner){
        var str =  partner.name;
        if(partner.document_number){
            str += '|' + partner.document_number;
            str += '|' + partner.document_number.replace('.','');
        }
        if(partner.barcode){
            str += '|' + partner.barcode;
        }
        if(partner.address){
            str += '|' + partner.address;
        }
        if(partner.phone){
            str += '|' + partner.phone.split(' ').join('');
        }
        if(partner.mobile){
            str += '|' + partner.mobile.split(' ').join('');
        }
        if(partner.email){
            str += '|' + partner.email;
        }
        str = '' + partner.id + ':' + str.replace(':','') + '\n';
        return str;
    },
});
	
});