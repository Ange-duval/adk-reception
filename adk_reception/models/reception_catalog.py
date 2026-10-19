# -*- coding: utf-8 -*-
from odoo import models, fields


class ReceptionIdType(models.Model):
    """Type de pièce d'identité — configurable, remplace l'ancienne liste
    figée pour permettre à l'utilisateur d'ajouter ses propres types
    (visa, carte de séjour, badge partenaire, etc.)."""
    _name = 'adk.reception.id.type'
    _description = "Type de pièce d'identité"
    _order = 'sequence asc, name asc'

    name = fields.Char(string="Type de pièce", required=True)
    sequence = fields.Integer(string="Ordre", default=10)
    active = fields.Boolean(default=True)


class ReceptionMaterialCategory(models.Model):
    """Catégorie de matériel déclaré (entrée/sortie) — configurable."""
    _name = 'adk.reception.material.category'
    _description = 'Catégorie de matériel'
    _order = 'sequence asc, name asc'

    name = fields.Char(string="Catégorie", required=True)
    sequence = fields.Integer(string="Ordre", default=10)
    icon = fields.Char(string="Icône (classe FontAwesome)", default='fa-cube',
                        help="ex: fa-laptop, fa-archive, fa-wrench")
    active = fields.Boolean(default=True)


class ReceptionBadgeMethod(models.Model):
    """Méthode de badgeage employé — configurable (QR, NFC, matricule, etc.)."""
    _name = 'adk.reception.badge.method'
    _description = 'Méthode de badgeage'
    _order = 'sequence asc, name asc'

    name = fields.Char(string="Méthode", required=True)
    sequence = fields.Integer(string="Ordre", default=10)
    active = fields.Boolean(default=True)


class ReceptionGoodsType(models.Model):
    """Type de bien / marchandise — configurable."""
    _name = 'adk.reception.goods.type'
    _description = 'Type de bien / marchandise'
    _order = 'sequence asc, name asc'

    name = fields.Char(string="Type", required=True)
    sequence = fields.Integer(string="Ordre", default=10)
    icon = fields.Char(string="Icône (classe FontAwesome)", default='fa-cube')
    active = fields.Boolean(default=True)
