# Shell completion

The installed `roadmap` command uses Click's built-in completion for command
names, option names, and choice values. It does not complete workspace entity
IDs yet. Completion does not run a mutation or initialize a workspace.

Add the appropriate line to your shell configuration, then start a new shell:

```sh
# Bash 4.4+: ~/.bashrc
eval "$(_ROADMAP_COMPLETE=bash_source roadmap)"

# Zsh: ~/.zshrc
eval "$(_ROADMAP_COMPLETE=zsh_source roadmap)"

# Fish: ~/.config/fish/completions/roadmap.fish
_ROADMAP_COMPLETE=fish_source roadmap | source
```

Use the installed console entry point (`uv tool install roadmap-cli`), rather
than `python -m`, so Click can identify the executable. For development, use
`uv run --locked --extra dev roadmap` where the instructions invoke `roadmap`.

Try `roadmap <TAB>`, `roadmap issue <TAB>`, or
`roadmap issue create --priority <TAB>`. This works outside a workspace.

See [Click's completion documentation](https://click.palletsprojects.com/en/stable/shell-completion/).
