odoo.define('l10n_cl_dte_point_of_sale.screens', function (require) {
"use strict";

var screens = require('point_of_sale.screens');
var core = require('web.core');
var QWeb = core.qweb;
var _t = core._t;
var rpc = require('web.rpc');

screens.PaymentScreenWidget.include({
	renderElement: function(parent,options) {
		var self = this;
		this._super();
		this.$('.js_boleta').click(function(){
			self.click_boleta();
		});
		this.$('.js_boleta_exenta').click(function(){
			self.click_boleta_exenta();
		});
	},
	order_is_valid: function(force_validation) {
		var self = this;
		var res = this._super(force_validation);
		var order = self.pos.get_order();
		if (order.is_to_invoice() || order.es_boleta()){
		      var total_tax = order.get_total_tax();
		      if (order.es_boleta_exenta() && total_tax > 0){// @TODO agrregar facturas exentas
		        this.gui.show_popup('error',{
		        	'title': "Error de integridad",
		        	'body': "No pueden haber productos afectos en boleta/factura exenta",
		        });
				return false;
		      }else if(!order.es_boleta_exenta() && total_tax <= 0 && order.get_total_exento() > 0){
		        this.gui.show_popup('error',{
		        	'title': "Error de integridad",
		        	'body': "Debe haber almenos un producto afecto",
		      	});
				return false;
		    };
		};
		if (order.is_to_invoice() && order.get_client()) {
			var client = order.get_client();
			if (!client.street){
				this.gui.show_popup('error',{
					'title': 'Datos de Cliente Incompletos',
					'body':  'El Cliente seleccionado no tiene la direccion, por favor verifique',
				});
				return false;
			}
			if (!client.document_number){
				this.gui.show_popup('error',{
					'title': 'Datos de Cliente Incompletos',
					'body':  'El Cliente seleccionado no tiene RUT, por favor verifique',
				});
				return false;
			}
			if (!client.activity_description){
				this.gui.show_popup('error',{
					'title': 'Datos de Cliente Incompletos',
					'body':  'El Cliente seleccionado no tiene Giro, por favor verifique',
				});
				return false;
			}
		}
		if (res && Math.abs(order.get_total_with_tax() <= 0)) {
			this.gui.show_popup('error',{
				'title': 'Orden con total 0',
				'body':  'No puede emitir Pedidos con total 0, por favor asegurese que agrego lineas y que el precio es mayor a cero',
			});
			return false;
		}
		if (res && !order.is_to_invoice() && order.es_boleta()){
			var start_number = 0;
			var numero_ordenes = 0;
			if (order.es_boleta_afecta()){
				start_number = self.pos.pos_session.start_number;
				numero_ordenes = self.pos.pos_session.numero_ordenes;
			} else if (order.es_boleta_exenta()){
				start_number = self.pos.pos_session.start_number_exentas;
				numero_ordenes = self.pos.pos_session.numero_ordenes_exentas;
			}
			var caf_files = JSON.parse(order.sequence_id.caf_files);
			var next_number = start_number + numero_ordenes;
			next_number = self.pos.get_next_number(next_number, caf_files, start_number);
			var caf_file = false;
			for (var x in caf_files){
				if(next_number >= caf_files[x].AUTORIZACION.CAF.DA.RNG.D && next_number <= caf_files[x].AUTORIZACION.CAF.DA.RNG.H){
					caf_file =caf_files[x]
				}
			}
			//validar que el numero emitido no supere el maximo del folio
			if (!caf_file){
				self.pos.gui.show_popup('error',{
	        		'title': "Sin Folios disponibles",
	                'body':  _.str.sprintf("No hay CAF para el folio de este documento: %(document_number)s " +
	              		  "Solicite un nuevo CAF en el sitio www.sii.cl", {
	                			document_number: next_number,
	              		  })
	            });
				return false;
	        }
		}
		return res;
	},
	unset_boleta:function(order){
		order.unset_boleta();
		this.$('.js_boleta').removeClass('highlight');
		this.$('.js_boleta_exenta').removeClass('highlight');
	},
	click_boleta: function(){
		var order = this.pos.get_order();
		order.set_to_invoice(false);
		this.$('.js_invoice').removeClass('highlight');
		if (this.pos.pos_session.caf_files && (order.es_boleta_exenta() || !order.es_boleta())) {
			this.unset_boleta(order);
			order.set_boleta(true);
			order.set_tipo_boleta(this.pos.config.secuencia_boleta);
			this.$('.js_boleta').addClass('highlight');
			return;
		}
		this.unset_boleta(order);
	},
	click_boleta_exenta: function(){
		var order = this.pos.get_order();
		order.set_to_invoice(false);
		this.$('.js_invoice').removeClass('highlight');
		if (this.pos.pos_session.caf_files_exentas && !order.es_boleta_exenta()){
			this.unset_boleta(order);
			order.set_boleta(true);
			order.set_tipo_boleta(this.pos.config.secuencia_boleta_exenta);
			this.$('.js_boleta_exenta').addClass('highlight');
			return;
		}
		this.unset_boleta(order);
	},
	click_invoice: function(){
		var order = this.pos.get_order();
		this.unset_boleta(order);
		var res = this._super();
	},
});

screens.ClientListScreenWidget.include({
	//what happens when we save the changes on the client edit form -> we fetch
	//the fields, sanitize them,
	//send them to the backend for update, and call saved_client_details() when
	//the server tells us the
	//save was successfull.
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
			if (!this.validar_rut(fields.document_number)){
				return;
			}
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
		if (fields.property_product_pricelist) {
			fields.property_product_pricelist = parseInt(fields.property_product_pricelist, 10);
        } else {
        	fields.property_product_pricelist = false;
        }
		if (fields.activity_description && !parseInt(fields.activity_description)){
			rpc.query({
				model:'sii.activity.description',
				method:'create_from_ui',
				args: [fields]
            }).then(function(description){
            	fields.activity_description = description;
                rpc.query({
                	model:'res.partner',
                	method: 'create_from_ui',
                	args: [fields]
                }).then(function(partner_id){
                      	self.saved_client_details(partner_id);
                }, function(err_type, err){
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
            }, function(err_type, err){
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
			rpc.query({
				model: 'res.partner',
				method: 'create_from_ui',
				args: [fields]
			}).then(function(partner_id){
				self.saved_client_details(partner_id);
			}, function(err_type, err){
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
	display_client_details: function(visibility, partner, clickpos){
		var self = this;
		this._super(visibility, partner, clickpos);
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
			self.$("select[name='city_id']").on('change', function(){
        		var city_id = self.$(this).val() || 0;
        		if (city_id > 0){
        			var city = self.pos.cities_by_id[city_id];
        			var select_country = self.$("select[name='country_id']:visible");
        			select_country.val(city.country_id ? city.country_id[0] : 0);
        			select_country.change();
        			var select_state = self.$("select[name='state_id']:visible");
        			select_state.val(city.state_id ? city.state_id[0] : 0);
        		}
        	});
			self.$(".client-document_number").on('change', function(){
				var document_number = self.$(this).val() || '';
				document_number = document_number.replace(/[^1234567890Kk]/g, "");
				document_number = _.str.lpad(document_number, 9, '0');
				document_number = _.str.sprintf('%s.%s.%s-%s',
					document_number.slice(0, 2),
    				document_number.slice(2, 5),
    				document_number.slice(5, 8),
    				document_number.slice(-1))
    			self.$(this).val(document_number);
			});
			self.$("select[name='country_id']").change();
		}
	},
	validar_rut: function(texto){
		var tmpstr = "";
		var i = 0;
		for ( i=0; i < texto.length ; i++ ){
			if ( texto.charAt(i) != ' ' && texto.charAt(i) != '.' && texto.charAt(i) != '-' ){
				tmpstr = tmpstr + texto.charAt(i);
			}
		}
		texto = tmpstr;
		var largo = texto.length;
		if ( largo < 2 ){
			this.gui.show_popup('error',_t('Debe ingresar el rut completo'));
			return false;
		}
		for (i=0; i < largo ; i++ ){
			if ( texto.charAt(i) !="0" && texto.charAt(i) != "1" && texto.charAt(i) !="2" && texto.charAt(i) != "3" && texto.charAt(i) != "4" && texto.charAt(i) !="5" && texto.charAt(i) != "6" && texto.charAt(i) != "7" && texto.charAt(i) !="8" && texto.charAt(i) != "9" && texto.charAt(i) !="k" && texto.charAt(i) != "K" ){
				this.gui.show_popup('error',_t('El valor ingresado no corresponde a un R.U.T valido'));
				return false;
			}
		}
		var j =0;
		var invertido = "";
		for ( i=(largo-1),j=0; i>=0; i--,j++ ){
			invertido = invertido + texto.charAt(i);
		}
		var dtexto = "";
		dtexto = dtexto + invertido.charAt(0);
		dtexto = dtexto + '-';
		var cnt = 0;

		for ( i=1, j=2; i<largo; i++,j++ ){
			// alert("i=[" + i + "] j=[" + j +"]" );
			if ( cnt == 3 ){
				dtexto = dtexto + '.';
				j++;
				dtexto = dtexto + invertido.charAt(i);
				cnt = 1;
			}else{
				dtexto = dtexto + invertido.charAt(i);
				cnt++;
			}
		}

		invertido = "";
		for ( i=(dtexto.length-1),j=0; i>=0; i--,j++ ){
			invertido = invertido + dtexto.charAt(i);
		}
		if ( this.revisarDigito2(texto) ){
			return true;
		}
		return false;
	},
	revisarDigito: function( dvr ){
		var dv = dvr + ""
		if ( dv != '0' && dv != '1' && dv != '2' && dv != '3' && dv != '4' && dv != '5' && dv != '6' && dv != '7' && dv != '8' && dv != '9' && dv != 'k'  && dv != 'K'){
			this.gui.show_popup('error',_t('Debe ingresar un digito verificador valido'));
			return false;
		}
		return true;
	},
	revisarDigito2: function( crut ){
		var largo = crut.length;
		if ( largo < 2 ){
			this.gui.show_popup('error',_t('Debe ingresar el rut completo'));
			return false;
		}
		if ( largo > 2 ){
			var rut = crut.substring(0, largo - 1);
		}else{
			var rut = crut.charAt(0);
		}
		var dv = crut.charAt(largo-1);
		this.revisarDigito( dv );

		if ( rut == null || dv == null ){
			return 0
		}

		var dvr = '0';
		var suma = 0;
		var mul = 2;
		var i = 0;
		for (i= rut.length -1 ; i >= 0; i--){
			suma = suma + rut.charAt(i) * mul;
			if (mul == 7){
				mul = 2;
			}else{
				mul++;
			}
		}
		var res = suma % 11;
		if (res==1){
			dvr = 'k';
		} else if (res==0){
			dvr = '0';
		} else{
			var dvi = 11-res;
			dvr = dvi + "";
		}
		if ( dvr != dv.toLowerCase()){
			this.gui.show_popup('error',_t('EL rut es incorrecto'));
			return false;
		}
		return true;
	},
});

screens.ReceiptScreenWidget.include({
	render_receipt: function() {
		var order = this.pos.get_order();
        if (order.to_invoice){
        	this.$('.pos-receipt-container').html(QWeb.render('PosInvoice', this.get_receipt_render_env()));
        }else{
        	this._super();
        }
	}
});
});
