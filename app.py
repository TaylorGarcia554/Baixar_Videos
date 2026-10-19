import os
import json
import threading
import subprocess
import sys

# ── Caminhos (funciona tanto rodando pelo Python quanto como .exe instalado) ──
_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    # Rodando como .exe (PyInstaller) — salva config no AppData do usuário
    _CFG_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "MioBaixador")
    os.makedirs(_CFG_DIR, exist_ok=True)
else:
    _CFG_DIR = os.path.dirname(os.path.abspath(__file__))


def _resource_path(*parts):
    """Caminho de um recurso (ex.: ícone), funcionando tanto via python app.py
    quanto empacotado pelo PyInstaller (onedir)."""
    if _FROZEN:
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


ICON_PATH = _resource_path("icone.ico")

# ── Detecta navegador instalado (fallback de cookies quando o YouTube pede
#    confirmação "não sou um robô") ──────────────────────────────────────────
# Firefox vem primeiro: no Windows, Chrome/Edge/Brave/Opera travam o arquivo de
# cookies enquanto estão abertos e usam criptografia ("app-bound") que o yt-dlp
# muitas vezes não consegue ler. O Firefox não tem esse problema.
_BROWSER_PATHS = [
    ("firefox", r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
    ("firefox", r"%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe"),
    ("chrome",  r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
    ("chrome",  r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ("chrome",  r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ("edge",    r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
    ("edge",    r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
    ("opera",   r"%LOCALAPPDATA%\Programs\Opera\opera.exe"),
    ("brave",   r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ("brave",   r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
]


def _detect_browsers():
    """Todos os navegadores instalados (sem repetir), na ordem de preferência."""
    achados = []
    for nome, caminho in _BROWSER_PATHS:
        if nome not in achados and os.path.exists(os.path.expandvars(caminho)):
            achados.append(nome)
    return achados


def _cookies_file():
    """cookies.txt exportado pelo usuário (formato Netscape), se existir.
    Procura na pasta de config (AppData\\MioBaixador) e ao lado do app/.exe."""
    pastas = [_CFG_DIR]
    if _FROZEN:
        pastas.append(os.path.dirname(sys.executable))
    for pasta in pastas:
        caminho = os.path.join(pasta, "cookies.txt")
        if os.path.isfile(caminho):
            return caminho
    return None

# ── Auto-instala dependências (só quando roda via Python, não no .exe) ───────
def _pip(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"], check=True)

if not _FROZEN:
    try:
        import customtkinter as ctk  # noqa: F401
    except ImportError:
        _pip("customtkinter")

    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        _pip("yt-dlp")

    try:
        import imageio_ffmpeg  # noqa: F401
    except ImportError:
        _pip("imageio-ffmpeg")

import customtkinter as ctk
import imageio_ffmpeg
import yt_dlp  # noqa: F401 — garante que está importável no .exe
from PIL import Image

_FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
_YT_DLP_OK  = True

# Autoteste usado pelo build automático: confirma que o .exe empacotado
# consegue carregar o yt-dlp, os certificados HTTPS e o ffmpeg, sem abrir a janela.
if "--selftest" in sys.argv:
    import certifi
    assert os.path.isfile(certifi.where()), "certifi sem cacert.pem"
    assert os.path.isfile(_FFMPEG_BIN), "ffmpeg não encontrado"
    with yt_dlp.YoutubeDL({"quiet": True}) as _ydl:
        pass
    sys.exit(0)

from tkinter import filedialog, messagebox

# ── Constantes ───────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(_CFG_DIR, "config.json")

QUALITY_OPTIONS = [
    "Melhor (4K/1080p)",
    "1080p (Full HD)",
    "720p (HD)",
    "480p",
    "360p",
    "Somente áudio (MP3)",
]
QUALITY_MAP = {
    "Melhor (4K/1080p)":   "bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
    "1080p (Full HD)":     "bestvideo[height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p (HD)":           "bestvideo[height<=720]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":                "bestvideo[height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":                "bestvideo[height<=360]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]",
    "Somente áudio (MP3)": "bestaudio/best",
}
FORMAT_OPTIONS = ["MP4", "MKV", "WEBM", "MP3", "M4A"]
FORMAT_MAP = {"MP4": "mp4", "MKV": "mkv", "WEBM": "webm", "MP3": "mp3", "M4A": "m4a"}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "pasta_destino": os.path.join(os.path.expanduser("~"), "Downloads"),
        "qualidade": "Melhor (4K/1080p)",
        "formato": "MP4",
        "tema": "dark",
    }


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── App ───────────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.cfg = load_config()
        self._theme = self.cfg.get("tema", "dark")
        ctk.set_appearance_mode(self._theme)
        ctk.set_default_color_theme("blue")

        self.title("Mió Baixador do Youtube")
        self.geometry("780x540")
        self.minsize(620, 460)
        self.resizable(True, True)

        try:
            self.iconbitmap(ICON_PATH)  # Ícone da janela/barra de tarefas
        except Exception:
            pass

        self.downloading = False
        self._build()

        threading.Thread(target=self._check_deps, daemon=True).start()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, minsize=58)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_content()
        self._build_bottom()

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, height=60,
                            fg_color=("#111827", "#0d1117"))
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)

        # Logo
        try:
            _logo_pil = Image.open(ICON_PATH)
            self._logo_img = ctk.CTkImage(
                light_image=_logo_pil, dark_image=_logo_pil, size=(36, 36))
            ctk.CTkLabel(hdr, image=self._logo_img, text="").grid(
                row=0, column=0, padx=16, pady=10, sticky="w")
        except Exception:
            logo = ctk.CTkFrame(hdr, width=40, height=40, corner_radius=6,
                                 fg_color=("#ffffff", "#ffffff"))
            logo.grid(row=0, column=0, padx=16, pady=10, sticky="w")
            logo.grid_propagate(False)
            ctk.CTkLabel(logo, text="Logo", text_color="#111827",
                         font=ctk.CTkFont(size=10, weight="bold")).place(
                relx=0.5, rely=0.5, anchor="center")

        # Título
        ctk.CTkLabel(hdr, text="Mió Baixador do Youtube",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=("#f9fafb", "#e6edf3")).grid(
            row=0, column=1, pady=10)

        # Linha separadora
        ctk.CTkFrame(self, height=1, corner_radius=0,
                     fg_color=("#1f2937", "#21262d")).grid(
            row=0, column=0, sticky="ews")

    # ── Conteúdo central ─────────────────────────────────────────────────────
    def _build_content(self):
        # Scroll container
        scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0,
            fg_color=("#111827", "#0d1117"),
            scrollbar_button_color=("#374151", "#21262d"),
            scrollbar_button_hover_color=("#4b5563", "#30363d"),
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(scroll, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=28, pady=16)
        wrap.grid_columnconfigure(0, weight=1)

        r = 0

        # ── Barra de URL ──────────────────────────────────────────────────────
        url_card = ctk.CTkFrame(
            wrap, corner_radius=12, height=52,
            fg_color=("#1f2937", "#161b22"),
            border_width=1, border_color=("#374151", "#30363d"),
        )
        url_card.grid(row=r, column=0, sticky="ew", pady=(0, 10))
        url_card.grid_columnconfigure(0, weight=1)
        url_card.grid_propagate(False)
        r += 1

        self.url_var = ctk.StringVar()
        ctk.CTkEntry(
            url_card, textvariable=self.url_var,
            placeholder_text="Cole o link do vídeo aqui  (YouTube, Vimeo, Instagram, TikTok...)",
            border_width=0, corner_radius=0,
            fg_color="transparent",
            placeholder_text_color=("#6b7280", "#6b7280"),
            text_color=("#f3f4f6", "#e6edf3"),
            font=ctk.CTkFont(size=12),
            height=52,
        ).grid(row=0, column=0, sticky="ew", padx=(14, 0))

        # Separador vertical
        ctk.CTkFrame(url_card, width=1, height=28, corner_radius=0,
                     fg_color=("#374151", "#30363d")).grid(
            row=0, column=1, pady=12, padx=0)

        # Botão Download
        self.btn_dl = ctk.CTkButton(
            url_card, text="Download  ⬇",
            command=self._start_download,
            width=140, height=52,
            corner_radius=12,
            fg_color="transparent",
            hover_color=("#1e3a5f", "#1f2937"),
            text_color=("#3b82f6", "#3b82f6"),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_dl.grid(row=0, column=2)

        # ── Opções (qualidade, formato, nome) ─────────────────────────────────
        opts = ctk.CTkFrame(wrap, fg_color="transparent")
        opts.grid(row=r, column=0, sticky="ew", pady=(0, 10))
        opts.grid_columnconfigure((0, 1, 2), weight=1)
        r += 1

        def opts_card(parent, label, col, padright=6):
            f = ctk.CTkFrame(parent, corner_radius=8,
                             fg_color=("#1f2937", "#161b22"),
                             border_width=1, border_color=("#374151", "#30363d"))
            f.grid(row=0, column=col, sticky="ew", padx=(0, padright))
            ctk.CTkLabel(f, text=label,
                         text_color=("#9ca3af", "#8b949e"),
                         font=ctk.CTkFont(size=10)).pack(padx=10, pady=(6, 1), anchor="w")
            return f

        # Qualidade
        qf = opts_card(opts, "Qualidade", 0)
        self.qual_var = ctk.StringVar(value=self.cfg.get("qualidade", "Melhor (4K/1080p)"))
        ctk.CTkComboBox(
            qf, values=QUALITY_OPTIONS, variable=self.qual_var,
            state="readonly", corner_radius=6,
            fg_color=("#1f2937", "#161b22"), border_width=0,
            text_color=("#f3f4f6", "#e6edf3"),
            button_color=("#374151", "#30363d"),
            button_hover_color=("#4b5563", "#3d444d"),
            dropdown_fg_color=("#1f2937", "#161b22"),
            dropdown_text_color=("#f3f4f6", "#e6edf3"),
            dropdown_hover_color=("#374151", "#21262d"),
            font=ctk.CTkFont(size=11), width=10,
            command=lambda _: self._save_prefs(),
        ).pack(padx=6, pady=(0, 6), fill="x")

        # Formato
        ff = opts_card(opts, "Formato", 1)
        self.fmt_var = ctk.StringVar(value=self.cfg.get("formato", "MP4"))
        ctk.CTkComboBox(
            ff, values=FORMAT_OPTIONS, variable=self.fmt_var,
            state="readonly", corner_radius=6,
            fg_color=("#1f2937", "#161b22"), border_width=0,
            text_color=("#f3f4f6", "#e6edf3"),
            button_color=("#374151", "#30363d"),
            button_hover_color=("#4b5563", "#3d444d"),
            dropdown_fg_color=("#1f2937", "#161b22"),
            dropdown_text_color=("#f3f4f6", "#e6edf3"),
            dropdown_hover_color=("#374151", "#21262d"),
            font=ctk.CTkFont(size=11),
            command=lambda _: self._save_prefs(),
        ).pack(padx=6, pady=(0, 6), fill="x")

        # Nome do arquivo
        nf = opts_card(opts, "Nome do arquivo  (opcional)", 2, padright=0)
        self.nome_var = ctk.StringVar()
        ctk.CTkEntry(
            nf, textvariable=self.nome_var,
            placeholder_text="Deixe vazio = título original",
            border_width=0, fg_color="transparent",
            placeholder_text_color=("#6b7280", "#6b7280"),
            text_color=("#f3f4f6", "#e6edf3"),
            font=ctk.CTkFont(size=11),
        ).pack(padx=6, pady=(0, 6), fill="x")

        # ── Pasta atual ───────────────────────────────────────────────────────
        path_card = ctk.CTkFrame(
            wrap, corner_radius=10, height=44,
            fg_color=("#1f2937", "#161b22"),
            border_width=1, border_color=("#374151", "#30363d"),
        )
        path_card.grid(row=r, column=0, sticky="ew", pady=(0, 10))
        path_card.grid_propagate(False)
        r += 1

        self.folder_var = ctk.StringVar(value=self.cfg.get("pasta_destino", ""))
        ctk.CTkLabel(
            path_card, textvariable=self.folder_var,
            text_color=("#f3f4f6", "#e6edf3"),
            font=ctk.CTkFont(size=12, weight="bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        # ── Card "Select Folder" ──────────────────────────────────────────────
        self.folder_card = ctk.CTkFrame(
            wrap, corner_radius=12, height=140,
            fg_color=("#1f2937", "#161b22"),
            border_width=1, border_color=("#374151", "#30363d"),
            cursor="hand2",
        )
        self.folder_card.grid(row=r, column=0, sticky="ew", pady=(0, 6))
        self.folder_card.grid_propagate(False)
        r += 1

        self.folder_card.bind("<Button-1>", lambda _: self._choose_folder())
        self.folder_card.bind("<Enter>",
            lambda _: self.folder_card.configure(fg_color=("#263548", "#1f2937")))
        self.folder_card.bind("<Leave>",
            lambda _: self.folder_card.configure(fg_color=("#1f2937", "#161b22")))

        icon_lbl = ctk.CTkLabel(self.folder_card, text="📁",
                                 font=ctk.CTkFont(size=36))
        icon_lbl.place(relx=0.5, rely=0.38, anchor="center")
        icon_lbl.bind("<Button-1>", lambda _: self._choose_folder())

        txt_lbl = ctk.CTkLabel(self.folder_card, text="Select Folder",
                                font=ctk.CTkFont(size=13, weight="bold"),
                                text_color=("#f3f4f6", "#e6edf3"))
        txt_lbl.place(relx=0.5, rely=0.74, anchor="center")
        txt_lbl.bind("<Button-1>", lambda _: self._choose_folder())

        # ── Status geral ──────────────────────────────────────────────────────
        self.status_var = ctk.StringVar(value="Pronto.")
        ctk.CTkLabel(wrap, textvariable=self.status_var,
                     text_color=("#9ca3af", "#8b949e"),
                     font=ctk.CTkFont(size=11)).grid(
            row=r, column=0, sticky="w", pady=(4, 0))

    # ── Barra de progresso (fixada embaixo) ───────────────────────────────────
    def _build_bottom(self):
        bottom = ctk.CTkFrame(self, corner_radius=0, height=58,
                               fg_color=("#111827", "#0d1117"))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_propagate(False)

        self._prog_val = ctk.DoubleVar(value=0)
        self._prog_bar = ctk.CTkProgressBar(
            bottom, variable=self._prog_val,
            height=12, corner_radius=6,
            fg_color=("#1f2937", "#21262d"),
            progress_color=("#16a34a", "#22c55e"),
        )
        self._prog_bar.set(0)
        self._prog_bar.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="ew")

        self._dl_label = ctk.StringVar(value="")
        ctk.CTkLabel(bottom, textvariable=self._dl_label,
                     text_color=("#f3f4f6", "#e6edf3"),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     anchor="e").grid(row=0, column=1, padx=(0, 16), pady=(14, 4), sticky="e")

    # ── Ações ─────────────────────────────────────────────────────────────────
    def _save_prefs(self):
        self.cfg["qualidade"] = self.qual_var.get()
        self.cfg["formato"] = self.fmt_var.get()
        save_config(self.cfg)

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or os.path.expanduser("~"))
        if folder:
            self.folder_var.set(folder)
            self.cfg["pasta_destino"] = folder
            save_config(self.cfg)

    def _set_status(self, msg):
        self.after(0, lambda: self.status_var.set(msg))

    def _check_deps(self):
        global _YT_DLP_OK
        if not _YT_DLP_OK:
            self._set_status("Instalando yt-dlp...")
            try:
                _pip("yt-dlp")
                _YT_DLP_OK = True
                self._set_status("yt-dlp instalado! Pronto.")
            except Exception as e:
                self._set_status(f"Erro ao instalar yt-dlp: {e}")
                return
        # imageio-ffmpeg já garante o ffmpeg — apenas verifica se funciona
        try:
            r = subprocess.run([_FFMPEG_BIN, "-version"], capture_output=True, timeout=6)
            self._ffmpeg_ok = r.returncode == 0
        except Exception:
            self._ffmpeg_ok = False

        if self._ffmpeg_ok:
            self._set_status("Pronto.")
        else:
            self._set_status("⚠ ffmpeg com problema — qualidade máxima pode não funcionar.")

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "Cole uma URL primeiro.", parent=self)
            return

        pasta = self.folder_var.get().strip()
        if not pasta:
            messagebox.showwarning("Aviso", "Escolha a pasta de destino.", parent=self)
            return

        os.makedirs(pasta, exist_ok=True)
        self._save_prefs()

        self.downloading = True
        self.btn_dl.configure(state="disabled", text="Baixando...")
        self._prog_bar.set(0)
        self._dl_label.set("Iniciando...")

        threading.Thread(target=self._download, args=(url, pasta), daemon=True).start()

    def _download(self, url, pasta):
        try:
            import yt_dlp

            fmt = FORMAT_MAP.get(self.fmt_var.get(), "mp4")
            qual = QUALITY_MAP.get(self.qual_var.get(), "bestvideo+bestaudio/best")
            is_audio = fmt in ("mp3", "m4a")

            nome = self.nome_var.get().strip()
            if nome:
                safe = "".join(c for c in nome if c not in r'\/:*?"<>|')
                outtmpl = os.path.join(pasta, safe + ".%(ext)s")
            else:
                outtmpl = os.path.join(pasta, "%(title)s.%(ext)s")

            ydl_opts = {
                "outtmpl": outtmpl,
                "progress_hooks": [self._hook],
                "ffmpeg_location": _FFMPEG_BIN,
                "quiet": True,
                "no_warnings": True,
            }

            if is_audio:
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": fmt,
                    "preferredquality": "192",
                }]
            else:
                ydl_opts["format"] = qual
                ydl_opts["merge_output_format"] = fmt
                # Garante áudio AAC no MP4 — evita opus/vorbis que a maioria dos players não toca
                if fmt == "mp4":
                    ydl_opts["postprocessor_args"] = {
                        "ffmpeg": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
                    }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                msg = str(e)
                # YouTube pedindo confirmação anti-bot: tenta de novo usando os
                # cookies de um navegador instalado (precisa estar logado no YouTube nele)
                low = msg.lower()
                bot_check = ("sign in to confirm" in low or "not a bot" in low
                             or ("cookies" in low and "login" in low))
                if not bot_check:
                    raise

                # Tentativas em ordem: cookies.txt exportado → cada navegador instalado.
                # Se um navegador falhar (ex.: Chrome com cookies travados), passa
                # para o próximo em vez de parar no primeiro erro.
                tentativas = []
                arquivo = _cookies_file()
                if arquivo:
                    tentativas.append(("cookies.txt", {"cookiefile": arquivo}))
                for nav in _detect_browsers():
                    tentativas.append((nav, {"cookiesfrombrowser": (nav,)}))

                falhas = []
                sucesso = False
                for nome_fonte, extra in tentativas:
                    self.after(0, lambda n=nome_fonte: self._dl_label.set(
                        f"Tentando novamente com login do {n}..."))
                    opts = {k: v for k, v in ydl_opts.items()
                            if k not in ("cookiefile", "cookiesfrombrowser")}
                    opts.update(extra)
                    try:
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            ydl.download([url])
                        sucesso = True
                        break
                    except Exception as e2:
                        falhas.append(f"• {nome_fonte}: {str(e2).splitlines()[0][:120]}")

                if not sucesso:
                    detalhes = ("\n".join(falhas) + "\n\n") if falhas else ""
                    raise Exception(
                        "O YouTube pediu confirmação de login e não deu para usar "
                        "os cookies de nenhum navegador.\n\n" + detalhes +
                        "Como resolver:\n"
                        "1) Faça login no YouTube pelo Firefox e tente de novo; ou\n"
                        "2) Feche o Chrome por completo (inclusive em segundo plano); ou\n"
                        "3) Exporte os cookies do YouTube (extensão \"Get cookies.txt "
                        f"LOCALLY\") e salve como cookies.txt em:\n{_CFG_DIR}"
                    )

            def _ok():
                self._prog_bar.set(1)
                self._dl_label.set("Concluído! ✓")
                self.status_var.set("Download concluído com sucesso!")
                messagebox.showinfo("Sucesso", "Download concluído!", parent=self)

            self.after(0, _ok)

        except Exception as e:
            err = str(e)
            def _err():
                self._dl_label.set("Erro!")
                self.status_var.set(f"Erro: {err[:80]}")
                messagebox.showerror("Erro no download", err[:1500], parent=self)
            self.after(0, _err)

        finally:
            self.downloading = False
            def _reset():
                self.btn_dl.configure(state="normal", text="Download  ⬇")
            self.after(2000, _reset)

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            done  = d.get("downloaded_bytes", 0)
            speed = d.get("_speed_str", "").strip()
            eta   = d.get("_eta_str", "").strip()

            if total > 0:
                pct = done / total
                info = f"Downloading...  {pct*100:.0f}%"
                if speed:
                    info += f"   •   {speed}"
                if eta:
                    info += f"   •   ETA {eta}"
                def _upd(p=pct, s=info):
                    self._prog_bar.set(p)
                    self._dl_label.set(s)
                self.after(0, _upd)

        elif d["status"] == "finished":
            def _proc():
                self._prog_bar.set(0.99)
                self._dl_label.set("Processando...")
            self.after(0, _proc)


if __name__ == "__main__":
    app = App()
    app.mainloop()
