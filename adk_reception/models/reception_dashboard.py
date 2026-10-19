# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pytz
from odoo import models, api, fields, _


class ReceptionDashboard(models.AbstractModel):
    """Backend logique du Dashboard OWL (adk_reception.Dashboard).
    Toutes les méthodes sont appelées en RPC (orm.call) depuis le composant
    JS ; aucune vue ne pointe sur ce modèle abstrait."""
    _name = 'adk.reception.dashboard'
    _description = 'Tableau de Bord Réception (backend)'

    @api.model
    def _get_period_domain(self, period, field='check_in_datetime'):
        # « Aujourd'hui » = minuit dans le fuseau de l'utilisateur, converti en UTC
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        local_midnight = datetime.now(pytz.utc).astimezone(tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        today_start = local_midnight.astimezone(pytz.utc).replace(tzinfo=None)
        if period == 'today':
            return [(field, '>=', today_start)]
        if period == 'week':
            start = today_start - timedelta(days=today_start.weekday())
            return [(field, '>=', start)]
        if period == 'month':
            start = today_start.replace(day=1)
            return [(field, '>=', start)]
        if period == 'year':
            start = today_start.replace(month=1, day=1)
            return [(field, '>=', start)]
        return []

    @api.model
    def get_kpis(self, period='today'):
        Visit = self.env['adk.reception.visit']
        Emp = self.env['adk.reception.employee.movement']
        Goods = self.env['adk.reception.goods']

        visit_domain = self._get_period_domain(period, 'check_in_datetime')

        visitors_present = Visit.search_count([('state', '=', 'checked_in')])
        visitors_expected = Visit.search_count([('state', '=', 'draft')])
        visitors_checked_out = Visit.search_count(visit_domain + [('state', '=', 'checked_out')])
        visitors_today_total = Visit.search_count(visit_domain)

        employees_present = Emp.search_count([('state', '=', 'present')])
        employees_late = Emp.search_count(self._get_period_domain(period, 'check_in_datetime') + [('is_late', '=', True)])
        employees_overtime = Emp.search_count(self._get_period_domain(period, 'check_in_datetime') + [('is_overtime', '=', True)])

        goods_in_pending = Goods.search_count([('direction', '=', 'in'), ('state', '=', 'pending')])
        goods_today = Goods.search_count(self._get_period_domain(period, 'movement_datetime'))

        alerts = Visit.search_count([('state', '=', 'checked_in'), ('has_unreturned_material', '=', True)])

        return {
            'visitors_present': visitors_present,
            'visitors_expected': visitors_expected,
            'visitors_checked_out': visitors_checked_out,
            'visitors_today_total': visitors_today_total,
            'employees_present': employees_present,
            'employees_late': employees_late,
            'employees_overtime': employees_overtime,
            'goods_in_pending': goods_in_pending,
            'goods_today': goods_today,
            'material_alerts': alerts,
            'total_present_onsite': visitors_present + employees_present,
        }

    @api.model
    def get_activity_feed(self, offset=0, limit=20, period='today', profile_type='all', search=''):
        """Flux d'activité unifié (visiteurs + employés + biens) trié par
        date décroissante, avec chargement progressif (scroll infini)."""
        entries = []

        def _push(kind, id_, label, sub, dt, state, icon, state_label=None):
            entries.append({
                'kind': kind, 'id': id_, 'label': label, 'sub': sub,
                'datetime': fields.Datetime.to_string(dt) if dt else False,
                '_dt': dt or datetime.min,
                'state': state, 'state_label': state_label or state, 'icon': icon,
            })

        domain_period = self._get_period_domain(period, 'check_in_datetime')

        if profile_type in ('all', 'visitor'):
            visit_domain = domain_period + (
                [('visitor_name', 'ilike', search)] if search else [])
            visits = self.env['adk.reception.visit'].search(visit_domain, limit=200)
            for v in visits:
                _push('visitor', v.id, v.visitor_name,
                      _('Visite - %s') % (v.motif_id.name or v.motif_detail or '-'),
                      v.check_in_datetime or v.create_date, v.state, 'fa-user',
                      dict(v._fields['state'].selection).get(v.state))

        if profile_type in ('all', 'employee'):
            emp_domain = self._get_period_domain(period, 'check_in_datetime') + (
                [('employee_id.name', 'ilike', search)] if search else [])
            movements = self.env['adk.reception.employee.movement'].search(emp_domain, limit=200)
            for m in movements:
                sub = _('Badgeage')
                if m.is_late:
                    sub = _('Retard %d min') % m.late_minutes
                elif m.is_overtime:
                    sub = _('Heures sup. +%d min') % m.overtime_minutes
                _push('employee', m.id, m.employee_id.name, sub,
                      m.check_in_datetime, m.state, 'fa-id-badge',
                      dict(m._fields['state'].selection).get(m.state))

        if profile_type in ('all', 'goods'):
            goods_domain = self._get_period_domain(period, 'movement_datetime') + (
                [('description', 'ilike', search)] if search else [])
            goods = self.env['adk.reception.goods'].search(goods_domain, limit=200)
            for g in goods:
                _push('goods', g.id, g.description,
                      g.goods_type.name or '-',
                      g.movement_datetime, g.state, 'fa-cube',
                      dict(g._fields['state'].selection).get(g.state))

        entries.sort(key=lambda e: e['_dt'], reverse=True)
        for e in entries:
            e.pop('_dt', None)

        total = len(entries)
        page = entries[offset:offset + limit]
        return {'entries': page, 'total': total, 'has_more': offset + limit < total}

    @api.model
    def get_present_list(self):
        """Liste de sécurité instantanée pour évacuation : toutes les
        personnes actuellement présentes sur site (visiteurs + employés)."""
        visits = self.env['adk.reception.visit'].search([('state', '=', 'checked_in')])
        movements = self.env['adk.reception.employee.movement'].search([('state', '=', 'present')])
        result = []
        for v in visits:
            result.append({
                'type': _('Visiteur'), 'name': v.visitor_name,
                'detail': v.host_id.name or '-',
                'since': fields.Datetime.to_string(v.check_in_datetime),
            })
        for m in movements:
            result.append({
                'type': _('Employé'), 'name': m.employee_id.name,
                'detail': m.department_id.name or '-',
                'since': fields.Datetime.to_string(m.check_in_datetime),
            })
        return result
