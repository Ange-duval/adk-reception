# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ReceptionSettings(models.TransientModel):
    """Écran de paramètres autonome, propre au module ADK Réception.

    Volontairement indépendant de la vue `res.config.settings` du coeur
    Odoo (dont la structure interne peut changer d'une version/build à
    l'autre) : les valeurs sont lues/écrites directement dans
    `ir.config_parameter`, ce qui rend ce module totalement autonome et
    évite toute erreur de parsing XPath liée au thème/build Odoo utilisé.
    """
    _name = 'adk.reception.settings'
    _description = 'Paramètres ADK Réception'

    expected_start_hour = fields.Float(string="Heure d'arrivée attendue", default=8.0)
    expected_end_hour = fields.Float(string="Heure de départ attendue", default=17.0)
    late_tolerance_minutes = fields.Integer(string="Tolérance retard/dépassement (min)", default=10)
    notify_host_email = fields.Boolean(string="Notifier l'hôte par email en plus du chatter")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        param = self.env['ir.config_parameter'].sudo()
        res['expected_start_hour'] = float(param.get_param('adk_reception.expected_start_hour', 8.0))
        res['expected_end_hour'] = float(param.get_param('adk_reception.expected_end_hour', 17.0))
        res['late_tolerance_minutes'] = int(param.get_param('adk_reception.late_tolerance_minutes', 10))
        res['notify_host_email'] = param.get_param('adk_reception.notify_host_email', 'False') == 'True'
        return res

    def action_save(self):
        self.ensure_one()
        param = self.env['ir.config_parameter'].sudo()
        param.set_param('adk_reception.expected_start_hour', self.expected_start_hour)
        param.set_param('adk_reception.expected_end_hour', self.expected_end_hour)
        param.set_param('adk_reception.late_tolerance_minutes', self.late_tolerance_minutes)
        param.set_param('adk_reception.notify_host_email', self.notify_host_email)
        return {'type': 'ir.actions.act_window_close'}
