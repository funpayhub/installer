#!/usr/bin/env bash
# .hub installer for Linux (Arch Linux, Debian, Ubuntu)
#
# Interactive:
#   bash install.sh                          install on this machine
#   bash install.sh --ssh user@host          install on a remote Linux server
#   bash install.sh --ssh user@host --port 2222
#   bash install.sh --ref v0.6.0             install a specific tag or branch (default: latest tag)
#
# Non-interactive (used by the GUI installer), enabled by --token:
#   bash install.sh --token T --password W [--proxy P] [--dir D] [--service yes|no] [--sudo-password-stdin]
#   bash install.sh --check --token T ...    only prepare the system and check the folder, proxy and token
# --password is the password for the Telegram bot, written to config/telegram.toml; it is required
#
# Exit codes: 10 proxy does not work, 11 token is invalid, 12 Telegram is unreachable.
# Lines starting with @@ are read by the GUI: @@DIR_STATE=, @@BOT=, @@DIR=, @@SERVICE

set -euo pipefail

REPO_URL="https://github.com/funpayhub/funpayhub"
SERVICE_NAME="dothub"

REF=""
SSH_TARGET=""
SSH_PORT="22"
OPT_TOKEN=""
OPT_PASSWORD=""
OPT_PROXY=""
OPT_DIR=""
OPT_SERVICE="no"
CHECK_ONLY=0
READ_SUDO_PASSWORD=0
SUDO_PASSWORD=""

if [ -t 1 ]; then
    C_RESET="$(printf '\033[0m')"
    C_RED="$(printf '\033[31m')"
    C_GREEN="$(printf '\033[32m')"
    C_YELLOW="$(printf '\033[33m')"
    C_CYAN="$(printf '\033[36m')"
    # on a terminal the tools show their own progress
    Q_APT="" Q_GIT="" Q_UV="" Q_CURL="--progress-bar"
else
    C_RESET="" C_RED="" C_GREEN="" C_YELLOW="" C_CYAN=""
    Q_APT="-qq" Q_GIT="-q" Q_UV="-q" Q_CURL="-s"
fi

info() { printf "${C_CYAN}(・ω・)${C_RESET} %s\n" "$*"; }
ok()   { printf "${C_GREEN}(＾▽＾)${C_RESET} %s\n" "$*"; }
warn() { printf "${C_YELLOW}(ಠ_ಠ)${C_RESET} %s\n" "$*"; }
die()  { printf "${C_RED}(x_x)${C_RESET} %s\n" "$*" >&2; exit 1; }

# Reads from the terminal, so the script also works as `curl ... | bash`.
ask() {
    printf '%s' "$1" > /dev/tty
    IFS= read -r REPLY < /dev/tty || REPLY=""
    [ -n "$REPLY" ] || REPLY="${2:-}"
}

confirm() {
    local hint="[y/N]"
    [ "$2" = y ] && hint="[Y/n]"
    ask "$1 $hint " "$2"
    case "$REPLY" in [yYдД]*) return 0 ;; *) return 1 ;; esac
}

as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif [ -n "$SUDO_PASSWORD" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S -p '' "$@"
    else
        sudo "$@"
    fi
}

usage() {
    cat <<'EOF'
Usage: install.sh [--ssh user@host] [--port 22] [--ref <tag-or-branch>]
       install.sh --token T --password W [--proxy P] [--dir D] [--service yes|no] [--sudo-password-stdin] [--check]
EOF
}


# ---------- remote install ----------

run_via_ssh() {
    [ -f "$0" ] || die "Для установки по SSH скачайте install.sh и запустите его как файл"
    info "Копирую установщик на $SSH_TARGET"
    scp -q -P "$SSH_PORT" "$0" "$SSH_TARGET:.dothub-install.sh"
    local ref_arg=""
    [ -n "$REF" ] && ref_arg="--ref $REF"
    exec ssh -t -p "$SSH_PORT" "$SSH_TARGET" "bash .dothub-install.sh $ref_arg; rm -f .dothub-install.sh"
}


# ---------- system ----------

detect_distro() {
    [ -r /etc/os-release ] || die "Не удалось определить дистрибутив"
    . /etc/os-release
    case " ${ID:-} ${ID_LIKE:-} " in
        *" arch "*) DISTRO=arch ;;
        *" debian "* | *" ubuntu "*) DISTRO=debian ;;
        *) die "Дистрибутив ${PRETTY_NAME:-unknown} не поддерживается. Поддерживаются Arch Linux, Debian и Ubuntu" ;;
    esac

    if [ "$(id -u)" -ne 0 ] && ! command -v sudo > /dev/null; then
        die "Запустите установщик от root или установите sudo"
    fi
}

install_packages() {
    local missing=""
    for cmd in git curl; do
        command -v "$cmd" > /dev/null || missing="$missing $cmd"
    done
    [ -n "$missing" ] || return 0

    info "Устанавливаю:$missing"
    case "$DISTRO" in
        debian)
            as_root apt-get update $Q_APT
            as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y $Q_APT $missing ca-certificates
            ;;
        arch)
            as_root pacman -Syu --needed --noconfirm $missing
            ;;
    esac
}

install_uv() {
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv > /dev/null; then
        info "Устанавливаю uv"
        curl -LSf $Q_CURL https://astral.sh/uv/install.sh | sh
    else
        info "Обновляю uv"
        uv self update
    fi
    UV="$(command -v uv)"
}


# ---------- folder, proxy and token ----------

resolve_dir() {
    INSTALL_DIR="${1/#\~/$HOME}"
    case "$INSTALL_DIR" in /*) ;; *) INSTALL_DIR="$PWD/$INSTALL_DIR" ;; esac
}

dir_state() {
    if [ -f "$INSTALL_DIR/launcher.py" ]; then
        echo installed
    elif [ -d "$INSTALL_DIR" ] && [ -n "$(ls -A "$INSTALL_DIR")" ]; then
        echo notempty
    else
        echo empty
    fi
}

make_install_dir() {
    mkdir -p "$INSTALL_DIR" || return 1
    INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
}

tg_curl() {
    if [ -n "$PROXY" ]; then
        curl --proxy "$PROXY" "$@"
    else
        curl "$@"
    fi
}

# Returns 1 if the proxy does not work.
check_proxy() {
    case "$PROXY" in
        socks5://* | http://* | https://*) ;;
        *) warn "Прокси должен начинаться с socks5://, http:// или https://"; return 1 ;;
    esac

    local code
    code="$(tg_curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://api.telegram.org || true)"
    if [ "$code" = 000 ]; then
        warn "Не удалось подключиться к Telegram через этот прокси"
        return 1
    fi
    ok "Прокси работает"
}

# Returns 1 if the token is invalid, 2 if Telegram is unreachable, 3 on an unexpected answer.
check_token() {
    if ! [[ "$TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
        warn "Это не похоже на токен. Его можно получить у @BotFather"
        return 1
    fi

    local resp code body
    resp="$(tg_curl -s --max-time 15 -w '\n%{http_code}' "https://api.telegram.org/bot$TOKEN/getMe" || true)"
    code="${resp##*$'\n'}"
    body="${resp%$'\n'*}"
    case "$code" in
        200)
            BOT_NAME="$(printf '%s' "$body" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')"
            ok "Токен подходит, бот @$BOT_NAME"
            return 0
            ;;
        401 | 404) warn "Telegram не принял токен, проверьте его"; return 1 ;;
        000) warn "Не удалось подключиться к Telegram. Возможно, нужен прокси"; return 2 ;;
        *) warn "Неожиданный ответ Telegram (HTTP $code)"; return 3 ;;
    esac
}

ask_install_dir() {
    local default="$HOME/dothub"
    while :; do
        ask "Куда установить .hub? [$default]: " "$default"
        resolve_dir "$REPLY"
        case "$(dir_state)" in
            installed) warn ".hub уже установлен в $INSTALL_DIR"; confirm "Всё равно установить сюда?" n || continue ;;
            notempty) warn "Папка $INSTALL_DIR не пустая"; confirm "Всё равно установить сюда?" n || continue ;;
        esac
        if make_install_dir; then
            return
        fi
        warn "Не удалось создать папку $INSTALL_DIR"
    done
}

ask_proxy() {
    while :; do
        ask "Прокси для Telegram (socks5://user:pass@host:port или http://...), Enter — без прокси: "
        PROXY="$REPLY"
        if [ -z "$PROXY" ] || check_proxy; then
            return 0
        fi
    done
}

# Returns 1 when Telegram is unreachable, so the proxy can be asked again.
ask_token() {
    local rc
    while :; do
        ask "Токен Telegram-бота (выглядит так: 123456789:AAHg7K...): "
        TOKEN="$REPLY"
        rc=0
        check_token || rc=$?
        case "$rc" in
            0) return 0 ;;
            2) return 1 ;;
        esac
    done
}

# Telegram trims messages, so a password with spaces at the ends could never be typed to the bot.
trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    printf '%s' "${s%"${s##*[![:space:]]}"}"
}

ask_password() {
    while :; do
        ask "Пароль для доступа к боту (его нужно будет отправить боту при первом обращении): "
        PASSWORD="$(trim "$REPLY")"
        [ -z "$PASSWORD" ] || return 0
        warn "Пароль обязателен"
    done
}

check_options() {
    resolve_dir "${OPT_DIR:-$HOME/dothub}"
    echo "@@DIR_STATE=$(dir_state)"

    PASSWORD="$(trim "$OPT_PASSWORD")"
    [ -n "$PASSWORD" ] || die "Не указан пароль для доступа к боту (--password)"
    PROXY="$OPT_PROXY"
    TOKEN="$OPT_TOKEN"
    if [ -n "$PROXY" ] && ! check_proxy; then
        exit 10
    fi
    local rc=0
    check_token || rc=$?
    case "$rc" in
        0) echo "@@BOT=$BOT_NAME" ;;
        1) exit 11 ;;
        2) exit 12 ;;
        *) exit 13 ;;
    esac
}


# ---------- install ----------

fetch_source() {
    if [ -z "$REF" ]; then
        REF="$(git ls-remote --tags --refs --sort=-v:refname "$REPO_URL" 'v*' | sed -n '1s#.*refs/tags/##p')"
        [ -n "$REF" ] || die "Не удалось получить список версий .hub"
    fi

    info "Скачиваю .hub $REF"
    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR"' EXIT
    SRC="$TMP_DIR/src"
    git -c advice.detachedHead=false clone $Q_GIT --depth 1 --branch "$REF" "$REPO_URL" "$SRC"
    [ -f "$SRC/bootstrap.py" ] || die "Версия $REF не поддерживается установщиком"
}

install_release() {
    local requires
    requires="$(sed -n 's/^requires-python *= *"\(.*\)"/\1/p' "$SRC/pyproject.toml")"

    info "Устанавливаю Python ${requires:-3}"
    "$UV" venv $Q_UV --clear --python "${requires:-3}" "$INSTALL_DIR/.venv"

    info "Устанавливаю .hub и его зависимости, это может занять пару минут"
    cd "$INSTALL_DIR"
    HUBPLATFORM_UV_BIN="$UV" "$INSTALL_DIR/.venv/bin/python" - "$SRC" <<'EOF'
import sys
import shutil
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import bootstrap
import launcher

bootstrap.setup_logging(Path('logs'))
bootstrap.install(Path('releases').resolve())
shutil.copy2(launcher.__file__, 'launcher.py')
EOF
    rm -rf "$TMP_DIR"
}

toml_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

write_config() {
    local cfg="$INSTALL_DIR/config/telegram.toml"
    mkdir -p "$INSTALL_DIR/config"
    if [ -f "$cfg" ]; then
        cp "$cfg" "$cfg.bak"
        warn "Старый $cfg сохранён в telegram.toml.bak"
    fi
    printf '[bot]\ntoken = "%s"\npassword = "%s"\nproxy = "%s"\n' \
        "$TOKEN" "$(toml_escape "$PASSWORD")" "$(toml_escape "$PROXY")" > "$cfg"
    chmod 600 "$cfg"
}

write_start_script() {
    cat > "$INSTALL_DIR/start.sh" <<EOF
#!/bin/sh
cd "\$(dirname "\$0")"
export HUBPLATFORM_UV_BIN="$UV"
exec .venv/bin/python launcher.py "\$@"
EOF
    chmod +x "$INSTALL_DIR/start.sh"
}

want_service() {
    if [ ! -d /run/systemd/system ]; then
        [ "$INTERACTIVE" = 1 ] || [ "$OPT_SERVICE" = no ] || warn "systemd не найден, служба не установлена"
        return 1
    fi
    if [ "$INTERACTIVE" = 1 ]; then
        confirm "Установить .hub как службу systemd (автозапуск и перезапуск при сбоях)?" y
    else
        [ "$OPT_SERVICE" = yes ]
    fi
}

install_service() {
    local unit
    unit="$(mktemp)"
    cat > "$unit" <<EOF
[Unit]
Description=.hub
Wants=network-online.target
After=network-online.target

[Service]
User=$(id -un)
WorkingDirectory=$INSTALL_DIR
ExecStart="$INSTALL_DIR/start.sh"
Environment=PYTHONUNBUFFERED=1
KillSignal=SIGINT
TimeoutStopSec=150
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    as_root install -m 644 "$unit" "/etc/systemd/system/$SERVICE_NAME.service"
    rm -f "$unit"
    as_root systemctl daemon-reload
    as_root systemctl enable -q "$SERVICE_NAME"
    as_root systemctl restart "$SERVICE_NAME"
}


# ---------- main ----------

while [ $# -gt 0 ]; do
    case "$1" in
        --ssh) SSH_TARGET="${2:?}"; shift 2 ;;
        --port) SSH_PORT="${2:?}"; shift 2 ;;
        --ref) REF="${2:?}"; shift 2 ;;
        --token) OPT_TOKEN="${2:?}"; shift 2 ;;
        --password) OPT_PASSWORD="${2:-}"; shift 2 ;;
        --proxy) OPT_PROXY="${2:-}"; shift 2 ;;
        --dir) OPT_DIR="${2:?}"; shift 2 ;;
        --service) OPT_SERVICE="${2:?}"; shift 2 ;;
        --check) CHECK_ONLY=1; shift ;;
        --sudo-password-stdin) READ_SUDO_PASSWORD=1; shift ;;
        -h | --help) usage; exit 0 ;;
        *) usage; die "Неизвестный аргумент: $1" ;;
    esac
done

[ -z "$SSH_TARGET" ] || run_via_ssh

if [ "$READ_SUDO_PASSWORD" = 1 ]; then
    IFS= read -r SUDO_PASSWORD || true
fi

INTERACTIVE=1
[ -z "$OPT_TOKEN" ] || INTERACTIVE=0

[ "$INTERACTIVE" = 0 ] || printf "\n${C_CYAN}(◕‿◕)${C_RESET} Привет! Это установщик .hub\n\n"

detect_distro
install_packages

if [ "$INTERACTIVE" = 1 ]; then
    ask_install_dir
    while :; do
        ask_proxy
        ask_token && break
    done
    ask_password
else
    check_options
    [ "$CHECK_ONLY" = 0 ] || exit 0
    make_install_dir || die "Не удалось создать папку $INSTALL_DIR"
fi

install_uv
fetch_source
install_release
write_config
write_start_script

echo ""
ok ".hub установлен в $INSTALL_DIR"
echo "@@DIR=$INSTALL_DIR"
if want_service; then
    install_service
    echo "@@SERVICE=$SERVICE_NAME"
    ok ".hub запущен как служба $SERVICE_NAME. Напишите боту @$BOT_NAME в Telegram и отправьте ему пароль"
    info "Логи: journalctl -u $SERVICE_NAME -f"
    info "Остановить: sudo systemctl stop $SERVICE_NAME"
else
    info "Запуск: $INSTALL_DIR/start.sh"
    if [ "$INTERACTIVE" = 1 ] && confirm "Запустить .hub сейчас?" y; then
        exec "$INSTALL_DIR/start.sh"
    fi
fi
