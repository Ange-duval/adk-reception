# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ReceptionVisitor(models.Model):
    """Fiche maître d'un visiteur : permet de retrouver rapidement un visiteur
    récurrent (recherche par nom / n° de pièce) et de conserver son historique
    de visites sans ressaisir ses informations à chaque passage."""
    _name = 'adk.reception.visitor'
    _description = 'Visiteur (fiche maître)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name asc'

    name = fields.Char(string="Nom complet", required=True, tracking=True, index=True)
    company_name = fields.Char(string="Entreprise", tracking=True)
    phone = fields.Char(string="Téléphone", tracking=True)
    email = fields.Char(string="Email", tracking=True)
    photo = fields.Image(string="Photo", max_width=1024, max_height=1024)
    id_piece_type = fields.Many2one('adk.reception.id.type', string="Type de pièce", tracking=True)
    id_piece_number = fields.Char(string="N° de pièce", tracking=True, index=True)
    is_blacklisted = fields.Boolean(string="Liste noire / Accès refusé", tracking=True)
    blacklist_reason = fields.Text(string="Motif du refus d'accès")
    notes = fields.Text(string="Observations")
    active = fields.Boolean(default=True)

    visit_ids = fields.One2many('adk.reception.visit', 'visitor_id', string="Visites")
    visit_count = fields.Integer(string="Nb Visites", compute="_compute_visit_count", store=True)
    last_visit_date = fields.Datetime(string="Dernière visite", compute="_compute_visit_count", store=True)

    @api.depends('visit_ids.check_in_datetime')
    def _compute_visit_count(self):
        for rec in self:
            rec.visit_count = len(rec.visit_ids)
            dates = [d for d in rec.visit_ids.mapped('check_in_datetime') if d]
            rec.last_visit_date = max(dates) if dates else False

    def action_view_visits(self):
        self.ensure_one()
        return {
            'name': _('Visites de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'adk.reception.visit',
            'view_mode': 'list,form',
            'domain': [('visitor_id', '=', self.id)],
            'context': {'default_visitor_id': self.id},
        }

    def action_new_visit(self):
        self.ensure_one()
        return {
            'name': _('Nouvelle Visite'),
            'type': 'ir.actions.act_window',
            'res_model': 'adk.reception.visit',
            'view_mode': 'form',
            'context': {
                'default_visitor_id': self.id,
                'default_visitor_name': self.name,
                'default_visitor_company': self.company_name,
                'default_id_piece_type': self.id_piece_type,
                'default_id_piece_number': self.id_piece_number,
                'default_photo': self.photo,
            },
        }
