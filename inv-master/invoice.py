# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning, UserError
from odoo import http
from pprint import pprint
import time
from datetime import datetime
import hmac
import hashlib
import requests 
import json
import os
from odoo.http import request
from decimal import Decimal
import qrcode
import base64
from io import BytesIO

from sunatservice.sunatservice import Service


class account_invoice(models.Model):

    _inherit = 'account.invoice'
    
    #diario = fields.Selection([('factura','Factura'),('boleta','Boleta'),('creadito','Nota Crédito'),('debito','Nota Débito')], string='Diario', default='factura')
    api_message = fields.Text(name="api_message", string="Estado", default='Documento contable sin emitir.')
    discrepance_code = fields.Text(name="discrepance_code", default='')
    discrepance_text = fields.Text(name="discrepance_text", string="Discrepancia", default='')
    

    #_columns = { 'api_message': fields.Text('Estado'), 'diario':fields.Selection([('factura','Factura'),('boleta','Boleta'),('creadito','Nota Crédito'),('debito','Nota Débito')], string='Diario')}
    _columns = { 'api_message': fields.Text('Estado'),'discrepance': fields.Text('Discrepancia')}
    _defaults = {'api_message':'Documento contable sin emitir.','diario':'factura','discrepance':''}

    qr_image = fields.Text(name="qr_image", default='')  
    qr_in_report = fields.Boolean('Ver QR en reporte')


    @api.multi
    def invoice_validate(self):
        
        urlPath = http.request.httprequest.full_path
        if 'payment/process' in urlPath:
            return super(account_invoice, self).invoice_validate()



        #FOR INVOICES
        invoice_items = []
        total_venta_gravada = 0.0
        total_venta = 0.0
        
        sumatoria_igv = 0.0
        sumatoria_igv_impuesto = 0.0
        total_venta_igv = 0.0
    
        sumatoria_isc = 0.0
        sumatoria_isc_impuesto = 0.0
        total_venta_ics = 0.0            
    
        sumatoria_inafecto = 0.0
        sumatoria_inafecto_impuesto = 0.0
        total_venta_inafecto = 0.0

        sumatoria_gratuita = 0.0
        sumatoria_gratuita_impuesto = 0.0
        total_venta_gratuita = 0.0

        sumatoria_exonerada = 0.0
        sumatoria_exonerada_impuesto = 0.0
        total_venta_exonerada = 0.0

        sumatoria_exportacion = 0.0
        sumatoria_exportacion_impuesto = 0.0
        total_venta_exportacion = 0.0

        sumatoria_other = 0.0
        sumatoria_other_impuesto = 0.0
        total_venta_other = 0.0

        tipoAfectacionTributo = 0
        tipoAfectacionISC = 0

        #if '/web/dataset/call_kw/pos.order/create_from_ui?' in urlPath:
        #    return super(account_invoice, self).invoice_validate()

        for invoice in self: 
            if invoice.partner_id.vat=="" or invoice.partner_id.vat==False:
               raise Warning(_("Por favor digitar el RUC del receptor"))

        tipo_documento_consultar = self.journal_id.code

        if(tipo_documento_consultar=="NCR"):
            index = 0
            total_venta = 0
            for invoice in self:            
                items = invoice.invoice_line_ids
                for item in items:
                    tax_line = False
                    for tax in item.invoice_line_tax_ids:
                           tax_line = tax   

                    impuesto = tax_line.amount/100
                    valor_venta = (item.price_unit * item.quantity)                        
                    monto_afectacion_tributo = valor_venta * impuesto    
                    precio_unitario = (item.price_unit * impuesto) + item.price_unit                                                          
                    
                    if(str(int(tax_line.sunat_tributo))=="1000"):
                        sumatoria_igv += monto_afectacion_tributo
                        sumatoria_igv_impuesto += impuesto
                        total_venta_igv += valor_venta
                        total_venta += total_venta_igv
                        tipoAfectacionTributo = "10"

                    if(str(int(tax_line.sunat_tributo))=="2000"):
                        sumatoria_isc += monto_afectacion_tributo
                        sumatoria_isc_impuesto += impuesto
                        total_venta_ics += valor_venta
                        total_venta += total_venta_ics
                        tipoAfectacionTributo = "01" # catalogo 8
                        
                    if(str(int(tax_line.sunat_tributo))=="9998"):
                        sumatoria_inafecto += monto_afectacion_tributo
                        sumatoria_inafecto_impuesto += impuesto
                        total_venta_inafecto += valor_venta
                        total_venta += total_venta_inafecto
                        tipoAfectacionTributo = "30"

                    if(str(int(tax_line.sunat_tributo))=="9996"):
                        sumatoria_gratuita += monto_afectacion_tributo
                        sumatoria_gratuita_impuesto += impuesto
                        total_venta_gratuita += valor_venta
                        total_venta += total_venta_gratuita
                        tipoAfectacionTributo = "21"
                    
                    if(str(int(tax_line.sunat_tributo))=="9997"):
                        sumatoria_exonerada += monto_afectacion_tributo
                        sumatoria_exonerada_impuesto += impuesto
                        total_venta_exonerada += valor_venta
                        total_venta += total_venta_exonerada
                        tipoAfectacionTributo = "20"
                    
                    if(str(int(tax_line.sunat_tributo))=="9995"):
                        sumatoria_exportacion += monto_afectacion_tributo
                        sumatoria_exportacion_impuesto += impuesto
                        total_venta_exportacion += valor_venta
                        total_venta += total_venta_exportacion
                        tipoAfectacionTributo = "40"

                    if(str(int(tax_line.sunat_tributo))=="9999"):
                        sumatoria_other += monto_afectacion_tributo
                        sumatoria_other_impuesto += impuesto
                        total_venta_other += valor_venta
                        total_venta += total_venta_other
                        tipoAfectacionTributo = "10"
                    
                    invoice_item = {
                                        'id':str(item.id),
                                        'cantidad':str(item.quantity),
                                        'descripcion':item.name, 
                                        'valorVenta':valor_venta, 
                                        'valorUnitario':item.price_unit, 
                                        'precioVentaUnitario':precio_unitario, 
                                        'tipoPrecioVentaUnitario':'01',  #instalar en ficha de producto catalogo 16                                            
                                        "tributo":{
                                                    "codigo":str(int(tax_line.sunat_tributo)),
                                                    "porcentaje": tax_line.amount,#taxes.tax_id.amount,
                                                    'montoAfectacionTributo':monto_afectacion_tributo, 
                                                    'tipoAfectacionTributo': tipoAfectacionTributo, # pendiente si es igv - catalogo 7. 
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                                  },                                                
                                        'unidadMedidaCantidad':"ZZ",
                                    }
                    invoice_items.append(invoice_item)  

            serieParts = str(invoice.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")
            #end for

            data = {
                    'serie': str(serieConsecutivoString),
                    "numero":str(serieConsecutivo),
                    "emisor":{
                                "tipo":6,
                                "nro":invoice.company_id.sol_ruc,
                                "nombre":invoice.company_id.name,
                                "direccion":invoice.company_id.street,
                                "ciudad":invoice.company_id.city,
                                "departamento":invoice.company_id.state_id.name,
                                "codigoPostal":invoice.company_id.zip,
                                "codigoPais":invoice.company_id.country_id.code,
                                "ubigeo":invoice.company_id.ubigeo
                             },
                    "receptor": {
                                    "tipo": 6,
                                    "nro": invoice.partner_id.vat,
                                    "nombre":invoice.partner_id.name,
                                    "direccion":invoice.partner_id.street,
                                },
                    "tributo":{
                                'IGV': {"total_venta":str(round(float(total_venta_igv),2)), "impuesto":str(round(float(sumatoria_igv_impuesto),2)), "sumatoria":str(round(float(sumatoria_igv),2))},
                                'ISC': {"total_venta":str(round(float(total_venta_ics),2)), "impuesto":str(round(float(sumatoria_isc_impuesto),2)), "sumatoria":str(round(float(sumatoria_isc),2))},
                                'inafecto': {"total_venta":str(round(float(total_venta_inafecto),2)), "impuesto":str(round(float(sumatoria_inafecto_impuesto),2)), "sumatoria":str(round(float(sumatoria_inafecto),2))},
                                'exonerado': {"total_venta":str(round(float(total_venta_exonerada),2)), "impuesto":str(round(float(sumatoria_exonerada_impuesto),2)), "sumatoria":str(round(float(sumatoria_exonerada),2))},
                                'exportacion': {"total_venta":str(round(float(total_venta_exportacion),2)), "impuesto":str(round(float(sumatoria_exportacion_impuesto),2)), "sumatoria":str(round(float(sumatoria_exportacion),2))},
                                'other': {"total_venta":str(round(float(total_venta_other),2)), "impuesto":str(round(float(sumatoria_other_impuesto),2)), "sumatoria":str(round(float(sumatoria_other),2))},
                               },
                    "notaDescripcion":self.name,
                    "notaDiscrepanciaCode":self.discrepance_code,
                    "documentoOrigen":self.origin,
                    "documentoOrigenTipo": str("01"), #01 factura, 03 boleta, 12 tiket de venta
                    "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                    "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                    "horaEmision":currentTime,                    
                    'totalVenta': total_venta,
                    'tipoMoneda': invoice.currency_id.name,
                    'items':invoice_items,
                    'sol':{
                            'usuario':invoice.company_id.sol_username,
                            'clave':invoice.company_id.sol_password
                          },
                    'licencia':"081OHTGAVHJZ4GOZJGJV"
                    } 
            #
            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.sol_ruc)+"-07-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            sunatResponse = SunatService.processCreditNote(data)

            #with open('/home/rockscripts/Documents/data1.json', 'w') as outfile:
            #    json.dump(data, outfile)
                        
            if(sunatResponse["status"] == "OK"):
                # generate qr for invoices and tickets in pos
                base_url = request.env['ir.config_parameter'].get_param('web.base.url')
                base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
                qr = qrcode.QRCode(
                                    version=1,
                                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                                    box_size=20,
                                    border=4,
                                  )
                qr.add_data(base_url)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                self.qr_image = base64.b64encode(temp.getvalue())
                self.qr_in_report = True

                self.api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"]["description"])
                return super(account_invoice, self).invoice_validate()
            else:
                errorMessage = "ESTADO: "+str(sunatResponse["status"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"])
                raise Warning(errorMessage)
            
            

        elif(tipo_documento_consultar=="NDB"):
            index = 0
            total_venta = 0
            for invoice in self:            
                items = invoice.invoice_line_ids
                for item in items:
                    tax_line = False
                    for tax in item.invoice_line_tax_ids:
                           tax_line = tax   

                    impuesto = tax_line.amount/100
                    valor_venta = (item.price_unit * item.quantity)                        
                    monto_afectacion_tributo = valor_venta * impuesto    
                    precio_unitario = (item.price_unit * impuesto) + item.price_unit                                                          
                    
                    if(str(int(tax_line.sunat_tributo))=="1000"):
                        sumatoria_igv += monto_afectacion_tributo
                        sumatoria_igv_impuesto += impuesto
                        total_venta_igv += valor_venta
                        total_venta += total_venta_igv
                        tipoAfectacionTributo = "10"

                    if(str(int(tax_line.sunat_tributo))=="2000"):
                        sumatoria_isc += monto_afectacion_tributo
                        sumatoria_isc_impuesto += impuesto
                        total_venta_ics += valor_venta
                        total_venta += total_venta_ics
                        tipoAfectacionTributo = "01" # catalogo 8
                        
                    if(str(int(tax_line.sunat_tributo))=="9998"):
                        sumatoria_inafecto += monto_afectacion_tributo
                        sumatoria_inafecto_impuesto += impuesto
                        total_venta_inafecto += valor_venta
                        total_venta += total_venta_inafecto
                        tipoAfectacionTributo = "30"

                    if(str(int(tax_line.sunat_tributo))=="9996"):
                        sumatoria_gratuita += monto_afectacion_tributo
                        sumatoria_gratuita_impuesto += impuesto
                        total_venta_gratuita += valor_venta
                        total_venta += total_venta_gratuita
                        tipoAfectacionTributo = "21"
                    
                    if(str(int(tax_line.sunat_tributo))=="9997"):
                        sumatoria_exonerada += monto_afectacion_tributo
                        sumatoria_exonerada_impuesto += impuesto
                        total_venta_exonerada += valor_venta
                        total_venta += total_venta_exonerada
                        tipoAfectacionTributo = "20"
                    
                    if(str(int(tax_line.sunat_tributo))=="9995"):
                        sumatoria_exportacion += monto_afectacion_tributo
                        sumatoria_exportacion_impuesto += impuesto
                        total_venta += sumatoria_exportacion_impuesto
                        tipoAfectacionTributo = "40"

                    if(str(int(tax_line.sunat_tributo))=="9999"):
                        sumatoria_other += monto_afectacion_tributo
                        sumatoria_other_impuesto += impuesto
                        total_venta_other += valor_venta
                        total_venta += total_venta_other
                        tipoAfectacionTributo = "10"
                    
                    invoice_item = {
                                        'id':str(item.id),
                                        'cantidad':str(item.quantity),
                                        'descripcion':item.name, 
                                        'valorVenta':valor_venta, 
                                        'valorUnitario':item.price_unit, 
                                        'precioVentaUnitario':precio_unitario, 
                                        'tipoPrecioVentaUnitario':'01',  #instalar en ficha de producto catalogo 16                                            
                                        "tributo":{
                                                    "codigo":str(int(tax_line.sunat_tributo)),
                                                    "porcentaje": tax_line.amount,#taxes.tax_id.amount,
                                                    'montoAfectacionTributo':monto_afectacion_tributo, 
                                                    'tipoAfectacionTributo': tipoAfectacionTributo, # pendiente si es igv - catalogo 7. 
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                                  },                                                
                                        'unidadMedidaCantidad':"ZZ",
                                    }
                    invoice_items.append(invoice_item)  

            serieParts = str(invoice.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")
            #end for

            data = {
                    'serie': str(serieConsecutivoString),
                    "numero":str(serieConsecutivo),
                    "emisor":{
                                "tipo":6,
                                "nro":invoice.company_id.sol_ruc,
                                "nombre":invoice.company_id.name,
                                "direccion":invoice.company_id.street,
                                "ciudad":invoice.company_id.city,
                                "departamento":invoice.company_id.state_id.name,
                                "codigoPostal":invoice.company_id.zip,
                                "codigoPais":invoice.company_id.country_id.code,
                                "ubigeo":invoice.company_id.ubigeo
                             },
                    "receptor": {
                                    "tipo": 6,
                                    "nro": invoice.partner_id.vat,
                                    "nombre":invoice.partner_id.name,
                                    "direccion":invoice.partner_id.street,
                                },
                    "tributo":{
                                'IGV': {"total_venta":str(round(float(total_venta_igv),2)), "impuesto":str(round(float(sumatoria_igv_impuesto),2)), "sumatoria":str(round(float(sumatoria_igv),2))},
                                'ISC': {"total_venta":str(round(float(total_venta_ics),2)), "impuesto":str(round(float(sumatoria_isc_impuesto),2)), "sumatoria":str(round(float(sumatoria_isc),2))},
                                'inafecto': {"total_venta":str(round(float(total_venta_inafecto),2)), "impuesto":str(round(float(sumatoria_inafecto_impuesto),2)), "sumatoria":str(round(float(sumatoria_inafecto),2))},
                                'exonerado': {"total_venta":str(round(float(total_venta_exonerada),2)), "impuesto":str(round(float(sumatoria_exonerada_impuesto),2)), "sumatoria":str(round(float(sumatoria_exonerada),2))},
                                'exportacion': {"total_venta":str(round(float(total_venta_exportacion),2)), "impuesto":str(round(float(sumatoria_exportacion_impuesto),2)), "sumatoria":str(round(float(sumatoria_exportacion),2))},
                                'other': {"total_venta":str(round(float(total_venta_other),2)), "impuesto":str(round(float(sumatoria_other_impuesto),2)), "sumatoria":str(round(float(sumatoria_other),2))},
                               },
                    "notaDescripcion":self.name,
                    "notaDiscrepanciaCode":self.discrepance_code,
                    "documentoOrigen":self.origin,
                    "documentoOrigenTipo": str("01"), #01 factura, 03 boleta, 12 tiket de venta
                    "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                    "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                    "horaEmision":currentTime,                    
                    'totalVenta': total_venta,
                    'tipoMoneda': invoice.currency_id.name,
                    'items':invoice_items,
                    'sol':{
                            'usuario':invoice.company_id.sol_username,
                            'clave':invoice.company_id.sol_password
                          },
                    'licencia':"081OHTGAVHJZ4GOZJGJV"
                    }            
            
            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.sol_ruc)+"-08-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            sunatResponse = SunatService.processDebitNote(data)

            #with open('/home/rockscripts/Documents/data1.json', 'w') as outfile:
            #    json.dump(sunatResponse, outfile)
                        
            if(sunatResponse["status"] == "OK"):
                # generate qr for invoices and tickets in pos
                base_url = request.env['ir.config_parameter'].get_param('web.base.url')
                base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
                qr = qrcode.QRCode(
                                    version=1,
                                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                                    box_size=20,
                                    border=4,
                                  )
                qr.add_data(base_url)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                self.qr_image = base64.b64encode(temp.getvalue())
                self.qr_in_report = True
                
                self.api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"]["description"])
                return super(account_invoice, self).invoice_validate()
            else:
                errorMessage = "ESTADO: "+str(sunatResponse["status"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"])
                raise Warning(errorMessage)
            

        elif(tipo_documento_consultar=="BOL"):            
            index = 0
            total_venta = 0
            for invoice in self:            
                items = invoice.invoice_line_ids
                for item in items:
                    tax_line = False
                    for tax in item.invoice_line_tax_ids:
                           tax_line = tax   

                    impuesto = tax_line.amount/100
                    valor_venta = (item.price_unit * item.quantity)                        
                    monto_afectacion_tributo = valor_venta * impuesto    
                    precio_unitario = (item.price_unit * impuesto) + item.price_unit    

                    if(str(int(tax_line.sunat_tributo))=="1000"):
                        sumatoria_igv += monto_afectacion_tributo
                        sumatoria_igv_impuesto += impuesto
                        total_venta_igv += valor_venta
                        total_venta += total_venta_igv
                        tipoAfectacionTributo = "10"

                    if(str(int(tax_line.sunat_tributo))=="2000"):
                        sumatoria_isc += monto_afectacion_tributo
                        sumatoria_isc_impuesto += impuesto
                        total_venta_ics += valor_venta
                        total_venta += total_venta_ics
                        tipoAfectacionTributo = "01" # catalogo 8
                        
                    if(str(int(tax_line.sunat_tributo))=="9998"):
                        sumatoria_inafecto += monto_afectacion_tributo
                        sumatoria_inafecto_impuesto += impuesto
                        total_venta_inafecto += valor_venta
                        total_venta += total_venta_inafecto
                        tipoAfectacionTributo = "30"

                    if(str(int(tax_line.sunat_tributo))=="9996"):
                        sumatoria_gratuita += monto_afectacion_tributo
                        sumatoria_gratuita_impuesto += impuesto
                        total_venta_gratuita += valor_venta
                        total_venta += total_venta_gratuita
                        tipoAfectacionTributo = "21"
                    
                    if(str(int(tax_line.sunat_tributo))=="9997"):
                        sumatoria_exonerada += monto_afectacion_tributo
                        sumatoria_exonerada_impuesto += impuesto
                        total_venta_exonerada += valor_venta
                        total_venta += total_venta_exonerada
                        tipoAfectacionTributo = "20"
                    
                    if(str(int(tax_line.sunat_tributo))=="9995"):
                        sumatoria_exportacion += monto_afectacion_tributo
                        sumatoria_exportacion_impuesto += impuesto
                        total_venta_exportacion += valor_venta
                        total_venta += total_venta_exportacion
                        tipoAfectacionTributo = "40"

                    if(str(int(tax_line.sunat_tributo))=="9999"):
                        sumatoria_other += monto_afectacion_tributo
                        sumatoria_other_impuesto += impuesto
                        total_venta_other += valor_venta
                        total_venta += total_venta_other
                        tipoAfectacionTributo = "10"
                    
                    invoice_item = {
                                        'id':str(item.id),
                                        'cantidad':str(item.quantity),
                                        'descripcion':item.name, 
                                        'valorVenta':valor_venta, 
                                        'valorUnitario':item.price_unit, 
                                        'precioVentaUnitario':precio_unitario, 
                                        'tipoPrecioVentaUnitario':'01',  #instalar en ficha de producto catalogo 16                                            
                                        "tributo":{
                                                    "codigo":str(int(tax_line.sunat_tributo)),
                                                    "porcentaje": tax_line.amount,#taxes.tax_id.amount,
                                                    'montoAfectacionTributo':monto_afectacion_tributo, 
                                                    'tipoAfectacionTributo': tipoAfectacionTributo, # pendiente si es igv - catalogo 7. 
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                                  },                                                
                                        'unidadMedidaCantidad':"ZZ",
                                    }
                    invoice_items.append(invoice_item)  

            serieParts = str(invoice.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")
            #end for

            data = {
                    'serie': str(serieConsecutivoString),
                    "numero":str(serieConsecutivo),
                    "emisor":{
                                "tipo":6,
                                "nro":invoice.company_id.sol_ruc,
                                "nombre":invoice.company_id.name,
                                "direccion":invoice.company_id.street,
                                "ciudad":invoice.company_id.city,
                                "departamento":invoice.company_id.state_id.name,
                                "codigoPostal":invoice.company_id.zip,
                                "codigoPais":invoice.company_id.country_id.code,
                                "ubigeo":invoice.company_id.ubigeo
                             },
                    "receptor": {
                                    "tipo": 6,
                                    "nro": invoice.partner_id.vat,
                                    "nombre":invoice.partner_id.name,
                                    "direccion":invoice.partner_id.street,
                                },
                    "tributo":{
                                'IGV': {"total_venta":str(round(float(total_venta_igv),2)), "impuesto":str(round(float(sumatoria_igv_impuesto),2)), "sumatoria":str(round(float(sumatoria_igv),2))},
                                'ISC': {"total_venta":str(round(float(total_venta_ics),2)), "impuesto":str(round(float(sumatoria_isc_impuesto),2)), "sumatoria":str(round(float(sumatoria_isc),2))},
                                'inafecto': {"total_venta":str(round(float(total_venta_inafecto),2)), "impuesto":str(round(float(sumatoria_inafecto_impuesto),2)), "sumatoria":str(round(float(sumatoria_inafecto),2))},
                                'exonerado': {"total_venta":str(round(float(total_venta_exonerada),2)), "impuesto":str(round(float(sumatoria_exonerada_impuesto),2)), "sumatoria":str(round(float(sumatoria_exonerada),2))},
                                'exportacion': {"total_venta":str(round(float(total_venta_exportacion),2)), "impuesto":str(round(float(sumatoria_exportacion_impuesto),2)), "sumatoria":str(round(float(sumatoria_exportacion),2))},
                                'other': {"total_venta":str(round(float(total_venta_other),2)), "impuesto":str(round(float(sumatoria_other_impuesto),2)), "sumatoria":str(round(float(sumatoria_other),2))},
                               },
                    "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                    "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                    "horaEmision":currentTime,
                    
                    'totalVenta': total_venta,
                    'tipoMoneda': invoice.currency_id.name,
                    'items':invoice_items,
                    'sol':{
                            'usuario':invoice.company_id.sol_username,
                            'clave':invoice.company_id.sol_password
                          },
                    'licencia':"081OHTGAVHJZ4GOZJGJV"
                    } 
            #
            with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                json.dump(data, outfile)

            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.sol_ruc)+"-03-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            sunatResponse = SunatService.processTicket(data)

            
                        
            if(sunatResponse["status"] == "OK"):
                # generate qr for invoices and tickets in pos
                base_url = request.env['ir.config_parameter'].get_param('web.base.url')
                base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
                qr = qrcode.QRCode(
                                    version=1,
                                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                                    box_size=20,
                                    border=4,
                                  )
                qr.add_data(base_url)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                self.qr_image = base64.b64encode(temp.getvalue())
                self.qr_in_report = True
                
                self.api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"]["description"])
                return super(account_invoice, self).invoice_validate()
            else:
                errorMessage = "ESTADO: "+str(sunatResponse["status"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"])
                raise Warning(errorMessage)
                
        elif(tipo_documento_consultar=="FAC" or tipo_documento_consultar=="INV"):            
            index = 0
            total_venta = 0
            for invoice in self:            
                items = invoice.invoice_line_ids
                for item in items:
                    tax_line = False
                    for tax in item.invoice_line_tax_ids:
                           tax_line = tax   

                    impuesto = tax_line.amount/100
                    valor_venta = (item.price_unit * item.quantity)                        
                    monto_afectacion_tributo = valor_venta * impuesto    
                    precio_unitario = (item.price_unit * impuesto) + item.price_unit                                                          
                    

                    if(str(int(tax_line.sunat_tributo))=="1000"):
                        sumatoria_igv += monto_afectacion_tributo
                        sumatoria_igv_impuesto += impuesto
                        total_venta_igv += valor_venta
                        total_venta += total_venta_igv
                        tipoAfectacionTributo = "10"

                    if(str(int(tax_line.sunat_tributo))=="2000"):
                        sumatoria_isc += monto_afectacion_tributo
                        sumatoria_isc_impuesto += impuesto
                        total_venta_ics += valor_venta
                        total_venta += total_venta_ics
                        tipoAfectacionTributo = "01" # catalogo 8
                        
                    if(str(int(tax_line.sunat_tributo))=="9998"):
                        sumatoria_inafecto += monto_afectacion_tributo
                        sumatoria_inafecto_impuesto += impuesto
                        total_venta_inafecto += valor_venta
                        total_venta += total_venta_inafecto
                        tipoAfectacionTributo = "30"

                    if(str(int(tax_line.sunat_tributo))=="9996"):
                        sumatoria_gratuita += monto_afectacion_tributo
                        sumatoria_gratuita_impuesto += impuesto
                        total_venta_gratuita += valor_venta
                        total_venta += total_venta_gratuita
                        tipoAfectacionTributo = "21"
                    
                    if(str(int(tax_line.sunat_tributo))=="9997"):
                        sumatoria_exonerada += monto_afectacion_tributo
                        sumatoria_exonerada_impuesto += impuesto
                        total_venta_exonerada += valor_venta
                        total_venta += total_venta_exonerada
                        tipoAfectacionTributo = "20"
                    
                    if(str(int(tax_line.sunat_tributo))=="9995"):
                        sumatoria_exportacion += monto_afectacion_tributo
                        sumatoria_exportacion_impuesto += impuesto
                        total_venta_exportacion += valor_venta
                        total_venta += total_venta_exportacion
                        tipoAfectacionTributo = "40"

                    if(str(int(tax_line.sunat_tributo))=="9999"):
                        sumatoria_other += monto_afectacion_tributo
                        sumatoria_other_impuesto += impuesto
                        total_venta_other += valor_venta
                        total_venta += total_venta_other
                        tipoAfectacionTributo = "10"
                    
                    invoice_item = {
                                        'id':str(item.id),
                                        'cantidad':str(item.quantity),
                                        'descripcion':item.name, 
                                        'valorVenta':valor_venta, 
                                        'valorUnitario':item.price_unit, 
                                        'precioVentaUnitario':precio_unitario, 
                                        'tipoPrecioVentaUnitario':'01',  #instalar en ficha de producto catalogo 16                                            
                                        "tributo":{
                                                    "codigo":str(int(tax_line.sunat_tributo)),
                                                    "porcentaje": tax_line.amount,#taxes.tax_id.amount,
                                                    'montoAfectacionTributo':monto_afectacion_tributo, 
                                                    'tipoAfectacionTributo': tipoAfectacionTributo, # pendiente si es igv - catalogo 7. 
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                                  },                                                
                                        'unidadMedidaCantidad':"ZZ",
                                    }
                    invoice_items.append(invoice_item)  

            serieParts = str(invoice.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")
            #end for

            data = {
                    'serie': str(serieConsecutivoString),
                    "numero":str(serieConsecutivo),
                    "emisor":{
                                "tipo":6,
                                "nro":invoice.company_id.sol_ruc,
                                "nombre":invoice.company_id.name,
                                "direccion":invoice.company_id.street,
                                "ciudad":invoice.company_id.city,
                                "departamento":invoice.company_id.state_id.name,
                                "codigoPostal":invoice.company_id.zip,
                                "codigoPais":invoice.company_id.country_id.code,
                                "ubigeo":invoice.company_id.ubigeo
                             },
                    "receptor": {
                                    "tipo": 6,
                                    "nro": invoice.partner_id.vat,
                                    "nombre":invoice.partner_id.name,
                                    "direccion":invoice.partner_id.street,
                                },
                    "tributo":{
                                'IGV': {"total_venta":str(round(float(total_venta_igv),2)), "impuesto":str(round(float(sumatoria_igv_impuesto),2)), "sumatoria":str(round(float(sumatoria_igv),2))},
                                'ISC': {"total_venta":str(round(float(total_venta_ics),2)), "impuesto":str(round(float(sumatoria_isc_impuesto),2)), "sumatoria":str(round(float(sumatoria_isc),2))},
                                'inafecto': {"total_venta":str(round(float(total_venta_inafecto),2)), "impuesto":str(round(float(sumatoria_inafecto_impuesto),2)), "sumatoria":str(round(float(sumatoria_inafecto),2))},
                                'exonerado': {"total_venta":str(round(float(total_venta_exonerada),2)), "impuesto":str(round(float(sumatoria_exonerada_impuesto),2)), "sumatoria":str(round(float(sumatoria_exonerada),2))},
                                'exportacion': {"total_venta":str(round(float(total_venta_exportacion),2)), "impuesto":str(round(float(sumatoria_exportacion_impuesto),2)), "sumatoria":str(round(float(sumatoria_exportacion),2))},
                                'other': {"total_venta":str(round(float(total_venta_other),2)), "impuesto":str(round(float(sumatoria_other_impuesto),2)), "sumatoria":str(round(float(sumatoria_other),2))},
                               },
                    "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                    "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                    "horaEmision":currentTime,
                    
                    'totalVenta': total_venta,
                    'tipoMoneda': invoice.currency_id.name,
                    'items':invoice_items,
                    'sol':{
                            'usuario':invoice.company_id.sol_username,
                            'clave':invoice.company_id.sol_password
                          },
                    'licencia':"081OHTGAVHJZ4GOZJGJV"
                    }  

            with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                 json.dump(data, outfile)
                 
            #raise Warning("STOP")     
            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.sol_ruc)+"-01-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            sunatResponse = SunatService.processInvoice(data)

            #with open('/home/rockscripts/Documents/data1.json', 'w') as outfile:
            #    json.dump(sunatResponse, outfile)

            

            if(sunatResponse["status"] == "OK"):
                
                # generate qr for invoices and tickets in pos
                base_url = request.env['ir.config_parameter'].get_param('web.base.url')
                base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
                qr = qrcode.QRCode(
                                    version=1,
                                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                                    box_size=20,
                                    border=4,
                                  )
                qr.add_data(base_url)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                self.qr_image = base64.b64encode(temp.getvalue())
                self.qr_in_report = True
                
                self.api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"]["description"])
                return super(account_invoice, self).invoice_validate()
            else:
                errorMessage = "ESTADO: "+str(sunatResponse["status"])+"\n"+"DESCRIPCIÓN: "+str(sunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"])
                raise Warning(errorMessage)
        else:
            return super(account_invoice, self).invoice_validate()
