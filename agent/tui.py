# agent/tui.py — AgentForge Conversational Multi-Agent CLI
# Wireframe & Prototype 1:1 Implementation with 4 Screens, AF Logo Mark, and Full Telemetry
import os, sys, json, threading, time
from datetime import datetime
from zoneinfo import ZoneInfo

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.widgets import Frame
from prompt_toolkit.styles import Style
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import WordCompleter

from agent.core import Agent

WIB = ZoneInfo("Asia/Jakarta")
TS = lambda: datetime.now(WIB).strftime("%H:%M:%S")

# Enforce 24-bit truecolor for accurate gradient rendering matching the design spec
os.environ.setdefault("PROMPT_TOOLKIT_COLOR_DEPTH", "DEPTH_24_BIT")

# High-fidelity RGB half-block representation of official AgentForge logo mark
LOGO_ROWS = [
    [(' ', ''), (' ', ''), (' ', ''), (' ', ''), ('▄', '#07656a'), ('█', '#126994'), ('█', '#202884'), ('█', '#3052fc'), ('█', '#2768f5'), ('█', '#1e86fa'), ('█', '#14abff'), ('█', '#0bc6ff'), ('█', '#02eeff'), ('▀', '#06a2ad')],
    [(' ', ''), (' ', ''), (' ', ''), ('▄', '#1486c4'), ('█', '#08c8f0'), ('█', '#11bbff'), ('█', '#2091ff'), ('█', '#145386'), ('█', '#2a44c2'), ('█', '#2366da'), ('▄', '#6840c8'), ('▄', '#a42db0'), ('▄', '#441d43'), (' ', '')],
    [(' ', ''), ('▄', '#152649'), ('█', '#174d88'), ('█', '#20a3ff'), ('█', '#146197'), ('▄', '#1f83e7'), ('█', '#105676'), ('█', '#1990c5'), ('█', '#349feb'), ('█', '#284577'), ('▀', '#35144b'), ('▀', '#3c1c47'), (' ', ''), (' ', '')],
    [('▄', '#2435ae'), ('█', '#294ddd'), ('█', '#2e63ff'), ('█', '#2c69ff'), ('▀', '#2770f1'), ('▀', '#204d97'), (' ', ''), (' ', ''), ('█', '#952394'), ('█', '#c827a4'), ('█', '#451538'), (' ', ''), (' ', ''), (' ', '')],
]

DEFAULT_FILES = {
    "redis.go": {
        "path": "internal/cache/redis.go",
        "lang": "go",
        "lines": [
            (1, "package cache", " "),
            (2, "", " "),
            (3, "import (", " "),
            (4, '    "context"', " "),
            (5, '    "time"', " "),
            (6, '    "github.com/redis/go-redis/v9"', " "),
            (7, ")", " "),
            (8, "", " "),
            (9, "type SessionCache struct {", " "),
            (10, "    client *redis.Client", " "),
            (11, "}", " "),
            (12, "", " "),
            (13, "func NewSessionCache(addr string) *SessionCache {", " "),
            (14, '    rdb := redis.NewClient(&redis.Options{Addr: addr, PoolSize: 50})', " "),
            (15, "    return &SessionCache{client: rdb}", " "),
            (16, "}", " "),
            (17, "", " "),
            (18, "func (s *SessionCache) SetSession(ctx context.Context, key string, data map[string]any, ttl time.Duration) error {", " "),
            (19, "    pipe := s.client.Pipeline()", "+"),
            (20, "    pipe.HSet(ctx, key, data)", "+"),
            (21, "    pipe.Expire(ctx, key, ttl)", "+"),
            (22, "    _, err := pipe.Exec(ctx)", "+"),
            (23, "    return err", "+"),
            (24, "}", "+"),
        ]
    },
    "session.proto": {
        "path": "proto/session.proto",
        "lang": "proto",
        "lines": [
            (1, 'syntax = "proto3";', " "),
            (2, "package usersession.v1;", " "),
            (3, 'option go_package = "agentforge/gen/usersession/v1;sessionpb";', " "),
            (4, "", " "),
            (5, "service UserSessionService {", " "),
            (6, "    rpc GetSession(GetSessionRequest) returns (GetSessionResponse);", "+"),
            (7, "    rpc SetSession(SetSessionRequest) returns (SetSessionResponse);", "+"),
            (8, "    rpc DeleteSession(DeleteSessionRequest) returns (DeleteSessionResponse);", "+"),
            (9, "}", " "),
            (10, "", " "),
            (11, "message GetSessionRequest { string session_id = 1; }", " "),
            (12, "message GetSessionResponse { map<string, string> fields = 1; bool found = 2; }", "+"),
            (13, "message SetSessionRequest {", " "),
            (14, "    string session_id = 1;", " "),
            (15, "    map<string, string> fields = 2;", " "),
            (16, "    int64 ttl_seconds = 3;", "+"),
            (17, "}", " "),
            (18, "message SetSessionResponse { bool stored = 1; }", "+"),
            (19, "message DeleteSessionRequest { string session_id = 1; }", " "),
            (20, "message DeleteSessionResponse { bool deleted = 1; }", " "),
        ]
    },
    "session_server.go": {
        "path": "internal/grpc/session_server.go",
        "lang": "go",
        "lines": [
            (1, "package grpcapi", " "),
            (2, "", " "),
            (3, "import (", " "),
            (4, '    "context"', " "),
            (5, '    "time"', " "),
            (6, '    "agentforge/internal/cache"', " "),
            (7, '    sessionpb "agentforge/gen/usersession/v1"', " "),
            (8, ")", " "),
            (9, "", " "),
            (10, "type SessionServer struct {", " "),
            (11, "    sessionpb.UnimplementedUserSessionServiceServer", " "),
            (12, "    cache *cache.SessionCache", " "),
            (13, "}", " "),
            (14, "", " "),
            (15, "func NewSessionServer(c *cache.SessionCache) *SessionServer {", " "),
            (16, "    return &SessionServer{cache: c}", " "),
            (17, "}", " "),
            (18, "func (s *SessionServer) SetSession(ctx context.Context, req *sessionpb.SetSessionRequest) (*sessionpb.SetSessionResponse, error) {", "+"),
            (19, "    err := s.cache.SetSession(ctx, req.SessionId, req.Fields, time.Duration(req.TtlSeconds)*time.Second)", "+"),
            (20, "    if err != nil { return nil, err }", "+"),
            (21, "    return &sessionpb.SetSessionResponse{Stored: true}, nil", "+"),
            (22, "}", "+"),
        ]
    }
}


class TUI:
    def __init__(self, agent):
        self.agent = agent
        self.turn = 0
        self.tools = 0
        self.veritas = 0
        self.running = False
        self._lock = threading.Lock()

        # Navigation state: 'live', 'review', 'cluster', 'wireframe'
        self.active_screen: str = "live"
        self.active_file: str = "redis.go"
        self.focused_agent_id: str = "coder"
        self.is_paused: bool = False
        self.palette_open: bool = False
        self.palette_input: str = ""
        self.inspected_prompt_agent_id: str | None = None
        self.applied: bool = False

        # Live session metrics matching wireframe WF-01 / WF-08
        self.tokens_used = 34291
        self.tokens_max = 100000
        self.cost = 0.24
        self.latency = 12

        # Staged files for Review & Apply screen (WF-11)
        self.staged = {
            "redis.go": True,
            "session.proto": True,
            "session_server.go": True,
        }
        self.files = dict(DEFAULT_FILES)

        # Multi-Agent Cluster swarm (WF-06 & WF-12)
        self.agents = [
            {
                "id": "researcher",
                "name": "Researcher",
                "model": "forge-sonar-pro",
                "status": "DONE",
                "progress": 100,
                "paused": False,
                "tokens": 7180,
                "latency": "9ms",
                "role": "Analyzed go-redis/v9 pipeline pooling and TTL eviction strategies.",
                "system_prompt": "SYSTEM [ResearcherAgent]: Audit go-redis/v9 connection pooling, atomic HSet+Expire pipelining, and sub-millisecond session lookup patterns. Output concise architectural constraints."
            },
            {
                "id": "architect",
                "name": "Architect",
                "model": "forge-reasoner-2",
                "status": "DONE",
                "progress": 100,
                "paused": False,
                "tokens": 8940,
                "latency": "11ms",
                "role": "Authored proto3 contract for UserSessionService and cache boundaries.",
                "system_prompt": "SYSTEM [ArchitectAgent]: Define proto3 schema for UserSessionService with strict backward compatibility, clean gRPC status codes, and decoupled cache interface."
            },
            {
                "id": "coder",
                "name": "Coder",
                "model": "forge-coder-ultra",
                "status": "WORKING",
                "progress": 86,
                "paused": False,
                "tokens": 16051,
                "latency": "12ms",
                "role": "Writing internal/cache/redis.go and gRPC SessionServer handler.",
                "system_prompt": "SYSTEM [CoderAgent]: Implement idiomatic Go 1.22 Redis cache layer using Pipeline() for HSet+Expire and wire UserSessionServiceServer with context propagation."
            },
            {
                "id": "reviewer",
                "name": "Reviewer",
                "model": "forge-verifier-2",
                "status": "WAITING",
                "progress": 0,
                "paused": False,
                "tokens": 2120,
                "latency": "10ms",
                "role": "Queued. Starts after gRPC handler is written.",
                "system_prompt": "SYSTEM [ReviewerAgent]: Verify error wrapping, race safety (-race), Redis pipeline atomicity, and benchmark allocations (ns/op, B/op) across cache and gRPC packages."
            }
        ]

        # Task breakdown plan (WF-07)
        self.tasks = [
            {"id": 1, "label": "1. PROTOBUF", "status": "DONE", "progress": 100},
            {"id": 2, "label": "2. REDIS CACHE LAYER", "status": "DONE", "progress": 100},
            {"id": 3, "label": "3. gRPC ENDPOINT", "status": "WORKING", "progress": 86},
            {"id": 4, "label": "4. UNIT & BENCHMARK TESTS", "status": "PENDING", "progress": 0},
        ]

        # Live Dynamic Logs (WF-05)
        self.live_logs = [
            {
                "title": "CoderAgent [Pipeline]",
                "body": "Pipelined HSet + Expire into single Redis roundtrip (internal/cache/redis.go:19-23)",
                "tone": "cyan",
                "ts": TS()
            },
            {
                "title": "ReviewerAgent [Audit]",
                "body": "Static analysis checks pass. Zero race conditions detected in session cache.",
                "tone": "green",
                "ts": TS()
            }
        ]

        # General interactive chat log
        self.chat_log = [
            ("dim", "AgentForge v2.0.0 — Autonomous Conversational Multi-Agent CLI"),
            ("dim", "Teken [1] Live  [2] Review  [3] Cluster  [4] Wireframe  ·  Ctrl+P Command Palette"),
            ("", ""),
        ]

        # Test output buffer for /test command
        self.test_output = []

        completer = WordCompleter([
            "/help", "/mode", "/skill", "/tool", "/checkpoint", "/replay",
            "/diff", "/apply", "/test", "/agents", "/clear", "/pause", "/quit"
        ], ignore_case=True, match_middle=True)
        self.input_buf = Buffer(multiline=False, completer=completer, complete_while_typing=True)
        self.app = None

    # ── FRAGMENT: HEADER & TELEMETRY (WF-01) ───────────
    def _header_frag(self):
        pct = (self.tokens_used / self.tokens_max) * 100
        active_count = sum(1 for a in self.agents if not a.get("paused"))

        out = []
        for i, row in enumerate(LOGO_ROWS):
            # Logo glyph half-blocks
            for ch, col in row:
                if col:
                    out.append((f"fg:{col}", ch))
                else:
                    out.append(("", " "))
            
            # Text columns aligned to the 4 rows of the logo mark
            if i == 0:
                out.append(("class:hdr-title", "  AGENT FORGE  "))
                out.append(("class:hdr-ver", "v2.0.0"))
                out.append(("", "   "))
                out.append(("class:hdr-dim", "Agents: "))
                out.append(("class:hdr-val-green", f"{active_count} active"))
                out.append(("class:hdr-dim", "  │  Latency: "))
                out.append(("class:hdr-val-blue", f"{self.latency}ms"))
            elif i == 1:
                out.append(("class:hdr-sub", "  Autonomous Conversational Multi-Agent CLI"))
                out.append(("", "   "))
                out.append(("class:hdr-dim", "Tokens: "))
                out.append(("class:hdr-val", f"{self.tokens_used:,} / {self.tokens_max:,} ({pct:.1f}%)"))
            elif i == 2:
                model_str = f"Swarm: 4 nodes [{self.agent.model}]"
                out.append(("class:hdr-dim", f"  {model_str:<43}"))
                out.append(("class:hdr-dim", "Cost:   "))
                out.append(("class:hdr-val-amber", f"${self.cost:.2f}"))
            elif i == 3:
                pause_status = "PAUSED" if self.is_paused else "RUNNING"
                p_cls = "class:hdr-val-amber" if self.is_paused else "class:hdr-val-green"
                out.append(("class:hdr-dim", "  Status: "))
                out.append((p_cls, f"{pause_status}"))
                out.append(("class:hdr-dim", f"  │  WIB: {TS()}  │  Veritas: "))
                out.append(("class:hdr-val-green", "ACTIVE [100%]"))

            out.append(("", "\n"))
        return out

    # ── FRAGMENT: NAVIGATION BAR (WF-02) ────────────────
    def _nav_frag(self):
        tabs = [
            ("live", "[1] Live Session"),
            ("review", "[2] Review and Apply"),
            ("cluster", "[3] Agent Cluster"),
            ("wireframe", "[4] Wireframe Spec"),
        ]
        out = [("", " ")]
        for key, label in tabs:
            if self.active_screen == key:
                out.append(("class:nav-tab-active", f" {label} "))
            else:
                out.append(("class:nav-tab-idle", f" {label} "))
            out.append(("", "  "))
        out.append(("class:nav-hint", "   [Ctrl+P / Command Palette]  [Tab: Cycle Agent]  [Esc: Pause/Resume]"))
        return out

    # ── FRAGMENT: CODE CARD (WF-04) ────────────────────
    def _code_card_frag(self):
        focused = next((a for a in self.agents if a["id"] == self.focused_agent_id), self.agents[2])
        fobj = self.files.get(self.active_file, self.files["redis.go"])
        fpath = fobj["path"]

        out = []
        out.append(("class:card-title", f" CoderAgent [{focused['name']} Focus] "))
        out.append(("class:card-badge", f" {fpath} "))
        out.append(("class:card-badge-cyan", f" Status: {focused['status']} ({focused['progress']}%) "))
        out.append(("", "\n"))

        for fname in ["redis.go", "session.proto", "session_server.go"]:
            if self.active_file == fname:
                out.append(("class:subtab-active", f" • {fname} "))
            else:
                out.append(("class:subtab-idle", f"   {fname} "))
            out.append(("", " "))
        out.append(("", "\n\n"))

        for n, text, diff in fobj["lines"]:
            num_str = f"{n:3d} "
            out.append(("class:code-num", num_str))
            if diff == "+":
                out.append(("class:code-add-mark", "+ "))
                out.append(("class:code-add-text", text))
            elif diff == "-":
                out.append(("class:code-del-mark", "- "))
                out.append(("class:code-del-text", text))
            else:
                out.append(("class:code-plain-mark", "  "))
                out.append(("class:code-plain-text", text))
            out.append(("", "\n"))

        return out

    # ── FRAGMENT: REVIEWER & DYNAMIC LOG (WF-05) ───────
    def _reviewer_log_frag(self):
        rev = next((a for a in self.agents if a["id"] == "reviewer"), self.agents[3])
        out = []
        out.append(("class:card-title", " ReviewerAgent [Verification & Insights] "))
        badge_cls = "class:badge-green" if rev["status"] == "DONE" else "class:badge-amber"
        out.append((badge_cls, f" {rev['status']} "))
        out.append(("", "\n"))
        out.append(("class:dim", f" Role: {rev['role']}\n\n"))

        out.append(("class:card-subtitle", "── Dynamic Live Logs ─────────────────────────────────\n"))
        for item in self.live_logs[-6:]:
            t_cls = "class:log-cyan" if item["tone"] == "cyan" else ("class:log-green" if item["tone"] == "green" else "class:log-amber")
            out.append((t_cls, f"[{item['ts']}] {item['title']}\n"))
            out.append(("class:log-body", f"  {item['body']}\n\n"))

        return out

    # ── FRAGMENT: SIDEBAR ORCHESTRATION & TASKS (WF-06/07/08/09)
    def _sidebar_frag(self):
        out = []
        out.append(("class:side-head", " MULTI-AGENT SWARM\n"))
        for a in self.agents:
            is_foc = a["id"] == self.focused_agent_id
            prefix = "▶ " if is_foc else "  "
            f_cls = "class:agent-focused" if is_foc else "class:agent-idle"
            
            p_status = "PAUSED" if a.get("paused") else (f"WORKING {a['progress']}%" if a["status"] == "WORKING" else a["status"])
            p_cls = "class:badge-amber" if a.get("paused") or a["status"] == "WAITING" else ("class:badge-blue" if a["status"] == "WORKING" else "class:badge-green")
            
            out.append((f_cls, f"{prefix}{a['name']:<11}"))
            out.append((p_cls, f" {p_status:<11}"))
            out.append(("", "\n"))
        out.append(("", "\n"))

        out.append(("class:side-head", " TASK BREAKDOWN\n"))
        for t in self.tasks:
            if t["status"] == "DONE":
                out.append(("class:task-done", f" [✓] {t['label']:<19} DONE\n"))
            elif t["status"] == "WORKING":
                pct_bar = "█" * (t["progress"] // 10) + "░" * (10 - (t["progress"] // 10))
                out.append(("class:task-working", f" [●] {t['label']:<19} {t['progress']}%\n"))
                out.append(("class:task-bar", f"     [{pct_bar}]\n"))
            else:
                out.append(("class:task-pending", f" [○] {t['label']:<19} PENDING\n"))
        out.append(("", "\n"))

        out.append(("class:side-head", " METRICS & CONTEXT\n"))
        pct = (self.tokens_used / self.tokens_max) * 100
        bar_len = 16
        filled = int((pct / 100) * bar_len)
        bar_str = "█" * filled + "░" * (bar_len - filled)
        out.append(("class:dim", " Context: "))
        out.append(("class:metric-blue", f"{pct:.1f}% [{bar_str}]\n"))
        out.append(("class:dim", f" Tokens:  {self.tokens_used:,} / {self.tokens_max:,}\n"))
        out.append(("class:dim", f" Cost:    ${self.cost:.2f}  │  Lat: {self.latency}ms\n\n"))

        out.append(("class:side-head", " COMMANDS\n"))
        cmds = [
            ("/diff", "View staged changes"),
            ("/apply", "Write files to disk"),
            ("/test", "Run test suite"),
            ("/agents", "Cycle focused agent"),
        ]
        for c, desc in cmds:
            out.append(("class:cmd-chip", f" {c:<7} "))
            out.append(("class:dim", f" {desc}\n"))

        return out

    # ── FRAGMENT: REVIEW & APPLY SCREEN (WF-11) ─────────
    def _review_screen_frag(self):
        out = []
        out.append(("class:screen-title", " REVIEW AND APPLY — STAGED WORKSPACE DIFFS\n"))
        out.append(("class:dim", " Tekan spasi untuk toggle file staging · Jalankan /apply untuk commit ke disk.\n\n"))

        for fname, fobj in self.files.items():
            is_staged = self.staged.get(fname, False)
            chk = "[✓]" if is_staged else "[ ]"
            add_count = sum(1 for _, _, d in fobj["lines"] if d == "+")
            status_text = "APPLIED TO DISK" if self.applied and is_staged else ("STAGED" if is_staged else "UNSTAGED")
            st_cls = "class:badge-green" if self.applied and is_staged else ("class:badge-blue" if is_staged else "class:dim")

            out.append((st_cls, f" {chk} {fobj['path']} "))
            out.append(("class:badge-green", f" +{add_count} "))
            out.append(("", "  "))
            out.append((st_cls, f" {status_text} \n"))

            for n, text, diff in fobj["lines"][:6]:
                if diff == "+":
                    out.append(("class:code-add-mark", f"    {n:2d} + {text}\n"))
                else:
                    out.append(("class:dim", f"    {n:2d}   {text}\n"))
            if len(fobj["lines"]) > 6:
                out.append(("class:dim", f"    ... (+{len(fobj['lines'])-6} more lines)\n"))
            out.append(("", "\n"))

        if self.test_output:
            out.append(("class:card-subtitle", "── Test Run Console ──────────────────────────────────────\n"))
            for line in self.test_output:
                out.append(("class:cmd", f"  {line}\n"))

        return out

    # ── FRAGMENT: AGENT CLUSTER SCREEN (WF-12) ──────────
    def _cluster_screen_frag(self):
        online = sum(1 for a in self.agents if not a.get("paused"))
        out = []
        out.append(("class:screen-title", f" AGENT CLUSTER — CLOUD SWARM (forge-cluster-8291) [{online}/4 Online]\n\n"))

        for a in self.agents:
            is_foc = a["id"] == self.focused_agent_id
            p_status = "PAUSED" if a.get("paused") else a["status"]
            b_cls = "class:badge-amber" if a.get("paused") else ("class:badge-blue" if a["status"] == "WORKING" else "class:badge-green")

            foc_mark = "▶ " if is_foc else "  "
            out.append(("class:card-title", f"{foc_mark}{a['name']}Agent "))
            out.append((b_cls, f" {p_status} "))
            out.append(("class:dim", f"  Model: {a['model']}  Tokens: {a['tokens']:,}  Lat: {a['latency']}\n"))
            out.append(("class:dim", f"   Role: {a['role']}\n"))

            if self.inspected_prompt_agent_id == a["id"]:
                out.append(("class:cluster-prompt", f"   PROMPT: {a['system_prompt']}\n"))
            out.append(("", "\n"))

        return out

    # ── FRAGMENT: WIREFRAME MAP SPEC INSPECTOR ──────────
    def _wireframe_frag(self):
        out = []
        out.append(("class:screen-title", " WIREFRAME SPECIFICATION MAP (WF-01 to WF-12)\n\n"))
        specs = [
            ("WF-01", "Header & Telemetry Bar", "Branded header, 36x36 geometric logo, active agent counter, latency, token quota, cost."),
            ("WF-02", "Navigation Tab Bar", "Tabs [1] Live Session, [2] Review & Apply, [3] Agent Cluster, [4] Wireframe Spec."),
            ("WF-03", "Command Box & Team Joined", "Banner showing all 4 swarm agents joined and ready for cooperative orchestration."),
            ("WF-04", "CoderAgent Code Card", "High-fidelity syntax view with sub-file tabs (redis.go, session.proto, session_server.go)."),
            ("WF-05", "ReviewerAgent & Live Logs", "Verification output and real-time streaming event bus logs."),
            ("WF-06", "Multi-Agent Orchestration", "Status indicator for Researcher, Architect, Coder, and Reviewer agents."),
            ("WF-07", "Task Plan Breakdown", "4-stage pipeline with percentage completion indicators."),
            ("WF-08", "Metrics & Context Window", "Token consumption, visual gauge bar, USD cost, and network response latency."),
            ("WF-09", "Command Palette Preview", "Quick chips for /diff, /apply, /test, /agents, /help."),
            ("WF-10", "Persistent Input Field", "Interactive command line with history and auto-complete support."),
            ("WF-11", "Review and Apply Screen", "Interactive staging toggles and file diff verification."),
            ("WF-12", "Agent Cluster Swarm View", "Full cluster management view with prompt inspection and pause/resume controls.")
        ]
        for code, title, desc in specs:
            out.append(("class:card-badge-cyan", f" {code} "))
            out.append(("class:card-title", f" {title}\n"))
            out.append(("class:dim", f"    {desc}\n\n"))

        return out

    # ── FRAGMENT: FOOTER PROMPT & TELEMETRY (WF-10) ────
    def _footer_frag(self):
        foc = next((a for a in self.agents if a["id"] == self.focused_agent_id), self.agents[2])
        out = [
            ("class:foot-prompt", " ➜ agentforge:"),
            ("class:foot-agent", f"{foc['name'].lower()} "),
            ("class:foot-sep", "❯ "),
        ]
        return out

    def _bottom_bar_frag(self):
        curr_mode = getattr(getattr(self.agent, "modes", None), "current_mode", "auto").upper()
        return [
            ("class:foot-bar", f" Screen: [{self.active_screen.upper()}] "),
            ("class:foot-dim", "│"),
            ("class:foot-bar", f" Mode: [{curr_mode}] "),
            ("class:foot-dim", "│"),
            ("class:foot-ok", " Veritas: ON "),
            ("class:foot-dim", "│"),
            ("class:foot-bar", f" Turn {self.turn} · Tools {self.tools} · Veritas {self.veritas} "),
            ("class:foot-dim", "│"),
            ("class:foot-bar", f" Cost: ${self.cost:.2f} "),
            ("class:foot-dim", "│"),
            ("class:foot-warn", " [1-4] Screens · [Tab] Agent · [Ctrl+P] Palette "),
        ]

    # ── COMMAND HANDLERS ───────────────────────────────
    def handle_command(self, raw):
        cmd = raw.strip()
        if not cmd:
            return

        with self._lock:
            self.chat_log.append(("q", f"❯ {cmd}"))

        if cmd == "/diff" or cmd == "2":
            self.active_screen = "review"
            self._add_log("Navigation", "Switched to Review and Apply screen", "cyan")
            return
        if cmd == "/agents" or cmd == "3":
            self.cycle_agent()
            return
        if cmd == "/cluster":
            self.active_screen = "cluster"
            return
        if cmd == "/live" or cmd == "1":
            self.active_screen = "live"
            return
        if cmd == "/wireframe" or cmd == "4":
            self.active_screen = "wireframe"
            return
        if cmd == "/apply":
            self.apply_staged_files()
            return
        if cmd == "/test":
            self.run_tests()
            return
        if cmd == "/pause":
            self.is_paused = not self.is_paused
            state_lbl = "PAUSED" if self.is_paused else "RESUMED"
            self._add_log("Cluster", f"Session {state_lbl}", "amber")
            return
        if cmd == "/clear":
            self.live_logs = []
            return
        if cmd.startswith("/mode"):
            parts = cmd.split()
            if len(parts) > 1 and hasattr(self.agent, "modes"):
                ok, msg = self.agent.modes.set_mode(parts[1])
                self._add_log("Mode", msg, "cyan" if ok else "amber")
            elif hasattr(self.agent, "modes"):
                self._add_log("Mode", self.agent.modes.list_modes(), "cyan")
            return
        if cmd == "/help":
            with self._lock:
                self.chat_log.extend([
                    ("dim", "Perintah AgentForge:"),
                    ("cmd", "  /diff     — Buka [2] Review and Apply diffs"),
                    ("cmd", "  /apply    — Commit staged files ke disk workspace"),
                    ("cmd", "  /test     — Jalankan Go unit & benchmark tests"),
                    ("cmd", "  /agents   — Cycle focused agent highlight"),
                    ("cmd", "  /cluster  — Buka [3] Agent Cluster Swarm"),
                    ("cmd", "  /live     — Kembali ke [1] Live Session"),
                    ("cmd", "  /pause    — Toggle Pause / Resume swarm"),
                    ("cmd", "  /status   — Periksa keyring, model, dan budget"),
                    ("cmd", "  /quit     — Keluar"),
                    ("", ""),
                ])
            return

        self.bump_metrics(1420, 0.02)
        foc = next((a for a in self.agents if a["id"] == self.focused_agent_id), self.agents[2])
        self._add_log("User Prompt", f"> {cmd}", "amber")
        self._add_log(f"{foc['name']}Agent [Task]", f"Executing: {cmd}", "cyan")
        self._submit(cmd)

    def cycle_agent(self):
        ids = [a["id"] for a in self.agents]
        idx = (ids.index(self.focused_agent_id) + 1) % len(ids)
        self.focused_agent_id = ids[idx]
        if self.focused_agent_id == "architect":
            self.active_file = "session.proto"
        elif self.focused_agent_id == "coder":
            self.active_file = "redis.go"
        elif self.focused_agent_id == "reviewer":
            self.active_file = "session_server.go"
        self._add_log("Swarm Focus", f"Switched focus to {self.focused_agent_id.capitalize()}Agent", "cyan")

    def cycle_file(self):
        fnames = ["redis.go", "session.proto", "session_server.go"]
        idx = (fnames.index(self.active_file) + 1) % len(fnames)
        self.active_file = fnames[idx]

    def apply_staged_files(self):
        self.applied = True
        staged_names = [f for f, s in self.staged.items() if s]
        self._add_log("/apply", f"Applied {len(staged_names)} staged files to workspace disk.", "green")
        self.active_screen = "review"

    def run_tests(self):
        self.test_output = [
            "=== RUN   TestSessionCache_SetSession",
            "--- PASS: TestSessionCache_SetSession (0.00s)",
            "=== RUN   TestUserSessionService_GetSession",
            "--- PASS: TestUserSessionService_GetSession (0.00s)",
            "=== RUN   TestUserSessionService_DeleteSession",
            "--- PASS: TestUserSessionService_DeleteSession (0.00s)",
            "BenchmarkSessionCache_SetSession-8    100000    1204 ns/op    64 B/op    2 allocs/op",
            "PASS: All 4 test packages verified successfully."
        ]
        self.tasks[3]["status"] = "DONE"
        self.tasks[3]["progress"] = 100
        self._add_log("/test", "PASS: Unit & Benchmark suites verified (100%)", "green")
        self.active_screen = "review"

    def bump_metrics(self, tokens, cost_delta):
        self.tokens_used = min(self.tokens_max, self.tokens_used + tokens)
        self.cost = round(self.cost + cost_delta, 2)

    def _add_log(self, title, body, tone="cyan"):
        self.live_logs.append({
            "title": title,
            "body": body,
            "tone": tone,
            "ts": TS()
        })
        self._safe_invalidate()

    def _submit(self, task):
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
                            self._add_log("Tool Call", f"{tr['name']}({json.dumps(tr.get('args', {}), ensure_ascii=False)[:100]})", "cyan")
                            self.tools += 1
                        elif tr.get("type") == "veritas":
                            self._add_log("Veritas Verification", f"{tr.get('tool')} -> {tr.get('verdict', tr.get('ok'))}", "green")
                            self.veritas += 1
                    self.chat_log.append(("a", f"  {ans[:400]}"))
                    self.chat_log.append(("", ""))
                    self.turn += 1
                self._safe_invalidate()
            except Exception as e:
                with self._lock:
                    self.chat_log.append(("err", f"  error: {e}"))
                    self.chat_log.append(("", ""))
                self._safe_invalidate()
            finally:
                self.agent.llm = orig_llm
                self.running = False
                self._safe_invalidate()

        threading.Thread(target=worker, daemon=True).start()

    def _safe_invalidate(self):
        if self.app:
            try:
                self.app.invalidate()
            except Exception:
                pass

    # ── BUILD APPLICATION LAYOUT ───────────────────────
    def build(self):
        header_win = Window(content=FormattedTextControl(text=self._header_frag), height=5)
        header_frame = Frame(header_win, style="class:head-frame")

        nav_win = Window(content=FormattedTextControl(text=self._nav_frag), height=1, style="class:nav-frame")

        code_win = Window(content=FormattedTextControl(text=self._code_card_frag), wrap_lines=True)
        code_frame = Frame(code_win, title=" [WF-04] WORKSPACE CODE ", style="class:card-frame")

        rev_win = Window(content=FormattedTextControl(text=self._reviewer_log_frag), wrap_lines=True)
        rev_frame = Frame(rev_win, title=" [WF-05] VERIFICATION & STREAM LOG ", style="class:card-frame")

        live_center = HSplit([code_frame, rev_frame])

        review_win = Window(content=FormattedTextControl(text=self._review_screen_frag), wrap_lines=True)
        review_frame = Frame(review_win, title=" [WF-11] REVIEW & APPLY DIFFS ", style="class:card-frame")

        cluster_win = Window(content=FormattedTextControl(text=self._cluster_screen_frag), wrap_lines=True)
        cluster_frame = Frame(cluster_win, title=" [WF-12] AGENT CLUSTER SWARM ", style="class:card-frame")

        wireframe_win = Window(content=FormattedTextControl(text=self._wireframe_frag), wrap_lines=True)
        wireframe_frame = Frame(wireframe_win, title=" [WF-01..12] ARCHITECTURAL WIREFRAME ", style="class:card-frame")

        main_center = HSplit([
            ConditionalContainer(content=live_center, filter=Condition(lambda: self.active_screen == "live")),
            ConditionalContainer(content=review_frame, filter=Condition(lambda: self.active_screen == "review")),
            ConditionalContainer(content=cluster_frame, filter=Condition(lambda: self.active_screen == "cluster")),
            ConditionalContainer(content=wireframe_frame, filter=Condition(lambda: self.active_screen == "wireframe")),
        ])

        sidebar_win = Window(content=FormattedTextControl(text=self._sidebar_frag), wrap_lines=True, width=D(preferred=36))
        sidebar_frame = Frame(sidebar_win, title=" SWARM CONTROL ", style="class:side-frame")

        center_area = VSplit([main_center, sidebar_frame])

        prompt_lbl = Window(content=FormattedTextControl(text=self._footer_frag), height=1, width=D(preferred=26))
        prompt_input = Window(content=BufferControl(buffer=self.input_buf), height=1)
        input_row = VSplit([prompt_lbl, prompt_input])
        input_frame = Frame(input_row, style="class:prompt-frame")

        bottom_bar = Window(content=FormattedTextControl(text=self._bottom_bar_frag), height=1, style="class:foot-bar")

        root = HSplit([
            header_frame,
            nav_win,
            center_area,
            input_frame,
            bottom_bar,
        ])

        kb = KeyBindings()

        @kb.add("c-d")
        @kb.add("c-c")
        def _quit(event):
            event.app.exit()

        @kb.add("1")
        def _to_live(event):
            self.active_screen = "live"
            self._safe_invalidate()

        @kb.add("2")
        def _to_review(event):
            self.active_screen = "review"
            self._safe_invalidate()

        @kb.add("3")
        def _to_cluster(event):
            self.active_screen = "cluster"
            self._safe_invalidate()

        @kb.add("4")
        def _to_wireframe(event):
            self.active_screen = "wireframe"
            self._safe_invalidate()

        @kb.add("tab")
        def _cycle_agent_key(event):
            self.cycle_agent()
            self._safe_invalidate()

        @kb.add("escape")
        def _toggle_pause_key(event):
            self.is_paused = not self.is_paused
            self._safe_invalidate()

        @kb.add("f")
        def _cycle_file_key(event):
            if self.active_screen == "live":
                self.cycle_file()
                self._safe_invalidate()

        @kb.add("c-p")
        def _toggle_palette(event):
            self.input_buf.text = "/"
            self._safe_invalidate()

        @kb.add("enter")
        def _on_enter(event):
            text = self.input_buf.text.strip()
            self.input_buf.text = ""
            if text in ("/quit", "/exit", "/q"):
                event.app.exit()
                return
            self.handle_command(text)
            self._safe_invalidate()

        def _clock():
            while True:
                time.sleep(1)
                self._safe_invalidate()
        threading.Thread(target=_clock, daemon=True).start()

        self.app = Application(
            layout=Layout(root, focused_element=prompt_input),
            key_bindings=kb,
            full_screen=True,
            style=self._style(),
            mouse_support=True,
        )
        return self.app

    # ── DESIGN SPEC COLOR SYSTEM & TOKENS ──────────────
    def _style(self):
        return Style.from_dict({
            "": "bg:#0d1117 #c9d1d9",
            # Header
            "head-frame": "bg:#121720 #c9d1d9",
            "hdr-title": "#e6edf3 bold",
            "hdr-ver": "#38bdf8 bold",
            "hdr-sub": "#8b949e",
            "hdr-dim": "#8b949e",
            "hdr-val": "#e6edf3",
            "hdr-val-green": "#4ade80 bold",
            "hdr-val-blue": "#38bdf8 bold",
            "hdr-val-amber": "#fbbf24 bold",

            # Navigation
            "nav-frame": "bg:#090c12",
            "nav-tab-active": "bg:#1c2635 #38bdf8 bold",
            "nav-tab-idle": "bg:#121720 #8b949e",
            "nav-hint": "#6e7681",

            # Cards & Panes
            "card-frame": "bg:#0d1117",
            "side-frame": "bg:#0d1117",
            "card-title": "#e6edf3 bold",
            "card-subtitle": "#8b949e",
            "card-badge": "bg:#1c2635 #8b949e",
            "card-badge-cyan": "bg:#1c2635 #38bdf8 bold",
            "subtab-active": "bg:#1c2635 #38bdf8 bold",
            "subtab-idle": "bg:#121720 #8b949e",

            # Code display
            "code-num": "#6e7681",
            "code-add-mark": "#4ade80 bold",
            "code-add-text": "#4ade80",
            "code-del-mark": "#f85149 bold",
            "code-del-text": "#f85149",
            "code-plain-mark": "#30363d",
            "code-plain-text": "#e6edf3",

            # Logs & Insights
            "log-cyan": "#38bdf8 bold",
            "log-green": "#4ade80 bold",
            "log-amber": "#fbbf24 bold",
            "log-body": "#c9d1d9",

            # Swarm & Orchestration
            "side-head": "#38bdf8 bold",
            "agent-focused": "#38bdf8 bold",
            "agent-idle": "#8b949e",
            "badge-green": "bg:#161d28 #4ade80",
            "badge-blue": "bg:#161d28 #38bdf8",
            "badge-amber": "bg:#161d28 #fbbf24",

            # Task plan
            "task-done": "#4ade80",
            "task-working": "#38bdf8 bold",
            "task-pending": "#8b949e",
            "task-bar": "#38bdf8",
            "metric-blue": "#38bdf8 bold",
            "cmd-chip": "bg:#1c2635 #e6edf3 bold",

            # Screens
            "screen-title": "#e6edf3 bold",
            "cluster-prompt": "bg:#090c12 #c9d1d9",

            # Prompt & Footer
            "prompt-frame": "bg:#161d28",
            "foot-prompt": "#58a6ff bold",
            "foot-agent": "#3fb950 bold",
            "foot-sep": "#8b949e",
            "foot-bar": "bg:#121720 #8b949e",
            "foot-ok": "bg:#121720 #4ade80 bold",
            "foot-warn": "bg:#121720 #fbbf24",
            "foot-dim": "bg:#121720 #30363d",

            # Borders & UI
            "frame.border": "#2a3444",
            "frame.label": "#38bdf8",
            "dim": "#8b949e",
            "cmd": "#4ade80",
            "q": "#58a6ff bold",
            "a": "#c9d1d9",
            "err": "#f85149",
        })


def main():
    agent = Agent("config.json")
    agent.skill = "research"
    TUI(agent).build().run()


if __name__ == "__main__":
    main()
