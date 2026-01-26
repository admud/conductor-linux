"""Shell completion generators."""

from __future__ import annotations


def generate_completions(shell: str) -> str:
    """Generate shell completions for the given shell."""
    if shell == "bash":
        return generate_bash_completions()
    elif shell == "zsh":
        return generate_zsh_completions()
    elif shell == "fish":
        return generate_fish_completions()
    else:
        return f"# Unknown shell: {shell}"


def generate_bash_completions() -> str:
    """Generate bash completions."""
    return '''# CDL bash completions
# Add to ~/.bashrc: eval "$(cdl completions bash)"

_cdl_completions() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    commands="add list spawn status attach diff merge logs kill killall pick completions pr s a l k d"

    case "${prev}" in
        cdl)
            COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
            return 0
            ;;
        add)
            # No completion for URLs
            return 0
            ;;
        spawn)
            # Complete repo names
            local repos=$(cdl list --json 2>/dev/null | jq -r '.repos | keys[]' 2>/dev/null)
            COMPREPLY=( $(compgen -W "${repos}" -- ${cur}) )
            return 0
            ;;
        attach|a|logs|l|kill|k|diff|d|merge)
            # Complete agent numbers
            local agents=$(cdl status --json 2>/dev/null | jq -r '.agents | keys[]' 2>/dev/null)
            COMPREPLY=( $(compgen -W "${agents}" -- ${cur}) )
            return 0
            ;;
        completions)
            COMPREPLY=( $(compgen -W "bash zsh fish" -- ${cur}) )
            return 0
            ;;
        pr)
            COMPREPLY=( $(compgen -W "create view merge" -- ${cur}) )
            return 0
            ;;
        --tool)
            COMPREPLY=( $(compgen -W "delta difftastic diff-so-fancy" -- ${cur}) )
            return 0
            ;;
    esac

    # Complete flags
    case "${cur}" in
        -*)
            local flags="-h --help -t --task -y --auto-accept -n --no-auto-accept -c --cleanup -f --follow --json -j --base --title --body --fill --draft --web --merge --squash --rebase --delete-branch --auto"
            COMPREPLY=( $(compgen -W "${flags}" -- ${cur}) )
            return 0
            ;;
    esac
}

complete -F _cdl_completions cdl
'''


def generate_zsh_completions() -> str:
    """Generate zsh completions."""
    return '''#compdef cdl
# CDL zsh completions
# Add to ~/.zshrc: eval "$(cdl completions zsh)"

_cdl() {
    local -a commands
    commands=(
        'add:Add/clone a repository'
        'list:List repos and agents'
        'spawn:Spawn a new agent'
        'status:Show agent status'
        's:Show agent status (alias)'
        'attach:Attach to agent terminal'
        'a:Attach to agent terminal (alias)'
        'diff:Show changes made by agents'
        'd:Show changes (alias)'
        'merge:Push agent branch to origin'
        'logs:Show agent terminal output'
        'l:Show logs (alias)'
        'kill:Kill an agent'
        'k:Kill an agent (alias)'
        'killall:Kill all agents'
        'pick:Interactive agent picker'
        'completions:Generate shell completions'
        'pr:Pull request workflow'
    )

    _arguments -C \\
        '1: :->command' \\
        '*: :->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $words[2] in
                spawn)
                    if (( CURRENT == 3 )); then
                        local repos=(${(f)"$(cdl list --json 2>/dev/null | jq -r '.repos | keys[]' 2>/dev/null)"})
                        _describe 'repository' repos
                    fi
                    ;;
                attach|a|logs|l|kill|k|diff|d|merge)
                    local agents=(${(f)"$(cdl status --json 2>/dev/null | jq -r '.agents[] | "\\(.number):\\(.repo)/\\(.branch)"' 2>/dev/null)"})
                    _describe 'agent' agents
                    ;;
                completions)
                    _values 'shell' bash zsh fish
                    ;;
                pr)
                    if (( CURRENT == 3 )); then
                        _values 'pr subcommand' create view merge
                    fi
                    ;;
            esac
            ;;
    esac
}

compdef _cdl cdl
'''


def generate_fish_completions() -> str:
    """Generate fish completions."""
    return '''# CDL fish completions
# Add to ~/.config/fish/completions/cdl.fish

# Disable file completion by default
complete -c cdl -f

# Commands
complete -c cdl -n "__fish_use_subcommand" -a "add" -d "Add/clone a repository"
complete -c cdl -n "__fish_use_subcommand" -a "list" -d "List repos and agents"
complete -c cdl -n "__fish_use_subcommand" -a "spawn" -d "Spawn a new agent"
complete -c cdl -n "__fish_use_subcommand" -a "status s" -d "Show agent status"
complete -c cdl -n "__fish_use_subcommand" -a "attach a" -d "Attach to agent terminal"
complete -c cdl -n "__fish_use_subcommand" -a "diff d" -d "Show changes made by agents"
complete -c cdl -n "__fish_use_subcommand" -a "merge" -d "Push agent branch to origin"
complete -c cdl -n "__fish_use_subcommand" -a "logs l" -d "Show agent terminal output"
complete -c cdl -n "__fish_use_subcommand" -a "kill k" -d "Kill an agent"
complete -c cdl -n "__fish_use_subcommand" -a "killall" -d "Kill all agents"
complete -c cdl -n "__fish_use_subcommand" -a "pick" -d "Interactive agent picker"
complete -c cdl -n "__fish_use_subcommand" -a "completions" -d "Generate shell completions"
complete -c cdl -n "__fish_use_subcommand" -a "pr" -d "Pull request workflow"

# Completions subcommand
complete -c cdl -n "__fish_seen_subcommand_from completions" -a "bash zsh fish"

# Common flags
complete -c cdl -s h -l help -d "Show help"
complete -c cdl -s j -l json -d "Output in JSON format"

# spawn flags
complete -c cdl -n "__fish_seen_subcommand_from spawn" -s t -l task -d "Task for the agent"
complete -c cdl -n "__fish_seen_subcommand_from spawn" -s y -l auto-accept -d "Enable auto-accept mode"
complete -c cdl -n "__fish_seen_subcommand_from spawn" -s n -l no-auto-accept -d "Disable auto-accept mode"

# logs flags
complete -c cdl -n "__fish_seen_subcommand_from logs l" -s f -l follow -d "Follow output (like tail -f)"
complete -c cdl -n "__fish_seen_subcommand_from logs l" -s n -l lines -d "Number of lines"

# kill/killall flags
complete -c cdl -n "__fish_seen_subcommand_from kill k killall" -s c -l cleanup -d "Also remove worktree"

# diff flags
complete -c cdl -n "__fish_seen_subcommand_from diff d" -l tool -d "Diff tool to use"

# pr flags
complete -c cdl -n "__fish_seen_subcommand_from pr" -a "create view merge"
complete -c cdl -n "__fish_seen_subcommand_from pr create" -l base -d "Base branch"
complete -c cdl -n "__fish_seen_subcommand_from pr create" -l title -d "PR title"
complete -c cdl -n "__fish_seen_subcommand_from pr create" -l body -d "PR body"
complete -c cdl -n "__fish_seen_subcommand_from pr create" -l fill -d "Auto-fill title/body"
complete -c cdl -n "__fish_seen_subcommand_from pr create" -l draft -d "Create as draft"
complete -c cdl -n "__fish_seen_subcommand_from pr create" -l web -d "Open PR in browser"
complete -c cdl -n "__fish_seen_subcommand_from pr view" -l web -d "Open PR in browser"
complete -c cdl -n "__fish_seen_subcommand_from pr merge" -l merge -d "Merge commit"
complete -c cdl -n "__fish_seen_subcommand_from pr merge" -l squash -d "Squash and merge"
complete -c cdl -n "__fish_seen_subcommand_from pr merge" -l rebase -d "Rebase and merge"
complete -c cdl -n "__fish_seen_subcommand_from pr merge" -l delete-branch -d "Delete branch after merge"
complete -c cdl -n "__fish_seen_subcommand_from pr merge" -l auto -d "Enable auto-merge"
'''
