# -*- coding: utf-8 -*-
import pytz
import base64
import csv
import io
from datetime import datetime, time

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReceptionExportWizard(models.TransientModel):
    _name = 'adk.reception.export.wizard'
    _description = "Générateur d'export (Historique Universel)"

    date_from = fields.Date(string="Du", required=True,
                             default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string="Au", required=True,
                           default=lambda self: fields.Date.context_today(self))
    profile_type = fields.Selection([
        ('all', 'Tous les profils'),
        ('visitor', 'Visiteurs'),
        ('employee', 'Employés'),
        ('goods', 'Biens & Marchandises'),
    ], string="Type de profil", default='all', required=True)
    export_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel (XLSX)'),
        ('csv', 'CSV'),
    ], string="Format d'export", default='xlsx', required=True)

    def _collect_rows(self):
        self.ensure_one()
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        def _utc(d, t):
            return tz.localize(datetime.combine(d, t)).astimezone(pytz.utc).replace(tzinfo=None)
        dt_from = _utc(self.date_from, time.min)
        dt_to = _utc(self.date_to, time.max)
        rows = []

        if self.profile_type in ('all', 'visitor'):
            visits = self.env['adk.reception.visit'].search([
                ('check_in_datetime', '>=', dt_from), ('check_in_datetime', '<=', dt_to),
            ])
            for v in visits:
                rows.append({
                    'type': 'Visiteur', 'nom': v.visitor_name, 'detail': v.visitor_company or '-',
                    'lien': v.host_id.name or '-', 'entree': v.check_in_datetime or '',
                    'sortie': v.check_out_datetime or '', 'statut': dict(
                        v._fields['state'].selection).get(v.state),
                })

        if self.profile_type in ('all', 'employee'):
            movements = self.env['adk.reception.employee.movement'].search([
                ('check_in_datetime', '>=', dt_from), ('check_in_datetime', '<=', dt_to),
            ])
            for m in movements:
                rows.append({
                    'type': 'Employé', 'nom': m.employee_id.name, 'detail': m.department_id.name or '-',
                    'lien': m.anomaly_notes or '-', 'entree': m.check_in_datetime or '',
                    'sortie': m.check_out_datetime or '', 'statut': dict(
                        m._fields['state'].selection).get(m.state),
                })

        if self.profile_type in ('all', 'goods'):
            goods = self.env['adk.reception.goods'].search([
                ('movement_datetime', '>=', dt_from), ('movement_datetime', '<=', dt_to),
            ])
            for g in goods:
                rows.append({
                    'type': 'Bien/Marchandise', 'nom': g.description,
                    'detail': g.goods_type.name or '-',
                    'lien': g.partner_id.name or '-', 'entree': g.movement_datetime or '',
                    'sortie': '', 'statut': dict(g._fields['state'].selection).get(g.state),
                })

        rows.sort(key=lambda r: r['entree'] or datetime.min, reverse=True)

        def _local(dt):
            # Les dates sont stockées en UTC : export dans le fuseau de l'utilisateur
            if not dt:
                return ''
            return fields.Datetime.context_timestamp(self, dt).strftime('%d/%m/%Y %H:%M')
        for r in rows:
            r['entree'] = _local(r['entree'])
            r['sortie'] = _local(r['sortie'])
        return rows

    def action_export(self):
        self.ensure_one()
        rows = self._collect_rows()
        if not rows:
            raise UserError(_("Aucune donnée à exporter pour cette période / ce profil."))

        if self.export_format == 'csv':
            return self._export_csv(rows)
        if self.export_format == 'xlsx':
            return self._export_xlsx(rows)
        return self._export_pdf()

    def _make_attachment(self, name, content):
        attachment = self.env['ir.attachment'].create({
            'name': name,
            'type': 'binary',
            'datas': base64.b64encode(content),
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _export_csv(self, rows):
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=';')
        writer.writerow(['Type', 'Nom', 'Détail', 'Hôte/Lien', 'Entrée', 'Sortie', 'Statut'])
        for r in rows:
            writer.writerow([r['type'], r['nom'], r['detail'], r['lien'],
                              r['entree'], r['sortie'], r['statut']])
        content = buffer.getvalue().encode('utf-8-sig')
        filename = 'adk_reception_export_%s_%s.csv' % (self.date_from, self.date_to)
        return self._make_attachment(filename, content)

    def _export_xlsx(self, rows):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("La librairie xlsxwriter n'est pas disponible sur ce serveur."))

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet('Historique')
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#2c3e50', 'font_color': 'white'})

        headers = ['Type', 'Nom', 'Détail', 'Hôte/Lien', 'Entrée', 'Sortie', 'Statut']
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_fmt)
            sheet.set_column(col, col, 22)

        for row_idx, r in enumerate(rows, start=1):
            sheet.write(row_idx, 0, r['type'])
            sheet.write(row_idx, 1, r['nom'])
            sheet.write(row_idx, 2, r['detail'])
            sheet.write(row_idx, 3, r['lien'])
            sheet.write(row_idx, 4, r['entree'])
            sheet.write(row_idx, 5, r['sortie'])
            sheet.write(row_idx, 6, r['statut'])

        workbook.close()
        content = buffer.getvalue()
        filename = 'adk_reception_export_%s_%s.xlsx' % (self.date_from, self.date_to)
        return self._make_attachment(filename, content)

    def _export_pdf(self):
        return self.env.ref('adk_reception.action_report_export_document').report_action(self)
