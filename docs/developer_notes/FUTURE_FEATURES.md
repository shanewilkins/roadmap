# Future Features: Roadmap for Roadmap

What we're planning for Roadmap (the tool's roadmap).

## v1.0.0 (Current)

**Release Date:** Early 2025

✅ **In v1.0:**
- CLI-first interface with 15+ commands
- Issue, milestone, and project management
- Four output formats (rich, JSON, CSV, plain)
- Advanced filtering and sorting
- Git integration (commit message parsing)
- GitHub two-way sync
- 87% test coverage
- Security audit framework
- YAML/Markdown data format

❌ **Not in v1.0:**
- Web UI
- PR/MR auto-sync
- Historical tracking
- Analytics dashboards
- Enterprise features (RBAC, SSO)

---

## v1.1.0: Analytics & Insights (Q2 2025)

**Focus:** Historical tracking and trend analysis.

### Planned Features

#### Historical Tracking
```bash
roadmap history issue-id               # Show all status changes
roadmap history issue-id --from 2025-01-01 --to 2025-02-01
roadmap history milestone-id           # Milestone progress over time
```

**Implementation:**
- Timestamp all status changes (already done)
- Add `roadmap history` command
- Query snapshots across time
- Show who changed what and when

#### Trends & Velocity
```bash
roadmap analytics velocity            # Team velocity (issues per week)
roadmap analytics burndown milestone-id
roadmap analytics cycle-time          # How long issues take (avg)
```

**Implementation:**
- Analyze snapshot history
- Calculate metrics
- Output as JSON/CSV for graphing

#### Daily Snapshots (Automated)
```bash
roadmap snapshot create               # Manual snapshot
roadmap snapshot list                 # View all snapshots
```

**Implementation:**
- Auto-save daily status to `.roadmap/.snapshots/`
- Optional: Cron job for automation
- Git history = trend tracking

---

## v1.2.0: Enterprise Features (Q3 2025)

**Focus:** Team management and access control.

### Planned Features

#### Role-Based Access Control (RBAC)
```bash
roadmap team add alice                # Add team member
roadmap team list                     # List team
roadmap team alice --role dev         # Assign role

# Roles:
# - admin: Full access
# - pm: Can assign, change milestones
# - dev: Can only update assigned issues
# - viewer: Read-only access
```

**Implementation:**
- Store team definitions in `config.yaml`
- Check permissions before operations
- API auth for GitHub/GitLab sync

#### Team Permissions
- PMs: Create issues, assign to team, move milestones
- Devs: Update own issues, commit-based status changes
- Viewers: Read-only export (CLI or web)

#### Multi-Team Support
```bash
roadmap team create platform
roadmap team create web
roadmap team add alice --team platform --team web
```

---

## v1.3.0: Integration Platform (Q4 2025)

**Focus:** Webhooks, REST API, SDKs.

### Planned Features

#### REST API
```
GET /api/issues                       # List issues
POST /api/issues                      # Create issue
PATCH /api/issues/{id}                # Update issue
```

**Use case:** External tooling, dashboards, mobile apps.

#### Webhooks
```yaml
webhooks:
  - event: issue.created
    url: https://example.com/webhook

  - event: issue.status_changed
    url: https://example.com/notify
```

**Use cases:**
- Slack notifications
- Custom automation
- CI/CD triggers

#### SDKs
- Python SDK for scripting
- JavaScript SDK for tooling
- Go SDK for deployment automation

#### Third-Party Integrations
- Slack: Status updates, notifications
- Discord: Daily summary posts
- Datadog: Ingest metrics
- Grafana: Dashboard data source

---

## v2.0.0: Advanced Platform (2026)

**Focus:** Web UI, real-time collaboration, mobile.

### Planned Features

#### Web UI
- Interactive dashboard
- Drag-and-drop Kanban board
- Gantt charts
- Burndown charts
- Team insights

#### Real-Time Collaboration
- WebSocket sync
- Live presence (who's viewing what)
- Concurrent editing with conflict resolution

#### Mobile Apps
- iOS app for status updates
- Android app for notifications
- Offline support

#### AI/ML Integration
- Predictive analytics
  - "This issue will take ~3 days"
  - "You're at risk of missing deadline"
- Smart recommendations
  - "Based on history, prioritize X next"
  - "Team is overloaded, defer Y to next sprint"
- Automated summaries
  - "Here's what the team did this week"

---

## Deferred / Maybe

### Things We're **Not** Planning (Yet)

#### Advanced Project Management
- Kanban boards (v2.0)
- Gantt charts (v2.0)
- Time tracking (maybe v1.3)
- Resource planning (enterprise only)
- Capacity planning (v1.2+)

#### Workflow Customization
- Custom issue statuses (v1.1)
- Custom fields (v1.1)
- Custom workflows (v2.0)

#### Scale Features
- Multi-organization support (v1.2+)
- Workspace management (v2.0)
- Subscription tiers (if SaaS)

#### Things We'll Probably Never Do
- Microsoft Outlook integration
- Salesforce integration
- Enterprise licensing
- Closed-source version
- Proprietary data format
- Cloud-only SaaS lock-in

We're staying CLI-first, open-source, and focused on developer experience.

---

## Contributing to the Roadmap

Have feature ideas? Here's how:

### File an Issue

```bash
cd roadmap
git checkout -b feature/my-idea
# Edit docs/FUTURE_FEATURES.md with your idea
git push origin feature/my-idea
# Open a PR
```

### Contribute Code

See [Contributing Guide](../CONTRIBUTING.md) (coming in v1.0).

---

## Timeline & Versioning

| Version | Timeline | Theme |
|---------|----------|-------|
| **v1.0** | Early 2025 | Stability & Foundation |
| **v1.1** | Q2 2025 | Analytics & Insights |
| **v1.2** | Q3 2025 | Team Management |
| **v1.3** | Q4 2025 | APIs & Integration |
| **v2.0** | 2026+ | Web UI & Collaboration |

**Notes:**
- Timelines are estimates, not commitments
- User feedback may shift priorities
- v1.x will remain backward compatible
- v2.0 may have breaking changes (with migration guide)

---

## Philosophy for Future Releases

### What We'll Always Do
✅ Keep data in plain text
✅ Keep git as the source of truth
✅ Maintain open-source
✅ Support offline workflows
✅ Focus on developer experience

### What We Won't Do
❌ Close-source
❌ Require cloud SaaS
❌ Lock data in proprietary format
❌ Abandon CLI-first design
❌ Introduce licensing tiers

---

## Questions?

- See [FAQ.md](../user-guide/FAQ.md) for common questions
- File an issue on GitHub for feature requests
- Join our community discussions
