"""
CheckMatte – Agenda leve para certificados digitais
Suporte: .pfx, .p12, .cer, .crt, .pem, .der
Pool de múltiplas senhas, log de erros, busca recursiva em subpastas.
"""

import os
import json
import hashlib
import datetime
import sys
import traceback
from pathlib import Path
from collections import defaultdict

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
import keyring
import tkinter as tk
from tkinter import messagebox, simpledialog, Listbox, Scrollbar, Button, Label, Frame, END, Canvas, Toplevel, Entry, BooleanVar

# ------------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------------
PASTA_CERTIFICADOS = Path("D:\\CheckMatte\\MeusCertificados")
DIAS_AVISO = 5
CACHE_FILE = Path("cache_checkmatte.json")
LOG_FILE = Path("checkmatte_log.txt")
SERVICE_NAME = "CheckMatte"
SENHAS_KEY = "lista_senhas"
# ------------------------------------------------------------

# ---------- Funções de senha ----------
def carregar_lista_senhas():
    raw = keyring.get_password(SERVICE_NAME, SENHAS_KEY)
    if raw:
        try:
            return json.loads(raw)
        except:
            return []
    return []

def salvar_lista_senhas(lista_senhas):
    keyring.set_password(SERVICE_NAME, SENHAS_KEY, json.dumps(lista_senhas))

def inicializar_senhas():
    senhas = carregar_lista_senhas()
    if not senhas:
        root_temp = tk.Tk()
        root_temp.withdraw()
        senha_inicial = simpledialog.askstring(
            "CheckMatte – Configuração inicial",
            "Nenhuma senha cadastrada.\nDigite a primeira senha para seus certificados:",
            show="*"
        )
        root_temp.destroy()
        if senha_inicial:
            senhas = [senha_inicial]
            salvar_lista_senhas(senhas)
        else:
            messagebox.showerror("Erro", "É necessário cadastrar ao menos uma senha. O programa será encerrado.")
            sys.exit(0)
    return senhas

# ---------- Leitura de certificados ----------
def hash_arquivo(caminho):
    with open(caminho, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def extrair_dados_certificado(caminho, lista_senhas):
    sufixo = caminho.suffix.lower()
    try:
        with open(caminho, "rb") as f:
            conteudo = f.read()

        if sufixo in (".pfx", ".p12"):
            for senha in lista_senhas:
                senha_bytes = senha.encode('utf-8', errors='ignore') if senha else None
                try:
                    pfx = pkcs12.load_pkcs12(conteudo, senha_bytes)
                    cert = pfx.cert.certificate
                    nome = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                    emissao = cert.not_valid_before.date()
                    expiracao = cert.not_valid_after.date()
                    return {"nome": nome, "emissao": str(emissao), "expiracao": str(expiracao)}, None
                except Exception as e:
                    continue
            return None, f"Nenhuma das {len(lista_senhas)} senhas funcionou para este arquivo PFX."

        elif sufixo in (".cer", ".crt", ".pem"):
            try:
                cert = x509.load_pem_x509_certificate(conteudo, default_backend())
            except Exception:
                try:
                    cert = x509.load_der_x509_certificate(conteudo, default_backend())
                except Exception as e:
                    return None, f"Falha ao carregar certificado PEM/DER: {e}"

            nome = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            emissao = cert.not_valid_before.date()
            expiracao = cert.not_valid_after.date()
            return {"nome": nome, "emissao": str(emissao), "expiracao": str(expiracao)}, None

        elif sufixo == ".der":
            cert = x509.load_der_x509_certificate(conteudo, default_backend())
            nome = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            emissao = cert.not_valid_before.date()
            expiracao = cert.not_valid_after.date()
            return {"nome": nome, "emissao": str(emissao), "expiracao": str(expiracao)}, None

        else:
            return None, f"Formato de arquivo não suportado: {sufixo}"

    except Exception as e:
        return None, f"Erro inesperado: {e}"

# ---------- Log de erros ----------
def salvar_log(mensagem):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()} - {mensagem}\n")

def carregar_log():
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "Nenhum registro de erro ainda."

# ---------- Cache ----------
def carregar_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_cache(dados):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2)

# ---------- Interface gráfica ----------
class CheckMatteApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CheckMatte – Agenda de Certificados")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        self.ano_atual = datetime.date.today().year
        self.mes_atual = datetime.date.today().month

        self.certificados = []
        self.lista_senhas = inicializar_senhas()

        # ---- Cabeçalho ----
        Label(self.root, text="CheckMatte", font=("Arial", 14, "bold")).pack(pady=(10,0))
        Label(self.root, text="Agenda de Vencimentos", font=("Arial", 10)).pack(pady=(0,5))

        frame_nav = Frame(self.root)
        frame_nav.pack(pady=5)

        self.btn_anterior = Button(frame_nav, text="◀ Mês anterior", command=self.mes_anterior)
        self.btn_anterior.pack(side="left", padx=5)

        self.lbl_mes = Label(frame_nav, text="", font=("Arial", 11, "bold"), width=20)
        self.lbl_mes.pack(side="left", padx=10)

        self.btn_proximo = Button(frame_nav, text="Próximo mês ▶", command=self.mes_proximo)
        self.btn_proximo.pack(side="left", padx=5)

        # Área rolável da agenda
        frame_agenda = Frame(self.root)
        frame_agenda.pack(fill="both", expand=True, padx=10, pady=(0,5))

        self.canvas = Canvas(frame_agenda, borderwidth=0, highlightthickness=0)
        self.scrollbar = Scrollbar(frame_agenda, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = Frame(self.canvas)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Botões inferiores
        frame_botoes = Frame(self.root)
        frame_botoes.pack(pady=5)

        Button(frame_botoes, text="Atualizar certificados", command=self.recarregar_tudo).pack(side="left", padx=5)
        Button(frame_botoes, text="Gerenciar senhas", command=self.abrir_gerenciador).pack(side="left", padx=5)
        Button(frame_botoes, text="Ver Log", command=self.abrir_log).pack(side="left", padx=5)

        self.recarregar_tudo()
        self.root.mainloop()

    def mes_anterior(self):
        if self.mes_atual == 1:
            self.mes_atual = 12
            self.ano_atual -= 1
        else:
            self.mes_atual -= 1
        self.mostrar_mes()

    def mes_proximo(self):
        if self.mes_atual == 12:
            self.mes_atual = 1
            self.ano_atual += 1
        else:
            self.mes_atual += 1
        self.mostrar_mes()

    def recarregar_tudo(self):
        self.lista_senhas = carregar_lista_senhas()
        if not self.lista_senhas:
            messagebox.showerror("Erro", "Nenhuma senha cadastrada. Use 'Gerenciar senhas'.")
            return

        cache = carregar_cache()
        extensoes = ["*.pfx", "*.p12", "*.cer", "*.crt", "*.pem", "*.der"]
        arquivos = []
        for ext in extensoes:
            # USANDO rglob PARA VARREDURA RECURSIVA EM SUBPASTAS
            arquivos.extend(PASTA_CERTIFICADOS.rglob(ext))
        arquivos = list(set(arquivos))

        self.certificados = []
        erros = []

        for arq in arquivos:
            str_path = str(arq)
            hash_arq = hash_arquivo(arq)

            if str_path in cache and cache[str_path].get("hash") == hash_arq:
                dados = cache[str_path]
                try:
                    exp = datetime.date.fromisoformat(dados["expiracao"])
                    # Obtém caminho relativo à pasta base
                    caminho_relativo = arq.relative_to(PASTA_CERTIFICADOS)
                    self.certificados.append({
                        "nome": dados["nome"],
                        "expiracao": exp,
                        "arquivo": str(caminho_relativo)
                    })
                except Exception:
                    pass
                continue

            dados_novo, erro = extrair_dados_certificado(arq, self.lista_senhas)
            if dados_novo:
                dados_novo["hash"] = hash_arq
                cache[str_path] = dados_novo
                exp = datetime.date.fromisoformat(dados_novo["expiracao"])
                caminho_relativo = arq.relative_to(PASTA_CERTIFICADOS)
                self.certificados.append({
                    "nome": dados_novo["nome"],
                    "expiracao": exp,
                    "arquivo": str(caminho_relativo)
                })
            else:
                msg_erro = f"Falha ao ler {arq.name}: {erro}"
                erros.append(msg_erro)
                salvar_log(msg_erro)
                print(msg_erro)

        salvar_cache(cache)
        self.mostrar_mes()
        self.verificar_avisos()

    def mostrar_mes(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        self.lbl_mes.config(text=f"{meses[self.mes_atual-1]} de {self.ano_atual}")

        hoje = datetime.date.today()
        certificados_mes = defaultdict(list)
        for cert in self.certificados:
            exp = cert["expiracao"]
            if exp.year == self.ano_atual and exp.month == self.mes_atual:
                certificados_mes[exp.day].append(cert)

        if not certificados_mes:
            Label(self.scroll_frame, text="Nenhum certificado vence neste mês.", fg="gray").pack(pady=10)
            return

        for dia in sorted(certificados_mes.keys()):
            dia_frame = Frame(self.scroll_frame, bd=1, relief="solid", pady=4, padx=4)
            dia_frame.pack(fill="x", padx=5, pady=3)

            data = datetime.date(self.ano_atual, self.mes_atual, dia)
            dias_restantes = (data - hoje).days

            if dias_restantes < 0:
                cor_dia = "gray"
            elif 0 <= dias_restantes <= DIAS_AVISO:
                cor_dia = "red"
            elif dias_restantes <= 30:
                cor_dia = "orange"
            else:
                cor_dia = "green"

            Label(dia_frame, text=f"Dia {dia:02d}", font=("Arial", 10, "bold"), fg=cor_dia).pack(anchor="w")

            for cert in certificados_mes[dia]:
                # Mostra o nome do titular e o caminho relativo (subpasta/arquivo)
                texto = f"  • {cert['nome']} ({cert['arquivo']})"
                Label(dia_frame, text=texto, anchor="w", justify="left", fg="black").pack(anchor="w", padx=10)

    def verificar_avisos(self):
        """Nenhuma notificação será exibida. Apenas as cores na agenda indicam a urgência."""
        pass

    # ---------- Gerenciador de senhas ----------
    def abrir_gerenciador(self):
        janela = Toplevel(self.root)
        janela.title("Gerenciar senhas")
        janela.geometry("400x300")
        janela.resizable(False, False)

        Label(janela, text="Lista de senhas cadastradas", font=("Arial", 10, "bold")).pack(pady=5)

        frame_lista = Frame(janela)
        frame_lista.pack(fill="both", expand=True, padx=10, pady=5)

        scroll = Scrollbar(frame_lista)
        scroll.pack(side="right", fill="y")

        lista_widget = Listbox(frame_lista, yscrollcommand=scroll.set)
        lista_widget.pack(side="left", fill="both", expand=True)
        scroll.config(command=lista_widget.yview)

        def atualizar_lista():
            lista_widget.delete(0, END)
            for i, senha in enumerate(self.lista_senhas):
                lista_widget.insert(END, f"Senha {i+1}: {'*' * len(senha)}")

        atualizar_lista()

        def adicionar():
            nova = simpledialog.askstring("Nova senha", "Digite a nova senha:", show="*", parent=janela)
            if nova:
                self.lista_senhas.append(nova)
                salvar_lista_senhas(self.lista_senhas)
                atualizar_lista()
                messagebox.showinfo("Sucesso", "Senha adicionada. Use 'Atualizar certificados' para aplicar.", parent=janela)

        def remover():
            sel = lista_widget.curselection()
            if sel:
                idx = sel[0]
                if messagebox.askyesno("Confirmar", f"Remover a senha {idx+1}?", parent=janela):
                    del self.lista_senhas[idx]
                    salvar_lista_senhas(self.lista_senhas)
                    atualizar_lista()
                    if not self.lista_senhas:
                        messagebox.showwarning("Atenção", "Nenhuma senha restante! Cadastre ao menos uma.", parent=janela)

        def editar():
            sel = lista_widget.curselection()
            if sel:
                idx = sel[0]
                nova = simpledialog.askstring("Editar senha", "Digite a nova senha:", show="*", parent=janela)
                if nova:
                    self.lista_senhas[idx] = nova
                    salvar_lista_senhas(self.lista_senhas)
                    atualizar_lista()
                    messagebox.showinfo("Sucesso", "Senha alterada. Use 'Atualizar certificados' para aplicar.", parent=janela)

        frame_botoes = Frame(janela)
        frame_botoes.pack(pady=5)
        Button(frame_botoes, text="Adicionar", command=adicionar).pack(side="left", padx=5)
        Button(frame_botoes, text="Editar", command=editar).pack(side="left", padx=5)
        Button(frame_botoes, text="Remover", command=remover).pack(side="left", padx=5)

    # ---------- Janela de Log ----------
    def abrir_log(self):
        janela = Toplevel(self.root)
        janela.title("CheckMatte – Log de Problemas")
        janela.geometry("600x400")

        texto_log = carregar_log()
        text_widget = tk.Text(janela, wrap="word")
        text_widget.insert("1.0", texto_log)
        text_widget.config(state="disabled")
        text_widget.pack(fill="both", expand=True, padx=5, pady=5)

        Button(janela, text="Limpar Log", command=lambda: self.limpar_log(janela, text_widget)).pack(pady=5)

    def limpar_log(self, janela, text_widget):
        if messagebox.askyesno("Confirmar", "Apagar todo o registro de log?", parent=janela):
            LOG_FILE.write_text("", encoding="utf-8")
            text_widget.config(state="normal")
            text_widget.delete("1.0", END)
            text_widget.insert("1.0", "Nenhum registro de erro ainda.")
            text_widget.config(state="disabled")

if __name__ == "__main__":
    CheckMatteApp()