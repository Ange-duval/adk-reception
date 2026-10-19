# -*- coding: utf-8 -*-
from odoo import models, fields


class ReceptionSecurityListWizard(models.TransientModel):
    _name = 'adk.reception.security.list.wizard'
    _description = "Liste de sécurité des personnes présentes"

    generated_at = fields.Datetime(string="Générée le", default=fields.Datetime.now, readonly=True)

    def _get_present_list(self):
        self.ensure_one()
        rows = self.env['adk.reception.dashboard'].get_present_list()
        # Heures affichées dans le fuseau de l'utilisateur (le serveur stocke en UTC)
        for row in rows:
            if row.get('since'):
                dt = fields.Datetime.from_string(row['since'])
                row['since'] = fields.Datetime.context_timestamp(self, dt).strftime('%d/%m/%Y %H:%M')
        return rows

    def action_print(self):
        self.ensure_one()
        return self.env.ref('adk_reception.action_report_present_list').report_action(self)
