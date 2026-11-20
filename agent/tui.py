# agent/tui.py — TUI AgentForge: header gradient, sidebar status live, chat panel, footer WIB.
import os, sys, json, threading, time
from datetime import datetime
from zoneinfo import ZoneInfo

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.widgets import Frame
from prompt_toolkit.styles import Style
from prompt_toolkit.buffer import Buffer

from agent.core import Agent

WIB = ZoneInfo("Asia/Jakarta")
TS = lambda: datetime.now(WIB).strftime("%H:%M:%S")

# ptk 3.0.52 default ke 8-bit depth meski terminal truecolor — bg #0d1117
# terkonversi ke 256-palette #233 (#1c1c1c). Paksa 24-bit di sini.
os.environ.setdefault("PROMPT_TOOLKIT_COLOR_DEPTH", "DEPTH_24_BIT")


class TUI:
    def __init__(self, agent):
        self.agent = agent
        # log: list[(style_class, text)]
        self.log = [("", "AgentForge TUI — ketik task lalu Enter. /help untuk perintah."), ("", "")]
        self.turn = 0
        self.tools = 0
        self.veritas = 0
        self.running = False
        self._lock = threading.Lock()

        self.input_buf = Buffer(multiline=False)

    # ── fragments (dipanggil setiap render) ────────────
    def _chat_frag(self):
        out = []
        for cls, txt in reversed(self.log[-30:]):
            out.append((f"class:{cls}" if cls else "class:chat", txt))
            out.append(("", "\n"))
        if self.running:
            out.append(("class:cursor", "▌"))
        return out

    def _status_frag(self):
        k = getattr(self.agent, "keyring", None)
        kname = None
        if k:
            kname = k.idx.get("rotation", {}).get("kei")
            if not kname:
                for n, e in k.idx.get("keys", {}).items():
                    if e.get("provider") == "kei" and e.get("active", True):
                        kname = n
                        break
        fp = k.idx["keys"][kname].get("fingerprint", "") if (k and kname and kname in k.idx["keys"]) else ""
        rows = [
            ("st-head", "STATUS", ""),
            ("", "", ""),
            ("st-k", "model  ", f"{self.agent.model}"),
            ("", "", ""),
            ("st-k", "skill  ", f"{getattr(self.agent,'skill','research')}"),
            ("", "", ""),
            ("st-k", "key    ", f"{kname or 'config'}  {fp}"),
            ("", "", ""),
            ("st-k", "memory ", f"{len(self.agent.memory)} pesan"),
            ("", "", ""),
            ("st-k", "turn   ", f"{self.turn}"),
            ("", "", ""),
            ("st-k", "tools  ", f"{self.tools} call"),
            ("", "", ""),
            ("st-k", "veritas", f"{self.veritas} check"),
        ]
        out = []
        for kcls, ktxt, vtxt in rows:
            if ktxt:
                out.append((f"class:{kcls}" if kcls else "", ktxt))
            if vtxt:
                out.append(("class:st-v", vtxt))
            out.append(("", "\n"))
        return out

    def _footer_frag(self):
        return [
            ("class:foot", f" WIB {TS()} "),
            ("class:foot-dim", "│"),
            ("class:foot-ok", " veritas ON "),
            ("class:foot-dim", "│"),
            ("class:foot", f" turn {self.turn} · tools {self.tools} "),
            ("class:foot-dim", "│"),
            ("class:foot-warn", " /help "),
        ]

    # ── UI ─────────────────────────────────────────────
    def build(self):
        banner = (
            "  █████╗ ███████╗██████╗ ███████╗███╗   ██╗████████╗\n"
            "  ██╔══██╗██╔════╝██╔══██╗██╔════╝████╗  ██║╚══██╔══╝\n"
            "  ███████║█████╗  ██║  ██║█████╗  ██╔██╗ ██║   ██║   \n"
            "  ██╔══██║██╔══╝  ██║  ██║██╔══╝  ██║╚██╗██║   ██║   \n"
            "  ██║  ██║███████╗██████╔╝███████╗██║ ╚████║   ██║   \n"
            "  ╚═╝  ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   "
        )
        head_left = FormattedTextControl(
            text=[("class:head-banner", banner)])
        head_right = FormattedTextControl(text=[
            ("class:head-info",
             f"  {self.agent.model}  ·  kei  ·  WIB {TS()}\n"
             f"  skill {getattr(self.agent,'skill','research')}  ·  /help  ·  Ctrl+D keluar"),
        ])
        header = Frame(
            VSplit([
                Window(content=head_left, width=D(preferred=31)),
                Window(content=head_right),
            ]),
            style="class:head-frame",
        )

        sidebar = Frame(
            Window(content=FormattedTextControl(text=self._status_frag), wrap_lines=True),
            title=" STATUS ",
            style="class:side-frame",
            width=D(preferred=24),
        )

        chat = Frame(
            Window(content=FormattedTextControl(text=self._chat_frag), wrap_lines=True),
            title=" CHAT ",
            style="class:chat-frame",
        )

        prompt_lbl = FormattedTextControl(text=[
            ("class:prompt-arrow", " ➜ "),
            ("class:prompt-name", "agentforge"),
            ("class:prompt-sep", " : "),
        ])
        prompt_win = Window(content=BufferControl(buffer=self.input_buf), height=1)
        prompt_row = HSplit([
            Window(content=prompt_lbl, height=1, width=D(preferred=20)),
            prompt_win,
        ])
        prompt_frame = Frame(prompt_row, style="class:prompt-frame")

        footer = Window(content=FormattedTextControl(text=self._footer_frag),
                        height=1, style="class:foot")

        root = HSplit([
            header,
            VSplit([sidebar, chat], height=D(weight=1)),
            prompt_frame,
            footer,
        ])

        kb = KeyBindings()

        @kb.add("c-d")
        def _quit(event):
            event.app.exit()

        @kb.add("enter")
        def _go(event):
            task = self.input_buf.text.strip()
            if not task:
                return
            self.input_buf.text = ""
            if task in ("/quit", "/exit", "/q"):
                event.app.exit()
                return
            if task == "/help":
                with self._lock:
                    self.log += [
                        ("dim", "perintah:"),
                        ("cmd", "  /status  — model, endpoint, key, memory"),
                        ("cmd", "  /help    — daftar ini"),
                        ("cmd", "  /quit    — keluar"),
                        ("", "  task lain → dikirim ke agent (skill aktif)"),
                        ("", ""),
                    ]
                return
            if task == "/status":
                with self._lock:
                    k = self.agent.keyring
                    kn = None
                    if k:
                        kn = k.idx.get("rotation", {}).get("kei")
                        if not kn:
                            for n, e in k.idx.get("keys", {}).items():
                                if e.get("provider") == "kei" and e.get("active", True):
                                    kn = n
                                    break
                    self.log += [
                        ("dim", f"model {self.agent.model} · endpoint {self.agent.base_url}"),
                        ("dim", f"skill {getattr(self.agent,'skill','research')} · key {kn or 'config'} · memory {len(self.agent.memory)}"),
                        ("", ""),
                    ]
                return
            self._submit(task)

        def _clock():
            while True:
                time.sleep(1)
                self._safe_invalidate()
        threading.Thread(target=_clock, daemon=True).start()

        self.app = Application(
            layout=Layout(root, focused_element=prompt_win),
            key_bindings=kb, full_screen=True,
            style=self._style(), mouse_support=True,
        )
        return self.app

    def _style(self):
        return Style.from_dict({
            "": "bg:#0d1117 #c9d1d9",
            "head-frame": "bg:#161b22 #c9d1d9",
            "head-banner": "bg:#161b22 #58a6ff bold",
            "head-info": "bg:#161b22 #8b949e",
            "side-frame": "bg:#0d1117",
            "chat-frame": "bg:#0d1117",
            "prompt-frame": "bg:#161b22",
            "prompt-arrow": "#58a6ff bold",
            "prompt-name": "#3fb950 bold",
            "prompt-sep": "#8b949e",
            "st-head": "#bc8cff bold",
            "st-k": "#8b949e",
            "st-v": "#c9d1d9",
            "chat": "#c9d1d9",
            "q": "#58a6ff bold",
            "a": "#c9d1d9",
            "dim": "#8b949e",
            "cmd": "#3fb950",
            "err": "#f85149",
            "cursor": "#d29922",
            "foot": "bg:#161b22 #c9d1d9",
            "foot-dim": "bg:#161b22 #30363d",
            "foot-ok": "bg:#161b22 #3fb950",
            "foot-warn": "bg:#161b22 #d29922",
            "frame.border": "#30363d",
            "frame.label": "#8b949e",
            "window": "bg:#0d1117 #c9d1d9",
        })

    def _safe_invalidate(self):
        try:
            self.app.invalidate()
        except Exception:
            pass

    # ── task ───────────────────────────────────────────
    def _submit(self, task):
        with self._lock:
            self.log.append(("q", f"❯ {task}"))
            self.log.append(("", ""))
        self.running = True

        def worker():
            orig_llm = self.agent.llm
            try:
                def llm_hook(system, messages, tools=True):
                    with self._lock:
                        self.turn = len(messages)
                    return orig_llm(system, messages, tools)

                self.agent.llm = llm_hook
                out = self.agent.run(task, skill=getattr(self.agent, "skill", "research"), verbose=False)
                ans = out.get("answer") or out.get("error") or ""
                with self._lock:
                    for tr in out.get("trace", []):
                        if tr.get("type") == "tool":
                            self.log.append(("dim", f"  [tool] {tr['name']}({json.dumps(tr.get('args', {}), ensure_ascii=False)[:100]})"))
                            self.tools += 1
                        elif tr.get("type") == "veritas":
                            self.log.append(("cmd", f"  [veritas] {tr.get('tool')} -> {tr.get('verdict', tr.get('ok'))}"))
                            self.veritas += 1
                    self.log.append(("a", f"  {ans[:400]}"))
                    self.log.append(("", ""))
                    self.turn += 1
                self._safe_invalidate()
            except Exception as e:
                with self._lock:
                    self.log.append(("err", f"  error: {e}"))
                    self.log.append(("", ""))
                self._safe_invalidate()
            finally:
                self.agent.llm = orig_llm
                self.running = False
                self._safe_invalidate()

        threading.Thread(target=worker, daemon=True).start()


def main():
    agent = Agent("config.json")
    agent.skill = "research"
    TUI(agent).build().run()


if __name__ == "__main__":
    main()
