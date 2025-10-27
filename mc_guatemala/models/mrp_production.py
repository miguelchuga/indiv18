# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from . import util
from datetime import datetime,timedelta
import pytz
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = 'mrp.production'


    @api.onchange('x_studio_estados_ot')
    def _calcular_fechas(self):
        for rec in self:
            hora = fields.datetime.now(pytz.timezone('America/Guatemala')).strftime("%Y-%m-%d")
            if rec.x_studio_estados_ot == 'ingresada':
                rec.x_studio_hora_ot_ingresada = hora
            if rec.x_studio_estados_ot == 'ejecutar':
                rec.x_studio_hora_ot_en_proceso_iniciada_para_ejecutar = hora
            if rec.x_studio_estados_ot == 'ejecucion':
                rec.x_studio_hora_ot_en_proceso_en_ejecucin = hora
            if rec.x_studio_estados_ot == 'standby':
                rec.x_studio_hora_ot_en_stand_by = hora
            if rec.x_studio_estados_ot == 'parafacturar':
                if rec.x_studio_numero_de_personas > 0:
                    rec.x_studio_hora_ot_lista_para_facturar = hora
                else:
                    raise ValidationError(_('No ha ingresado los tiempos de empleados...'))

            if rec.x_studio_estados_ot == 'facturada':
                rec.x_studio_hora_ot_ya_facturada = hora
            if rec.x_studio_estados_ot == 'cancelada':
                rec.x_studio_hora_ot_cancelada = hora
            if rec.x_studio_estados_ot == 'parciales':
                rec.x_studio_hora_ot_en_proceso_en_ejecucin_con_cierres_parciales = hora

