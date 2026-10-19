# -*- coding: utf-8 -*-
from datetime import datetime
import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReceptionVisit(models.Model):
    """Enregistrement d'une visite : de l'arrivée (check-in) au départ
    (check-out) du visiteur, horodaté à la seconde près."""
    _name = 'adk.reception.visit'
    _description = 'Visite (Check-in / Check-out)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'check_in_datetime desc, id desc'

    name = fields.Char(string="Référence", required=True, copy=False,
                        default=lambda self: _('Nouveau'), readonly=True)

    # ── Visiteur (saisie express + lien fiche maître optionnelle)
    visitor_id = fields.Many2one('adk.reception.visitor', string="Fiche visiteur",
                                  tracking=True)
    visitor_name = fields.Char(string="Nom du visiteur", required=True, tracking=True)
    visitor_company = fields.Char(string="Entreprise", tracking=True)
    photo = fields.Image(string="Photo (webcam)", max_width=1024, max_height=1024)
    id_piece_type = fields.Many2one('adk.reception.id.type', string="Type de pièce")
    id_piece_number = fields.Char(string="N° de pièce")
    is_blacklisted = fields.Boolean(related='visitor_id.is_blacklisted', string="Accès refusé", store=False)

    # ── Motif & hôte
    motif_id = fields.Many2one('adk.reception.motif', string="Motif de visite", tracking=True)
    motif_detail = fields.Char(string="Précision du motif")
    host_id = fields.Many2one('hr.employee', string="Hôte / Employé visité",
                               required=True, tracking=True)
    host_user_id = fields.Many2one(related='host_id.user_id', string="Utilisateur hôte", store=False)
    host_notified = fields.Boolean(string="Hôte notifié", default=False, readonly=True)

    # ── Site
    company_id = fields.Many2one('res.company', string="Site / Société",
                                  default=lambda self: self.env.company)

    # ── Horodatage & statut
    state = fields.Selection([
        ('draft', 'Attendu'),
        ('checked_in', 'Présent'),
        ('checked_out', 'Sorti'),
        ('cancelled', 'Annulé'),
    ], string="Statut", default='draft', tracking=True, required=True)
    expected_datetime = fields.Datetime(string="Rendez-vous prévu le")
    check_in_datetime = fields.Datetime(string="Entrée (horodatage exact)", tracking=True,
                                         help="Renseigné automatiquement au check-in, mais modifiable "
                                              "manuellement en cas de saisie tardive. Toute modification "
                                              "est tracée ci-dessous.")
    check_out_datetime = fields.Datetime(string="Sortie (horodatage exact)", tracking=True,
                                          help="Renseigné automatiquement au check-out, mais modifiable "
                                               "manuellement en cas de saisie tardive. Toute modification "
                                               "est tracée ci-dessous.")
    duration = fields.Float(string="Durée sur site (h)", compute="_compute_duration", store=True)

    # ── Matériel
    material_ids = fields.One2many('adk.reception.material.line', 'visit_id', string="Matériel déclaré")
    material_count = fields.Integer(string="Nb Objets", compute="_compute_material_count", store=True)
    has_unreturned_material = fields.Boolean(string="Matériel non confirmé à la sortie",
                                              compute="_compute_material_count", store=True)
    badge_number = fields.Char(string="N° Badge visiteur")

    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('adk.reception.visit') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('check_in_datetime', 'check_out_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.check_in_datetime and rec.check_out_datetime:
                delta = rec.check_out_datetime - rec.check_in_datetime
                rec.duration = delta.total_seconds() / 3600.0
            else:
                rec.duration = 0.0

    @api.depends('material_ids', 'material_ids.returned', 'material_ids.direction')
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_ids)
            rec.has_unreturned_material = bool(
                rec.material_ids.filtered(lambda m: m.direction == 'in' and not m.returned))

    @api.onchange('visitor_id')
    def _onchange_visitor_id(self):
        if self.visitor_id:
            self.visitor_name = self.visitor_id.name
            self.visitor_company = self.visitor_id.company_name
            self.id_piece_type = self.visitor_id.id_piece_type
            self.id_piece_number = self.visitor_id.id_piece_number
            self.photo = self.visitor_id.photo

    @api.onchange('check_in_datetime')
    def _onchange_check_in_datetime_manual(self):
        """Permet à l'agent d'accueil de saisir l'heure d'entrée manuellement
        (ex: pendant un pic d'affluence) sans passer par le bouton Check-in.
        Le statut est resynchronisé automatiquement ; la modification reste
        de toute façon tracée dans le chatter (champ suivi/tracking)."""
        if self.check_in_datetime and self.state == 'draft':
            self.state = 'checked_in'
        elif not self.check_in_datetime and self.state == 'checked_in':
            self.state = 'draft'

    @api.onchange('check_out_datetime')
    def _onchange_check_out_datetime_manual(self):
        if self.check_out_datetime:
            if not self.check_in_datetime:
                # Une sortie ne peut être postérieure à une entrée inconnue :
                # on considère alors que l'entrée a eu lieu au même moment,
                # à corriger si besoin par l'agent.
                self.check_in_datetime = self.check_out_datetime
            self.state = 'checked_out'
        elif self.state == 'checked_out':
            self.state = 'checked_in'

    def action_check_in(self):
        for rec in self:
            if rec.state == 'checked_in':
                continue
            if rec.is_blacklisted:
                raise UserError(_(
                    "Accès refusé : ce visiteur est marqué en liste noire (%s)."
                ) % (rec.visitor_id.blacklist_reason or ''))
            rec.write({
                'state': 'checked_in',
                'check_in_datetime': fields.Datetime.now(),
            })
            rec._notify_host()
        return True

    def action_check_out(self):
        for rec in self:
            if rec.state != 'checked_in':
                continue
            rec.write({
                'state': 'checked_out',
                'check_out_datetime': fields.Datetime.now(),
            })
            if rec.has_unreturned_material:
                rec.message_post(body=_(
                    "⚠️ Sortie enregistrée avec du matériel non confirmé comme restitué. "
                    "Merci de vérifier la liste du matériel."))
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'check_in_datetime': False, 'check_out_datetime': False})

    def _notify_host(self):
        for rec in self:
            if not rec.host_id:
                continue
            body = _("🔔 <b>%(visitor)s</b> (%(company)s) vient de badger à l'accueil pour vous voir. "
                      "Motif : %(motif)s") % {
                'visitor': rec.visitor_name,
                'company': rec.visitor_company or '-',
                'motif': rec.motif_id.name if rec.motif_id else (rec.motif_detail or '-'),
            }
            send_email = self.env['ir.config_parameter'].sudo().get_param(
                'adk_reception.notify_host_email') == 'True'
            rec.message_post(
                body=body,
                partner_ids=rec.host_id.user_id.partner_id.ids,
                message_type='comment' if send_email else 'notification',
                subtype_xmlid='mail.mt_comment' if send_email else 'mail.mt_note',
            )
            if rec.host_id.user_id:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Visiteur arrivé : %s') % rec.visitor_name,
                    note=body,
                    user_id=rec.host_id.user_id.id,
                )
            rec.host_notified = True

    @api.model
    def _cron_flag_forgotten_checkout(self):
        """Exécuté quotidiennement : signale (chatter + activité) les visites
        toujours 'Présent' alors qu'elles datent d'un jour précédent, pour
        éviter les oublis de check-out en fin de journée."""
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        local_midnight = datetime.now(pytz.utc).astimezone(tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        today_start = local_midnight.astimezone(pytz.utc).replace(tzinfo=None)
        stale_visits = self.search([
            ('state', '=', 'checked_in'),
            ('check_in_datetime', '<', today_start),
        ])
        for visit in stale_visits:
            visit.message_post(body=_(
                "⚠️ Ce visiteur n'a pas été enregistré en sortie depuis son entrée du %s. "
                "Merci de vérifier avec l'équipe de sécurité."
            ) % fields.Datetime.to_string(visit.check_in_datetime))
        return True

    def action_create_or_link_visitor(self):
        """Crée (ou met à jour) la fiche maître du visiteur à partir des
        informations saisies sur la visite, pour faciliter les prochains
        passages."""
        self.ensure_one()
        if not self.visitor_id:
            visitor = self.env['adk.reception.visitor'].create({
                'name': self.visitor_name,
                'company_name': self.visitor_company,
                'id_piece_type': self.id_piece_type,
                'id_piece_number': self.id_piece_number,
                'photo': self.photo,
            })
            self.visitor_id = visitor
        return True
