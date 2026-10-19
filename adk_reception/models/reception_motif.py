# -*- coding: utf-8 -*-
from odoo import models, fields


class ReceptionMotif(models.Model):
    _name = 'adk.reception.motif'
    _description = "Motif de visite"
    _order = 'sequence asc, name asc'

    name = fields.Char(string="Motif", required=True)
    sequence = fields.Integer(string="Ordre", default=10)
    color = fields.Integer(string="Couleur")
    active = fields.Boolean(default=True)
