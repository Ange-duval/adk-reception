/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

const PAGE_SIZE = 20;
const AUTO_REFRESH_MS = 30000;

export class ReceptionDashboard extends Component {
    static template = "adk_reception.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.feedRef = useRef("feedContainer");

        this.state = useState({
            darkMode: false,
            period: "today",
            profileType: "all",
            search: "",
            kpis: {},
            entries: [],
            offset: 0,
            hasMore: true,
            loading: false,
            loadingMore: false,
            lastRefresh: null,
        });

        this.searchTimeout = null;
        this.refreshInterval = null;

        onWillStart(async () => {
            await this.loadKpis();
            await this.loadFeed(true);
        });

        onMounted(() => {
            this.refreshInterval = setInterval(() => {
                this.loadKpis();
            }, AUTO_REFRESH_MS);
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
        });
    }

    async loadKpis() {
        const kpis = await this.orm.call("adk.reception.dashboard", "get_kpis", [], {
            period: this.state.period,
        });
        this.state.kpis = kpis;
        this.state.lastRefresh = new Date();
    }

    async loadFeed(reset = false) {
        if (reset) {
            this.state.offset = 0;
            this.state.entries = [];
            this.state.hasMore = true;
            this.state.loading = true;
        } else {
            if (!this.state.hasMore || this.state.loadingMore) {
                return;
            }
            this.state.loadingMore = true;
        }
        try {
            const result = await this.orm.call("adk.reception.dashboard", "get_activity_feed", [], {
                offset: this.state.offset,
                limit: PAGE_SIZE,
                period: this.state.period,
                profile_type: this.state.profileType,
                search: this.state.search,
            });
            this.state.entries = reset ? result.entries : [...this.state.entries, ...result.entries];
            this.state.offset += result.entries.length;
            this.state.hasMore = result.has_more;
        } finally {
            this.state.loading = false;
            this.state.loadingMore = false;
        }
    }

    onScrollFeed(ev) {
        const el = ev.target;
        if (el.scrollHeight - el.scrollTop - el.clientHeight < 120) {
            this.loadFeed(false);
        }
    }

    async onChangePeriod(period) {
        this.state.period = period;
        await Promise.all([this.loadKpis(), this.loadFeed(true)]);
    }

    async onChangeProfileType(profileType) {
        this.state.profileType = profileType;
        await this.loadFeed(true);
    }

    onSearchInput(ev) {
        const value = ev.target.value;
        this.state.search = value;
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        this.searchTimeout = setTimeout(() => this.loadFeed(true), 350);
    }

    formatEntryTime(value) {
        // Les dates serveur sont en UTC : on les affiche dans le fuseau de l'utilisateur.
        if (!value) {
            return "";
        }
        return formatDateTime(deserializeDateTime(value));
    }

    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
    }

    async onManualRefresh() {
        await Promise.all([this.loadKpis(), this.loadFeed(true)]);
    }

    openEntry(entry) {
        const modelMap = {
            visitor: "adk.reception.visit",
            employee: "adk.reception.employee.movement",
            goods: "adk.reception.goods",
        };
        const model = modelMap[entry.kind];
        if (!model) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: entry.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openKpiTarget(kind) {
        const domainMap = {
            visitors_present: { model: "adk.reception.visit", domain: [["state", "=", "checked_in"]] },
            visitors_expected: { model: "adk.reception.visit", domain: [["state", "=", "draft"]] },
            employees_present: { model: "adk.reception.employee.movement", domain: [["state", "=", "present"]] },
            employees_late: { model: "adk.reception.employee.movement", domain: [["is_late", "=", true]] },
            employees_overtime: { model: "adk.reception.employee.movement", domain: [["is_overtime", "=", true]] },
            goods_in_pending: { model: "adk.reception.goods", domain: [["direction", "=", "in"], ["state", "=", "pending"]] },
            material_alerts: { model: "adk.reception.visit", domain: [["has_unreturned_material", "=", true]] },
        };
        const target = domainMap[kind];
        if (!target) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: target.model,
            domain: target.domain,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openSecurityList() {
        await this.action.doAction("adk_reception.action_reception_security_list_wizard");
    }
}

registry.category("actions").add("adk_reception.dashboard", ReceptionDashboard);
