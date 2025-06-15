# Provides Bash tab completion for the `http` command by suggesting options when the current word starts with a dash.
#
# Globals:
#
# * COMP_WORDS: Array of words in the current command line.
# * COMP_CWORD: Index of the word the cursor is on.
#
# Arguments:
#
# None.
#
# Outputs:
#
# May call functions that set `COMPREPLY` for Bash completion.
#
# Example:
#
# When typing `http -` and pressing Tab, this function suggests available options.


_http_complete() {
    local cur_word=${COMP_WORDS[COMP_CWORD]}
    local prev_word=${COMP_WORDS[COMP_CWORD - 1]}

    if [[ "$cur_word" == -*  ]]; then
        _http_complete_options "$cur_word"
    fi
}

complete -o default -F _http_complete http

# Generates Bash completion suggestions for `http` command options matching the current word.
#
# Arguments:
#
# * cur_word: The current word being completed on the command line.
#
# Globals:
#
# * COMPREPLY: Populated with matching option completions for Bash to display.
#
# Outputs:
#
# * None.
#
# Example:
#
# ```bash
# _http_complete_options --ver
# # COMPREPLY will contain '--version'
# ```
_http_complete_options() {
    local cur_word=$1
    local options="-j --json -f --form --pretty -s --style -p --print
    -v --verbose -h --headers -b --body -S --stream -o --output -d --download
    -c --continue --session --session-read-only -a --auth --auth-type --proxy
    --follow --verify --cert --cert-key --timeout --check-status --ignore-stdin
    --help --version --traceback --debug"
    COMPREPLY=( $( compgen -W "$options" -- "$cur_word" ) )
}
