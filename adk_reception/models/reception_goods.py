# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ReceptionGoods(models.Model):
    """Registre logistique : colis, livraisons, fournitures et équipements
    de l'entreprise qui entrent ou sortent du site."""
    _name = 'adk.reception.goods'
    _description = 'Registre Logistique (Biens & Marchandises)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'movement_datetime desc, id desc'

    name = fields.Char(string="Référence", required=True, copy=False,
                        default=lambda self: _('Nouveau'), readonly=True)
    description = fields.Char(string="Désignation", required=True, tracking=True)
    goods_type = fields.Many2one('adk.reception.goods.type', string="Type", required=True, tracking=True)
    direction = fields.Selection([
        ('in', 'Entrée'),
        ('out', 'Sortie'),
    ], string="Sens", default='in', required=True, tracking=True)
    quantity = fields.Integer(string="Quantité", default=1)

    status = fields.Selection([
        ('temporary', 'Temporaire (ex: en réparation)'),
        ('definitive', 'Définitif'),
    ], string="Statut du flux", default='definitive', required=True, tracking=True)
    state = fields.Selection([
        ('pending', 'En attente'),
        ('processed', 'Traité'),
        ('returned', 'Retourné'),
    ], string="État", default='pending', tracking=True)

    partner_id = fields.Many2one('res.partner', string="Fournisseur / Transporteur / Destinataire")
    recipient_employee_id = fields.Many2one('hr.employee', string="Destinataire interne")
    reference_doc = fields.Char(string="N° Bon de livraison / Suivi")
    movement_datetime = fields.Datetime(string="Date & heure", default=fields.Datetime.now, tracking=True)
    expected_return_date = fields.Date(string="Retour attendu le",
                                        help="Pour les biens temporaires (réparation, prêt, etc.)")
    company_id = fields.Many2one('res.company', string="Site / Société",
                                  default=lambda self: self.env.company)
    notes = fields.Text(string="Observations")
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('adk.reception.goods') or _('Nouveau')
        return super().create(vals_list)

    def action_mark_processed(self):
        self.write({'state': 'processed'})

    def action_mark_returned(self):
        self.write({'state': 'returned'})
