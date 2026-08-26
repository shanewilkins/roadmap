# Sharing Roadmap with Git

Roadmap has no application server to self-host. Canonical project data lives in
the repository under `.roadmap/`, so any normal Git host can share it.

```bash
roadmap init --project-name "My project"
roadmap issue create --title "Build API layer"

git add .roadmap/
git commit -m "Initialize roadmap and add API work"
git push
```

Collaborators use their existing Git authentication and workflow:

```bash
git pull --rebase
roadmap issue list
```

Roadmap 0.2 does not wrap fetch, merge, rebase, or push and does not maintain a
second remote-sync backend. The local SQLite database is a rebuildable
projection, not a shared database. Canonical Markdown and YAML files win if the
projection disagrees.

The `roadmap git sync`, provider-backend, automatic-hook, and provider-token
instructions formerly in this guide described experimental 0.1.1 behavior and
are retired. See the [supported workflows](user_guide/WORKFLOWS.md) and
[0.2 public contract](architecture/public-contract-0.2.md).
