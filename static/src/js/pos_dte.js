odoo.define('l10n_cl_dte_point_of_sale.pos_dte', function (require) {
"use strict";

// implementaciónen el lado del cliente de firma

  var models = require('point_of_sale.models');
  var PosBaseWidget = require('point_of_sale.BaseWidget');
  var utils = require('web.utils');
  var screens = require('point_of_sale.screens');
  var core = require('web.core');
  var _t = core._t;
  var Model = require('web.DataModel');

  var modules = models.PosModel.prototype.models;
  var round_pr = utils.round_precision;

  for(var i=0; i<modules.length; i++){

      var model=modules[i];

      if(model.model === 'res.company'){
           model.fields.push('activity_description','street','city');
      }
      if(model.model === 'res.partner'){
           model.fields.push('document_number','activity_description','document_type_id', 'state_id', 'city_id');
      }
      if(model.model === 'pos.session'){
           model.fields.push('caf_file', 'start_number','numero_ordenes');
      }
      if (model.model == 'product.product') {
          model.fields.push('name');
      }
      if (model.model == 'res.country') {
          model.fields.push('code');
      }
  }

  models.load_models({
      model: 'res.partner',
      fields: ['document_number',],
      domain: function(self){ return [['id','=', self.company.partner_id[0]]]; },
      loaded: function(self, dn){
          self.company.document_number = dn[0].document_number;
      },
  });

  models.load_models({
      model: 'sii.document_class',
      fields: ['id', 'name', 'sii_code'],
      domain: function(self){ return [['id','=', self.config.sii_document_class_id[0]]]; },
      loaded: function(self,dc){
          self.config.sii_document_class_id = dc[0];
      },
  });

  models.load_models({
      model: 'sii.document_type',
      fields: ['id', 'name', 'sii_code'],
      loaded: function(self, dt){
          self.sii_document_types = dt;
      },
  });

  models.load_models({
      model: 'sii.activity.description',
      fields: ['id', 'name'],
      loaded: function(self, ad){
          self.sii_activities = ad;
      },
  });

  models.load_models({
      model: 'res.country.state',
      fields: ['id', 'name', 'country_id'],
      loaded: function(self, st){
          self.states = st;
      },
  });

  models.load_models({
      model: 'res.country.state.city',
      fields: ['id', 'name', 'state_id'],
      loaded: function(self, ct){
          self.cities = ct;
      },
  });

  models.load_models({
      model: 'sii.responsability',
      fields: ['id', 'name', 'tp_sii_code'],
      loaded: function(self, rs){
          self.responsabilities = rs;
      },
  });

  screens.PaymentScreenWidget.include({
    renderElement: function(parent,options) {
      var self = this;
      this._super();
      this.$('.js_boleta').click(function(){
            self.click_boleta();
        });

    },
    click_boleta: function(){
          var order = this.pos.get_order();
          var no_caf = true;
          if (this.pos.pos_session.caf_file){
            no_caf = false;
          }
          if (order.es_boleta() || no_caf) {
            order.set_boleta(false);
            this.$('.js_boleta').removeClass('highlight');
          } else {
            if(order.is_to_invoice()){
              this.click_invoice();
            }
            order.set_boleta(true);
            this.$('.js_boleta').addClass('highlight');
          }
      }
    });

  screens.ClientListScreenWidget.include({
   // what happens when we save the changes on the client edit form -> we fetch the fields, sanitize them,
   // send them to the backend for update, and call saved_client_details() when the server tells us the
   // save was successfull.
   save_client_details: function(partner) {
       var self = this;

       var fields = {};
       this.$('.client-details-contents .detail').each(function(idx,el){
           fields[el.name] = el.value;
       });

       if (!fields.name) {
           this.gui.show_popup('error',_t('A Customer Name Is Required'));
           return;
       }
       if (fields.document_number && !fields.document_type_id) {
           this.gui.show_popup('error',_t('Seleccione el tipo de documento'));
           return;
       }
       if (fields.document_number ) {
          fields.document_number = fields.document_number.toUpperCase().replace('.','').replace('.','');
          var dv = fields.document_number.charAt(fields.document_number.length-1);
          var entero = parseInt(fields.document_number.replace('-'+dv, ''));
          if (entero < 10000000 ){
            fields.document_number = '0' + entero;
          }
          var rut = '';
          for(var c = 0; c < fields.document_number.length ; c++){
            if (c === 2 || c === 5){
              rut += '.';
            }
            if (c === 8 ){
              rut += '-';
            }
            rut += fields.document_number[c];
          }
          fields.document_number = rut;
           if (!this.validar_rut(fields.document_number))
            {return;}
       }

       if (!fields.country_id) {
           this.gui.show_popup('error',_t('Seleccione el Pais'));
           return;
       }

       if (!fields.state_id) {
           this.gui.show_popup('error',_t('Seleccione la Provincia'));
           return;
       }

       if (!fields.city_id) {
           this.gui.show_popup('error',_t('Seleccione la comuna'));
           return;
       }

       if (!fields.street) {
           this.gui.show_popup('error',_t('Ingrese la direccion(calle)'));
           return;
       }

       if (this.uploaded_picture) {
           fields.image = this.uploaded_picture;
       }
       var country = _.filter(this.pos.countries, function(country){ return country.id == fields.country_id; });

       fields.id           = partner.id || false;
       fields.country_id   = fields.country_id || false;
       fields.barcode      = fields.barcode || '';
       if (country.length > 0){
        fields.vat = country[0].code + fields.document_number.replace('-','').replace('.','').replace('.','');
       }

       if (fields.activity_description && !parseInt(fields.activity_description)){
         new Model('sii.activity.description').call('create_from_ui',[fields]).then(function(description){
           fields.activity_description = description;
           new Model('res.partner').call('create_from_ui',[fields]).then(function(partner_id){
               self.saved_client_details(partner_id);
           },function(err,event){
               event.preventDefault();
               if (err.data.message) {
                self.gui.show_popup('error',{
                         'title': _t('Error: Could not Save Changes partner'),
                         'body': err.data.message,
                     });
              }else{
                self.gui.show_popup('error',{
                         'title': _t('Error: Could not Save Changes'),
                         'body': _t('Your Internet connection is probably down.'),
                     });
              }
           });
         },function(err,event){
             event.preventDefault();
             if (err.data.message) {
                self.gui.show_popup('error',{
                         'title': _t('Error: Could not Save Changes'),
                         'body': err.data.message,
                     });
              }else{
                self.gui.show_popup('error',{
                         'title': _t('Error: Could not Save Changes'),
                         'body': _t('Your Internet connection is probably down.'),
                     });
              }
            });
       }else{
         new Model('res.partner').call('create_from_ui',[fields]).then(function(partner_id){
             self.saved_client_details(partner_id);
         },function(err,event){
             event.preventDefault();
             if (err.data.message) {
              self.gui.show_popup('error',{
                       'title': _t('Error: Could not Save Changes'),
                       'body': err.data.message,
                   });
            }else{
              self.gui.show_popup('error',{
                       'title': _t('Error: Could not Save Changes'),
                       'body': _t('Your Internet connection is probably down.'),
                   });
            }
         });
       }
   },
   display_client_details: function(visibility,partner,clickpos){
       var self = this;
       this._super(visibility,partner,clickpos);
       if (visibility === "edit"){
        var state_options = self.$("select[name='state_id']:visible option:not(:first)");
        var comuna_options = self.$("select[name='city_id']:visible option:not(:first)");
        self.$("select[name='country_id']").on('change', function(){
        var select = self.$("select[name='state_id']:visible");
               var selected_state = select.val();
               state_options.detach();
               var displayed_state = state_options.filter("[data-country_id="+(self.$(this).val() || 0)+"]");
               select.val(selected_state);
               displayed_state.appendTo(select).show();
        });
        self.$("select[name='state_id']").on('change', function(){
        var select = self.$("select[name='city_id']:visible");
               var selected_comuna = select.val();
               comuna_options.detach();
               var displayed_comuna = comuna_options.filter("[data-state_id="+(self.$(this).val() || 0)+"]");
               select.val(selected_comuna);
               displayed_comuna.appendTo(select).show();
        });
        self.$("select[name='country_id']").change();
        self.$("select[name='state_id']").change();
       }
   },
   validar_rut: function(texto)
   {
      var tmpstr = "";
      for ( i=0; i < texto.length ; i++ )
        if ( texto.charAt(i) != ' ' && texto.charAt(i) != '.' && texto.charAt(i) != '-' )
          tmpstr = tmpstr + texto.charAt(i);
      texto = tmpstr;
      var largo = texto.length;

      if ( largo < 2 )
      {
        this.gui.show_popup('error',_t('Debe ingresar el rut completo'));
        return false;
      }

      for (i=0; i < largo ; i++ )
      {
        if ( texto.charAt(i) !="0" && texto.charAt(i) != "1" && texto.charAt(i) !="2" && texto.charAt(i) != "3" && texto.charAt(i) != "4" && texto.charAt(i) !="5" && texto.charAt(i) != "6" && texto.charAt(i) != "7" && texto.charAt(i) !="8" && texto.charAt(i) != "9" && texto.charAt(i) !="k" && texto.charAt(i) != "K" )
          {
          this.gui.show_popup('error',_t('El valor ingresado no corresponde a un R.U.T valido'));
          return false;
        }
      }
      var j =0;
      var invertido = "";
      for ( i=(largo-1),j=0; i>=0; i--,j++ )
        invertido = invertido + texto.charAt(i);
      var dtexto = "";
      dtexto = dtexto + invertido.charAt(0);
      dtexto = dtexto + '-';
      var cnt = 0;

      for ( i=1, j=2; i<largo; i++,j++ )
      {
        //alert("i=[" + i + "] j=[" + j +"]" );
        if ( cnt == 3 )
        {
          dtexto = dtexto + '.';
          j++;
          dtexto = dtexto + invertido.charAt(i);
          cnt = 1;
        }
        else
        {
          dtexto = dtexto + invertido.charAt(i);
          cnt++;
        }
      }

      invertido = "";
      for ( i=(dtexto.length-1),j=0; i>=0; i--,j++ )
        invertido = invertido + dtexto.charAt(i);
      if ( this.revisarDigito2(texto) )
        return true;

      return false;
    },
     revisarDigito: function( dvr )
    {
      var dv = dvr + ""
      if ( dv != '0' && dv != '1' && dv != '2' && dv != '3' && dv != '4' && dv != '5' && dv != '6' && dv != '7' && dv != '8' && dv != '9' && dv != 'k'  && dv != 'K')
      {
        this.gui.show_popup('error',_t('Debe ingresar un digito verificador valido'));
        return false;
      }
      return true;
    },
    revisarDigito2: function( crut )
    {
      var largo = crut.length;
      if ( largo < 2 )
      {
        this.gui.show_popup('error',_t('Debe ingresar el rut completo'));
        return false;
      }
      if ( largo > 2 )
        var rut = crut.substring(0, largo - 1);
      else
        var rut = crut.charAt(0);
      var dv = crut.charAt(largo-1);
      this.revisarDigito( dv );

      if ( rut == null || dv == null )
        return 0

      var dvr = '0'
      var suma = 0
      var mul  = 2

      for (i= rut.length -1 ; i >= 0; i--)
      {
        suma = suma + rut.charAt(i) * mul
        if (mul == 7)
          mul = 2
        else
          mul++
      }
      var res = suma % 11
      if (res==1)
        dvr = 'k'
      else if (res==0)
        dvr = '0'
      else
      {
        var dvi = 11-res
        dvr = dvi + ""
      }
      if ( dvr != dv.toLowerCase() )
      {
        this.gui.show_popup('error',_t('EL rut es incorrecto'));
        return false
      }

      return true
    },

  });

  var PosModelSuper = models.PosModel.prototype.push_order;
  models.PosModel.prototype.push_order = function(order, opts) {
        if(order && order.es_boleta()){
          var orden_numero = order.orden_numero -1;
          var caf_files = JSON.parse(this.pos_session.caf_file);
          var start_caf_file = false;
          for (var x in caf_files){
            if(parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D) <= parseInt(this.pos_session.start_number)
                && parseInt(this.pos_session.start_number) <= parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H)){
              start_caf_file = caf_files[x];
            }
          }
          var start_number = this.pos_session.start_number;
          var get_next_number = function(sii_document_number){
            var caf_file = false;
            var gived = 0;
            for (var x in caf_files){
              if(parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D) <= sii_document_number &&
                sii_document_number >= parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H)){
                caf_file = caf_files[x];
              }else if( !caf_file ||
                ( sii_document_number < parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D) &&
                sii_document_number < parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) &&
                parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) < parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D)
              )){//menor de los superiores caf
                caf_file = caf_files[x];
              }
              if (sii_document_number > parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H) && caf_files[x] != start_caf_file){
                gived += (parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H) - parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D)) +1;
              }
            }
            if (!caf_file){
              return sii_document_number;
            }
            if(sii_document_number < parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D)){
              var dif = orden_numero - ((parseInt(start_caf_file.AUTORIZACION.CAF.DA.RNG.H) - start_number) + 1 + gived);
              sii_document_number = parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) + dif;
              if (sii_document_number >  parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.H)){
                sii_document_number = get_next_number(sii_document_number);
              }
            }
            return sii_document_number;
          }
          var sii_document_number = get_next_number(parseInt(orden_numero) + parseInt(start_number));

          order.sii_document_number = sii_document_number;
          var amount = Math.round(order.get_total_with_tax());
          if (amount > 0){
            order.signature = order.timbrar(order);
          }
        }
        return PosModelSuper.call(this, order, opts);
  };

  var _super_order = models.Order.prototype;
  models.Order = models.Order.extend({
    initialize: function(attr, options) {
          _super_order.initialize.call(this,attr,options);
          this.set_boleta(false);
          if (this.pos.config.marcar === 'boleta'){
            if (this.pos.pos_session.caf_file){
              this.set_boleta(true);
            }
          }else if (this.pos.config.marcar === 'factura'){
            this.set_to_invoice(true);
          }
          this.signature = this.signature || false;
          this.sii_document_number = this.sii_document_number || false;
          this.orden_numero = this.orden_numero || this.pos.pos_session.numero_ordenes;
    },
    export_as_JSON: function() {
         var json = _super_order.export_as_JSON.apply(this,arguments);
         json.sii_document_number = this.sii_document_number;
         json.signature = this.signature;
         json.orden_numero = this.orden_numero;
         return json;
    },
    init_from_JSON: function(json) {//carga pedido individual
          _super_order.init_from_JSON.apply(this,arguments);
          this.sii_document_number = json.sii_document_number;
          this.signature = json.signature;
          this.orden_numero = json.orden_numero;
    },
    export_for_printing: function() {
          var json = _super_order.export_for_printing.apply(this,arguments);
          json.company.document_number = this.pos.company.document_number;
          json.company.activity_description = this.pos.company.activity_description[1];
          json.company.street = this.pos.company.street;
          json.company.city = this.pos.company.city;
          json.sii_document_number = this.sii_document_number;
          json.orden_numero = this.orden_numero;
          json.journal_document_class_id = this.pos.config.journal_document_class_id[1];
            var d = this.creation_date;
           var curr_date = this.completa_cero(d.getDate());
           var curr_month = this.completa_cero(d.getMonth() + 1); //Months are zero based
           var curr_year = d.getFullYear();
           var hours = d.getHours();
           var minutes = d.getMinutes();
           var seconds = d.getSeconds();
           var date = curr_year + '-' + curr_month + '-' + curr_date + ' ' +
                     this.completa_cero(hours) + ':' + this.completa_cero(minutes) + ':' + this.completa_cero(seconds);
          json.creation_date = date;
          json.barcode = this.barcode_pdf417();
          json.exento = this.get_total_exento();
          json.referencias = [];
          json.client = this.get('client');
          return json;
      },
    initialize_validation_date: function(){
        _super_order.initialize_validation_date.apply(this,arguments);
        if (!this.is_to_invoice() && this.es_boleta())
        {
          this.pos.pos_session.numero_ordenes ++;
          this.orden_numero = this.pos.pos_session.numero_ordenes;
        }
    },
    get_total_with_tax: function() {
      _super_order.get_total_with_tax.apply(this,arguments);
      return round_pr(this.orderlines.reduce((function(sum, orderLine) {
          return sum + orderLine.get_price_with_tax();
      }), 0), this.pos.currency.rounding);
    },
    set_to_invoice: function(){
      _super_order.set_to_invoice.apply(this,arguments);
      this.set_boleta(!this.is_to_invoice());
    },
    set_boleta: function(boleta){
      this.boleta = boleta;
    },
    es_boleta: function(){
      return this.boleta;
    },
    get_total_exento:function(){
      var taxes =  this.pos.taxes;
      var exento = 0;

      this.orderlines.each(function(line){
        var product =  line.get_product();
        var taxes_ids = product.taxes_id;
        _(taxes_ids).each(function(el){
              _.detect(taxes,function(t){
                  if(t.id === el && t.amount === 0){
                    exento += (line.get_unit_price() * line.get_quantity());
                  }
              });
          });
      });
      return exento;
    },
    completa_cero(val){
        if (parseInt(val) < 10){
            return '0' + val;
        }
          return val;
    },
    encode: function(caracter){
        var string = ""
        for (var i=0; i< caracter.length; i++){
          var l = caracter[i];
          if(l.charCodeAt() >= 160)
          {
            l = "&#"+ l.charCodeAt()+';';
          }
          if(i < 40)
          {
            string += l;
          }
        }
        return string;
      },
      timbrar: function(order){
          if (order.signature){ //no firmar otra vez
            return order.signature;
          }
          var caf_files = JSON.parse(this.pos.pos_session.caf_file);
          var caf_file = false;
          for (var x in caf_files){
            if(caf_files[x].AUTORIZACION.CAF.DA.RNG.D <= order.sii_document_number && order.sii_document_number <= caf_files[x].AUTORIZACION.CAF.DA.RNG.H){
              caf_file =caf_files[x]
            }
          }
          if (!caf_file){
            this.pos.gui.show_popup('error',_t('No quedan más Folios Disponibles'));
            return false;
          }
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
         var product_name = false;
         var ols = order.orderlines.models;
         var ols2 = ols;
         for (var p in ols){
           var es_menor = true;
           for(var i in ols2){
             if(ols[p].id !== ols2[i].id && ols[p].id > ols2[i].id){
               es_menor = false;
             }
             if(es_menor === true){
               product_name = this.encode(ols[p].product.name);
             }
           }
         }
         var d = order.validation_date;
          var curr_date = this.completa_cero(d.getDate());
          var curr_month = this.completa_cero(d.getMonth() + 1); //Months are zero based
          var curr_year = d.getFullYear();
          var hours = d.getHours();
          var minutes = d.getMinutes();
          var seconds = d.getSeconds();
          var date = curr_year + '-' + curr_month + '-' + curr_date + 'T' +
                    this.completa_cero(hours) + ':' + this.completa_cero(minutes) + ':' + this.completa_cero(seconds);
          var rut_emisor = this.pos.company.document_number.replace('.','').replace('.','');
          if (rut_emisor.charAt(0) == "0"){
            rut_emisor = rut_emisor.substr(1);
          }
          var string='<DD>' +
                '<RE>' + rut_emisor + '</RE>' +
                '<TD>' + this.pos.config.sii_document_class_id.sii_code + '</TD>' +
                '<F>' + order.sii_document_number + '</F>' +
                '<FE>' + curr_year + '-' + curr_month + '-' + curr_date + '</FE>' +
                '<RR>' + partner_id.document_number.replace('.','').replace('.','') +'</RR>' +
                '<RSR>' + this.encode(partner_id.name) + '</RSR>' +
                '<MNT>' + Math.round(this.get_total_with_tax()) + '</MNT>' +
                '<IT1>' + product_name + '</IT1>' +
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
        var order = this.pos.get_order();
        if (!this.pos.pos_session.caf_file || !order.sii_document_number){
          return false;
        }
        PDF417.init(order.signature, 5, 1);
        var barcode = PDF417.getBarcodeArray();
        var bw = 2;
        var bh = 2;
        var canvas = document.createElement('canvas');
        canvas.width = bw * barcode['num_cols'];
        canvas.height = 255;
        var ctx = canvas.getContext('2d');
        ctx.scale(1,0.9);
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

var _super_screen = PosBaseWidget.prototype;
PosBaseWidget.render_receipt = function() {
        var order = this.pos.get_order();
        if (order.to_invoice)
        {
          this.$('.pos-receipt-container').html(QWeb.render('PosInvoice',{
                  widget:this,
                  order: order,
                  receipt: order.export_for_printing(),
                  orderlines: order.get_orderlines(),
                  paymentlines: order.get_paymentlines(),
              }));

        }else{
          _super_screen.render_receipt();
        }
    };
});
