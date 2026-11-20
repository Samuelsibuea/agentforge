# agent/cli.py — interactive shell REA-grade: manifest commands, progress, cancellation.
import os, sys, json, time, signal
from datetime import datetime
from zoneinfo import ZoneInfo

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from agent.core import Agent
from agent.commands import COMMANDS

WIB = ZoneInfo("Asia/Jakarta")
TS = lambda: datetime.now(WIB).strftime("%H:%M:%S")

BANNER = r"""
  █████╗ ███████╗██████╗ ███████╗███╗   ██╗████████╗███████╗██╗  ██╗
 ██╔══██╗██╔════╝██╔══██╗██╔════╝████╗  ██║╚══██╔══╝██╔════╝╚██╗██╔╝
 ███████║█████╗  ██║  ██║█████╗  ██╔██╗ ██║   ██║   █████╗   ╚███╔╝
 ██╔══██║██╔══╝  ██║  ██║██╔══╝  ██║╚██╗██║   ██║   ██╔══╝   ██╔██╗
 ██║  ██║██║     ██████╔╝███████╗██║ ╚████║   ██║   ███████╗██╔╝ ██║
 ╚═╝  ╚═╝╚═╝     ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
"""

STYLE = Style.from_dict({
    "prompt": "#5c9dff bold",
    "banner": "#7ee787",
    "status": "#8b949e",
    "accent": "#d2a8ff",
    "warn": "#ffa657",
})


def status_line(agent):
    skill = getattr(agent, "skill", "research")
    return (f"model={agent.model}  skill={skill}  "
            f"mem={len(agent.memory)}  tools={len(agent.run_log)}  "
            f"{TS()} WIB")


def progress(msg):
    """Progress ke stderr — stdout tetap bersih untuk jawaban (REA cliProgress.ts pattern)."""
    sys.stderr.write(f"\r  {msg:<70}\n")
    sys.stderr.flush()


def run_task(agent, task):
    """Satu task dengan cancellation + progress tool-call."""
    import agent.core as core

    orig_llm = agent.llm

    def llm_with_progress(system, messages, tools=True):
        progress(f"[llm] turn {len(messages)} → {agent.model}")
        return orig_llm(system, messages, tools)

    agent.llm = llm_with_progress
    try:
        out = agent.run(task, skill=getattr(agent, "skill", "research"))
    finally:
        agent.llm = orig_llm
    return out


def main():
    agent = Agent()
    agent.skill = "research"

    if len(sys.argv) > 1:  # single-shot: python -m agent.cli "topik"
        task = " ".join(sys.argv[1:])
        out = run_task(agent, task)
        print(out.get("answer") or out.get("error"))
        return

    # interactive
    print(f"\033[32m{BANNER}\033[0m")
    print(f"  AgentForge · {TS()} WIB · model {agent.model} · /help untuk perintah · Ctrl+C batalkan, 2x keluar\n")

    completer = WordCompleter([f"/{n}" for n in COMMANDS] + ["/skill research", "/skill coding", "/skill summarize"],
                              ignore_case=True, sentence=False)
    session = PromptSession(history=FileHistory(os.path.expanduser("~/.agentforge_history")),
                            completer=completer, complete_while_typing=True, style=STYLE)

    last_interrupt = 0.0
    while True:
        skill = getattr(agent, "skill", "research")
        prompt_tokens = [("fg:ansibrightblue bold", "➜ "),
                         ("fg:ansibrightgreen bold", " agentforge"),
                         ("", ":"),
                         ("fg:ansiyellow bold", f" {skill}"),
                         ("fg:ansibrightblue bold", " ❯ ")]
        try:
            line = session.prompt(prompt_tokens,
                                  bottom_toolbar=status_line(agent),
                                  rprompt=f"\033[90m{TS()} WIB\033[0m",
                                  multiline=False).strip()
        except KeyboardInterrupt:
            now = time.time()
            if now - last_interrupt < 2.0:
                print("\n  keluar.")
                return
            last_interrupt = now
            progress("tekan Ctrl+C lagi dalam 2 detik untuk keluar")
            continue
        except EOFError:
            print("\n  keluar.")
            return
        if not line:
            continue

        if line.startswith("/"):
            parts = line.split(None, 1)
            name = parts[0][1:].lower()
            args = parts[1] if len(parts) > 1 else ""
            if name == "exit":
                break
            cmd = COMMANDS.get(name)
            if cmd:
                try:
                    print("\n" + cmd["run"](agent, args) + "\n")
                except Exception as e:
                    print(f"\n  \033[31m✗ /{name}: {e}\033[0m\n")
            else:
                print(f"\n  perintah '{name}' tidak ada. /help untuk daftar.\n")
            continue

        # task → agent
        print()
        try:
            out = run_task(agent, line)
        except KeyboardInterrupt:
            progress("[cancel] tool call dibatalkan — sesi tetap hidup")
            continue
        if out.get("ok"):
            progress(f"[✓] jawaban {len(out.get('answer',''))} char"
                     + (f" · artefak {out['artefak']}" if out.get("artefak") else ""))
            print(f'\033[35m{out["answer"]}\033[0m\n')
        else:
            progress(f"[✗] {out.get('error')}")
            print()


if __name__ == "__main__":
    main()
