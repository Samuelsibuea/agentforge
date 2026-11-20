# AgentForge — Design Reference & Logo Spec

## Referensi desain yang BOZ minta (diambil live 2026-11-19)

| Sumber | Yang diambil untuk AgentForge | URL |
| :--- | :--- | :--- |
| shadcn/ui theming | Semantic token system — `background/foreground`, `card`, `primary`, `muted`, `accent`, `border`, `ring`; radius scale `--radius-sm..4xl` | https://ui.shadcn.com/docs/theming |
| Backblaze lerobot (shadcn + GitHub Primer) | Persis palette yang TUI pakai: `bg #0d1117`, `card #161b22`, `primary #58a6ff`, `success #3fb950`, `attention #d29922`, `destructive #f85149`, `border #30363d`; radius 4/5/6/8px; motion 120/200/320ms | https://github.com/backblaze-b2-samples/lerobot-b2-streaming/blob/main/docs/design-system.md |
| rampstackco/terminal-ui-theme | Terminal register: near-black ground, monospace sebagai display voice, SATU phosphor accent, glow sebagai emphasis — bukan efek. Tanpa scanline/CRT | https://github.com/rampstackco/terminal-ui-theme |
| Dribbble AI Agent Dashboard (Alamgir Hossain) | Dark-first dashboard, modular panel, widget grid | https://dribbble.com/shots/26252782-AI-Agent-Dashboard |
| Dribbble GoPilot (Naimur Rahman) | Minimal dark UI + gradient accent pada main input | https://dribbble.com/shots/27872961 |
| Dribbble NIXA (Rishan Khan) | Soft gradient, accessible contrast, sidebar + card flow | https://dribbble.com/shots/27570864 |
| Dribbble Orchestrix (Design Monks) | Workflow builder + guardrail panel, B2B SaaS structure | https://dribbble.com/shots/27605468 |

## Referensi khusus CLI / TUI (permintaan BOZ — tampilan terminal)

| Sumber | Yang diambil untuk AgentForge TUI | URL |
| :--- | :--- | :--- |
| Textual (Textualize) | TUI CSS-like: `dock`, `background: $boost`, `$foreground-muted`, panel terpisah | https://textual.textualize.io/tutorial/ |
| R cli themes | Selector + property styling untuk elemen CLI (alert/success/dim) | https://cli.r-lib.org/reference/themes.html |
| ThoughtWorks CLI design guidelines | CLI sebagai DX: struktur output, konsistensi perintah, "fun and fancy" | https://www.thoughtworks.com/en-us/insights/blog/engineering-effectiveness/elevate-developer-experiences-cli-design-guidelines |
| Warp brand guidelines (madeGoodDesigns) | Identitas CLI = name + prompt + ASCII banner + palette + mark kecil; warna brand tinggal di icon/docs, bukan di program | https://madegooddesigns.com/warp-brand-guidelines/ |
| Style Gallery — Developer Tool Direction | Hairline 1px, mono label, satu accent untuk state live/focus; caret = satu-satunya animasi ambient; stream don't fade | https://style.gallery/library/expression/directions/developer-tool/ |
| Linear brand guidelines | Monochrome wordmark, desaturated blue primary, ruang napas di sekitar mark | https://linear.app/brand |
| Dribbble tag CLI / iTerm / Warp shot | Komposisi panel terminal modern, block editor (Warp blocks) | https://dribbble.com/tags/cli · https://dribbble.com/shots/19612932-Warp-dev-Terminal |

### Turunan ke TUI AgentForge (sudah terpasang)

| Turunan | Di mana |
| :--- | :--- |
| Satu accent untuk state live | `#3fb950` cuma untuk veritas + prompt name; `#58a6ff` cuma interactive |
| Caret blink = satu animasi | footer WIB refresh 1s, tanpa loop lain |
| Stream, bukan fade | chat panel newest-first, output tool ke stderr live |
| Mark kecil di prompt | `➜ agentforge:<skill> ❯` — glyph, bukan gambar |
| Monospace sebagai display voice | seluruh TUI JetBrains/DejaVu mono, tanpa sans |

## Design token AgentForge (sudah dipakai di TUI)

| Token | Nilai | Pakai |
| :--- | :--- | :--- |
| ground | `#0d1117` | canvas, chat & sidebar body |
| surface | `#161b22` | header, prompt, footer, panel atas |
| border | `#30363d` | frame border |
| primary | `#58a6ff` | banner, link, prompt arrow |
| success | `#3fb950` | veritas, prompt name, cmd |
| attention | `#d29922` | cursor, warn |
| destructive | `#f85149` | err |
| accent | `#bc8cff` | st-head, node |
| text | `#c9d1d9` / muted `#8b949e` | body / dim |

## Logo — aset resmi (dari zip BOZ)

| File | Konsep | Struktur |
| :--- | :--- | :--- |
| `logo-mark.png` | **Mark murni** — glyph AgentForge di dark ground | 4096×4096, tanpa text, untuk favicon/avatar |
| `logo-lockup.png` | **Lockup vertikal** — mark + wordmark AGENTFORGE | 8192×8192, splash/about |
| `logo-horizontal.jpg` | **Horizontal lockup** — mark + wordmark + tagline | 4096×2304, hero README/situs |

Generator lama (`logo_gen.py` + varian v1–v4) dihapus — aset resmi BOZ yang
pakai. Palet logo = palet TUI (ground/surface/primary/success/attention/accent).

## Arah refresh TUI (dari referensi di atas)

1. Satu phosphor accent saja (terminal-ui-theme) — turunkan biru ke `#58a6ff` cuma untuk interactive, sisanya netral.
2. Glow sebagai emphasis, bukan efek — jangan scanline/CRT.
3. Radius konsisten (shadcn) — border TUI sudah kotak terminal, biarkan; radius untuk panel non-terminal bila ada web panel.
4. Motion 120/200/320ms bila TUI pakai transisi (fade cursor, blink 200ms).
5. Gradient accent pada prompt/input utama (GoPilot) — bila terminal support 24-bit, gradient `#58a6ff → #3fb950` pada bar prompt.
