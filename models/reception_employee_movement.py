# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _


class ReceptionEmployeeMovement(models.Model):
    """Badgeage d'un employé permanent (entrée / sortie) avec traçabilité du
    matériel de travail et détection automatique des anomalies horaires."""
    _name = 'adk.reception.employee.movement'
    _description = 'Badgeage Employé'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _order = 'check_in_datetime desc, id desc'

    employee_id = fields.Many2one('hr.employee', string="Employé", required=True,
                                   tracking=True, index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string="Département")
    company_id = fields.Many2one('res.company', string="Site / Société",
                                  default=lambda self: self.env.company)

    badge_method = fields.Many2one('adk.reception.badge.method', string="Méthode de badgeage")
    matricule = fields.Char(string="Matricule", related='employee_id.barcode', store=False, readonly=True)

    state = fields.Selection([
        ('present', 'Présent'),
        ('left', 'Sorti'),
    ], string="Statut", default='present', tracking=True, required=True)
    check_in_datetime = fields.Datetime(string="Entrée", default=fields.Datetime.now, tracking=True,
                                         help="Modifiable manuellement en cas de saisie tardive. "
                                              "Toute modification est tracée ci-dessous.")
    check_out_datetime = fields.Datetime(string="Sortie", tracking=True,
                                          help="Modifiable manuellement en cas de saisie tardive. "
                                               "Toute modification est tracée ci-dessous.")
    duration = fields.Float(string="Durée (h)", compute="_compute_duration", store=True)

    is_late = fields.Boolean(string="Retard", compute="_compute_anomalies", store=True)
    late_minutes = fields.Integer(string="Minutes de retard", compute="_compute_anomalies", store=True)
    is_overtime = fields.Boolean(string="Heures supplémentaires", compute="_compute_anomalies", store=True)
    overtime_minutes = fields.Integer(string="Minutes supp.", compute="_compute_anomalies", store=True)
    anomaly_notes = fields.Char(string="Anomalie détectée", compute="_compute_anomalies", store=True)

    material_ids = fields.One2many('adk.reception.material.line', 'employee_movement_id',
                                    string="Matériel de travail")
    material_count = fields.Integer(string="Nb Objets", compute="_compute_material_count")

    active = fields.Boolean(default=True)

    @api.depends('material_ids')
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_ids)

    @api.depends('check_in_datetime', 'check_out_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.check_in_datetime and rec.check_out_datetime:
                delta = rec.check_out_datetime - rec.check_in_datetime
                rec.duration = delta.total_seconds() / 3600.0
            else:
                rec.duration = 0.0

    @api.depends('check_in_datetime', 'check_out_datetime')
    def _compute_anomalies(self):
        config = self.env['ir.config_parameter'].sudo()
        expected_start = float(config.get_param('adk_reception.expected_start_hour', 8.0))
        expected_end = float(config.get_param('adk_reception.expected_end_hour', 17.0))
        tolerance = int(config.get_param('adk_reception.late_tolerance_minutes', 10))

        for rec in self:
            rec.is_late = False
            rec.late_minutes = 0
            rec.is_overtime = False
            rec.overtime_minutes = 0
            notes = []

            if rec.check_in_datetime:
                local_dt = fields.Datetime.context_timestamp(rec, rec.check_in_datetime)
                expected_dt = local_dt.replace(
                    hour=int(expected_start), minute=int((expected_start % 1) * 60),
                    second=0, microsecond=0)
                delta_minutes = (local_dt - expected_dt).total_seconds() / 60.0
                if delta_minutes > tolerance:
                    rec.is_late = True
                    rec.late_minutes = int(delta_minutes)
                    notes.append(_("Retard de %d min à l'entrée") % rec.late_minutes)

            if rec.check_out_datetime:
                local_out = fields.Datetime.context_timestamp(rec, rec.check_out_datetime)
                expected_out = local_out.replace(
                    hour=int(expected_end), minute=int((expected_end % 1) * 60),
                    second=0, microsecond=0)
                delta_out = (local_out - expected_out).total_seconds() / 60.0
                if delta_out > tolerance:
                    rec.is_overtime = True
                    rec.overtime_minutes = int(delta_out)
                    notes.append(_("Heures supplémentaires : +%d min") % rec.overtime_minutes)

            rec.anomaly_notes = ' | '.join(notes) if notes else False

    @api.onchange('check_in_datetime')
    def _onchange_check_in_datetime_manual(self):
        """Saisie manuelle possible (agent occupé) : le statut est
        resynchronisé automatiquement ; la modification reste tracée dans
        le chatter grâce au suivi (tracking) du champ."""
        if self.check_in_datetime and self.state == 'left' and not self.check_out_datetime:
            self.state = 'present'

    @api.onchange('check_out_datetime')
    def _onchange_check_out_datetime_manual(self):
        if self.check_out_datetime:
            if not self.check_in_datetime:
                self.check_in_datetime = self.check_out_datetime
            self.state = 'left'
        elif self.state == 'left':
            self.state = 'present'

    def action_check_in(self):
        for rec in self:
            if rec.state == 'present':
                continue
            rec.write({'state': 'present', 'check_in_datetime': fields.Datetime.now(),
                       'check_out_datetime': False})

    def action_check_out(self):
        for rec in self:
            if rec.state != 'present':
                continue
            rec.write({'state': 'left', 'check_out_datetime': fields.Datetime.now()})

    @api.model
    def badge_scan(self, employee_id, badge_method_id=False):
        """Point d'entrée unique pour un badgeage (toggle in/out), utilisable
        depuis un scanner QR/NFC ou une saisie de matricule."""
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'error': _('Employé introuvable.')}
        last_open = self.search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'present'),
        ], limit=1)
        if last_open:
            last_open.action_check_out()
            return {'action': 'check_out', 'movement_id': last_open.id, 'employee': employee.name}
        movement = self.create({
            'employee_id': employee_id,
            'badge_method': badge_method_id,
        })
        return {'action': 'check_in', 'movement_id': movement.id, 'employee': employee.name}
