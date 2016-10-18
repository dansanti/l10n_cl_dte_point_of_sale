odoo.define('l10n_cl_dte_post_of_sale.pos_dte', function (require) {
"use strict";

// implementaciónen el lado del cliente de firma

  var models = require('point_of_sale.models');

  var modules = models.PosModel.prototype.models;

  for(var i=0; i<modules.length; i++){

      var model=modules[i];

      if(model.model === 'res.company'){
           model.fields.push('activity_description','street','city');
      }
      if(model.model === 'res.partner'){
           model.fields.push('document_number');
      }
      if(model.model === 'pos.session'){
           model.fields.push('caf_file', 'start_number');
      }
  }

  models.load_models({
      model: 'res.partner',
      fields: ['document_number',],
      domain: function(self){ return [['id','=', self.company.partner_id[0]]]; },
      loaded: function(self,company){
          self.company.document_number = company[0].document_number;
      },
  });

  models.load_models({
      model: 'sii.document_class',
      fields: ['id','name','sii_code'],
      domain: function(self){ return [['id','=', self.config.sii_document_class_id[0]]]; },
      loaded: function(self,dc){
          self.config.sii_document_class_id = dc[0];
      },
  });

  var PosModelSuper = models.PosModel.prototype.push_order;
  models.PosModel.prototype.push_order = function(order, opts) {
        if(order){
          var sii_document_number = (parseInt(order.sequence_number) - 1) + parseInt(this.pos_session.start_number);
          order.sii_document_number = sii_document_number;
          order.signature = order.timbrar(order);
        }
        return PosModelSuper.call(this, order, opts);
  };
  var _super_order = models.Order.prototype;
  models.Order = models.Order.extend({
    initialize: function(attr, options) {
          _super_order.initialize.call(this,attr,options);
          this.signature = this.signature || false;
          this.sii_document_number = this.sii_document_number || false;
    },
    export_as_JSON: function() {
         var json = _super_order.export_as_JSON.apply(this,arguments);
         json.sii_document_number = this.sii_document_number;
         json.signature = this.signature;
         return json;
     },
     init_from_JSON: function(json) {//carga pedido individual
          _super_order.init_from_JSON.apply(this,arguments);
          this.sii_document_number = json.sii_document_number;
          this.signature = json.signature;
      },
      export_for_printing: function() {
          var json = _super_order.export_for_printing.apply(this,arguments);
          for (var i=0;  i < this.pos.partners.length; i++)
          {
            if (this.pos.partners[i].id === this.pos.company.partner_id[0]){
              json.company.document_number = this.pos.partners[i].document_number;
              break;
            }
          }
          json.company.activity_description = this.pos.company.activity_description[1]
          json.sii_document_number = this.sii_document_number;
          json.client = this.get_client();
          return json;
      },
      timbrar: function(order){
          if (order.signature){ //no firmar otra vez
            return order.signature;
          }
          var caf_file = JSON.parse(this.pos.pos_session.caf_file);
          var priv_key = caf_file.AUTORIZACION.RSASK;
          var pki = forge.pki;
          var privateKey = pki.privateKeyFromPem(priv_key);
          var md = forge.md.sha1.create();
          var partner_id = this.get_client();
          if(!partner_id){
            partner_id = {};
            partner_id.document_number = "66666666-6";
            partner_id.name = "Usuario Anonimo";
          }
          var orderlines = [];
          this.orderlines.each(function(orderline){
               orderlines.push(orderline.export_for_printing());
         });
         var d = order.validation_date;
          var date = d.toISOString();
          var curr_date = d.getDate();
          var curr_month = d.getMonth() + 1; //Months are zero based
          var curr_year = d.getFullYear();
          date = date.split('.')[0];
          var string='<DD>' +
                '<RE>' + this.pos.company.document_number.replace('.','').replace('.','') + '</RE>' +
                '<TD>' + this.pos.config.sii_document_class_id.sii_code + '</TD>' +
                '<F>' + order.sii_document_number + '</F>' +
                '<FE>' + curr_year + '-' + curr_month + '-' + curr_date + '</FE>' +
                '<RR>' + partner_id.document_number.replace('.','').replace('.','') +'</RR>' +
                '<RSR>' + partner_id.name + '</RSR>' +
                '<MNT>' + this.get_total_with_tax() + '</MNT>' +
                '<IT1>' + orderlines[0].product_name + '</IT1>' +
                '<CAF version="1.0"><DA><RE>' + caf_file.AUTORIZACION.CAF.DA.RE + '</RE>' +
                      '<RS>' + caf_file.AUTORIZACION.CAF.DA.RS + '</RS>' +
                      '<TD>' + caf_file.AUTORIZACION.CAF.DA.TD + '</TD>' +
                      '<RNG><D>' + caf_file.AUTORIZACION.CAF.DA.RNG.D + '</D><H>' + caf_file.AUTORIZACION.CAF.DA.RNG.H + '</H></RNG>' +
                      '<FA>' + caf_file.AUTORIZACION.CAF.DA.FA + '</FA>' +
                      '<RSAPK><M>' + caf_file.AUTORIZACION.CAF.DA.RSAPK.M + '</M><E>' + caf_file.AUTORIZACION.CAF.DA.RSAPK.E + '</E></RSAPK>' +
                      '<IDK>' + caf_file.AUTORIZACION.CAF.DA.IDK + '</IDK>' +
                    '</DA>' +
                    '<FRMA algoritmo="SHA1withRSA">' + caf_file.AUTORIZACION.CAF.FRMA["#text"] + '</FRMA>' +
                '</CAF>'+
                '<TSTED>' + date + '</TSTED></DD>';
          md.update(string);
          var signature = forge.util.encode64(privateKey.sign(md));
          string = '<TED version="1.0">' + string + '<FRMT algoritmo="SHA1withRSA">' + signature + '</FRMT></TED>';
          return string;
      },
      barcode_pdf417: function(){
        if (!this.pos.pos_session.caf_file){
          return "";
        }
        var order = this.pos.get_order();
          PDF417.init(order.signature);
          var barcode = PDF417.getBarcodeArray();
          var bw = 2;
          var bh = 2;
          var canvas = document.createElement('canvas');
          canvas.width = bw * barcode['num_cols'];
          canvas.height = bh * barcode['num_rows'];
          var ctx = canvas.getContext('2d');
          var y = 0;
          for (var r = 0; r < barcode['num_rows']; ++r) {
              var x = 0;
              for (var c = 0; c < barcode['num_cols']; ++c) {
                  if (barcode['bcode'][r][c] == 1) {
                      ctx.fillRect(x, y, bw, bh);
                  }
                  x += bw;
              }
              y += bh;
          }
          return canvas.toDataURL("image/png");
    },
  });
})
