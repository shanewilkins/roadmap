# Retired GitHub token setup

Roadmap 0.2 does not use the GitHub API, store provider credentials, or
synchronize hosted issues. Do not create a personal access token for Roadmap.

The 0.1.1 provider integration was experimental and is scheduled for removal.
If you previously configured it:

1. stop using `roadmap sync`, `roadmap git sync`, and provider link commands;
2. remove Roadmap-specific tokens from shell profiles, environment managers,
   keyrings, and CI secrets;
3. revoke tokens created solely for Roadmap in the provider's settings; and
4. use ordinary `git fetch`, merge or rebase, and `git push` to share canonical
   `.roadmap/` files.

Provider IDs already present in canonical content can remain ordinary text.
See the [0.2 public contract](architecture/public-contract-0.2.md).
