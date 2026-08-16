# Retired GitHub synchronization

Direct GitHub issue synchronization is not part of Roadmap 0.2. The 0.1.1
commands were experimental and are scheduled for removal; do not configure a
new workflow around them.

Use ordinary Git to share canonical Roadmap files:

```bash
git add .roadmap/
git commit -m "Update roadmap"
git pull --rebase
git push
```

Roadmap does not need a GitHub personal access token. If one was created solely
for Roadmap, remove it from local and CI configuration and revoke it. Existing
provider URLs or IDs may remain ordinary canonical content, but Roadmap will
not validate or reconcile them.

See [Supported workflows](WORKFLOWS.md) and the
[0.2 public contract](../architecture/public-contract-0.2.md).
