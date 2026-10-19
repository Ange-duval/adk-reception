# -*- coding: utf-8 -*-
from odoo import models, fields


class ReceptionMaterialLine(models.Model):
    """Ligne de matériel déclaré (apporté ou emporté) par un visiteur ou un
    employé. Une seule table sert les deux flux (visite / badgeage employé)."""
    _name = 'adk.reception.material.line'
    _description = 'Matériel déclaré (entrée/sortie)'
    _order = 'id desc'

    visit_id = fields.Many2one('adk.reception.visit', string="Visite",
                                ondelete='cascade', index=True)
    employee_movement_id = fields.Many2one('adk.reception.employee.movement', string="Badgeage Employé",
                                            ondelete='cascade', index=True)

    description = fields.Char(string="Objet / Matériel", required=True)
    category = fields.Many2one('adk.reception.material.category', string="Catégorie", required=True)
    quantity = fields.Integer(string="Quantité", default=1)
    direction = fields.Selection([
        ('in', 'Entrée (apporté)'),
        ('out', 'Sortie (emporté)'),
    ], string="Sens", default='in', required=True)
    returned = fields.Boolean(
        string="Restitué / Confirmé à la sortie",
        help="À cocher lorsque l'objet a bien été repris par son propriétaire "
             "(sortie) ou laissé sur site comme convenu à l'entrée.")
    notes = fields.Char(string="Note")
