#!/usr/bin/env python3
"""Revisa textos em pt-BR: anglicismos, datas, números e moeda no formato americano, palavras sem acento e termos inconsistentes.

    revisor.py hook                        # PostToolUse em Write e Edit (lê o JSON do Claude Code na entrada padrão)
    revisor.py revisar ARQUIVO.md [--json]

Configuração por projeto em <projeto>/.claude/pt-br-revisor.json (procurada a partir da pasta do arquivo)
e global em ~/.claude/pt-br-revisor.json:
    {
      "termos": {"preferido": ["variante", "outra variante"]},
      "anglicismos": {"palavra": "sugestão"},
      "permitir": ["feedback"],
      "ignorar_arquivos": ["CHANGELOG.md", "docs/en/**"],
      "regras": {"anglicismos": true, "datas": true, "numeros": true, "moeda": true, "acentos": true, "termos": true}
    }

Código (blocos e `trechos`), URLs e textos que parecem estar em inglês são ignorados.
"""

import argparse
import bisect
import fnmatch
import json
import re
import sys
from pathlib import Path

HOME = Path.home()
NOME_CONFIG = "pt-br-revisor.json"
REGRAS = ("anglicismos", "datas", "numeros", "moeda", "acentos", "termos")
MAX_AVISOS = 15

ANGLICISMOS = {
    "deadline": "prazo", "feedback": "retorno, opinião", "meeting": "reunião", "performance": "desempenho",
    "budget": "orçamento", "insight": "percepção, ideia", "insights": "percepções, ideias", "report": "relatório",
    "update": "atualização", "updates": "atualizações", "feature": "funcionalidade", "features": "funcionalidades",
    "approach": "abordagem", "target": "alvo, público-alvo", "workaround": "solução alternativa", "default": "padrão",
    "setup": "configuração", "troubleshooting": "solução de problemas", "dashboard": "painel",
    "checklist": "lista de verificação", "follow-up": "acompanhamento", "brainstorm": "discussão de ideias",
    "settings": "configurações", "user": "usuário", "users": "usuários", "password": "senha",
    "overview": "visão geral", "highlights": "destaques", "tips": "dicas", "warning": "aviso",
    "guidelines": "diretrizes", "best practices": "boas práticas", "review": "revisão", "template": "modelo",
    "expertise": "experiência, conhecimento", "delay": "atraso", "tracking": "acompanhamento",
    "stakeholders": "partes interessadas", "kickoff": "reunião inicial", "home office": "trabalho remoto",
    "full-time": "tempo integral", "part-time": "meio período", "onboarding": "integração",
    "startar": "iniciar", "printar": "imprimir, capturar a tela", "linkar": "vincular", "deletar": "apagar, excluir",
    "customizar": "personalizar", "atachar": "anexar", "performar": "ter bom desempenho",
}

SEM_ACENTO = {
    "nao": "não", "voce": "você", "voces": "vocês", "tambem": "também", "entao": "então", "ja": "já",
    "ate": "até", "apos": "após", "alem": "além", "porem": "porém", "atraves": "através", "tres": "três",
    "mes": "mês", "ninguem": "ninguém", "alguem": "alguém", "sera": "será", "estao": "estão", "sao": "são",
    "codigo": "código", "codigos": "códigos", "pagina": "página", "paginas": "páginas", "usuario": "usuário",
    "usuarios": "usuários", "necessario": "necessário", "obrigatorio": "obrigatório", "unico": "único",
    "unica": "única", "proximo": "próximo", "proxima": "próxima", "ultimo": "último", "ultima": "última",
    "padrao": "padrão", "padroes": "padrões", "relatorio": "relatório", "historico": "histórico",
    "metodo": "método", "parametro": "parâmetro", "parametros": "parâmetros", "diretorio": "diretório",
    "repositorio": "repositório", "conteudo": "conteúdo", "nivel": "nível", "facil": "fácil",
    "dificil": "difícil", "rapido": "rápido", "logica": "lógica", "basico": "básico", "automatico": "automático",
    "minimo": "mínimo", "maximo": "máximo", "saida": "saída", "numeros": "números", "periodo": "período",
    "area": "área", "tecnico": "técnico", "grafico": "gráfico", "graficos": "gráficos", "util": "útil",
    "uteis": "úteis", "pre-requisito": "pré-requisito", "pre-requisitos": "pré-requisitos",
}
# Terminações que, sem acento, não existem em português: -cao, -coes, -sao, -soes, -avel, -ivel, -aveis, -iveis.
SUFIXOS = [("cao", "ção"), ("coes", "ções"), ("sao", "são"), ("soes", "sões"),
           ("aveis", "áveis"), ("iveis", "íveis"), ("avel", "ável"), ("ivel", "ível")]
EXCECOES_SUFIXO = {"travel", "gravel", "unravel", "gavel", "navel", "ravel", "drivel", "swivel", "shrivel", "snivel"}

# Grupos de grafias equivalentes: o arquivo deve usar uma só.
GRUPOS = [["e-mail", "email"], ["on-line", "online"], ["login", "log-in"],
          ["front-end", "frontend"], ["back-end", "backend"]]

SIMBOLOS = {"USD": "US$", "BRL": "R$"}
MESES_EN = (r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
            r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)")
PT = {"de", "que", "não", "para", "com", "uma", "os", "as", "do", "da", "em", "é", "no", "na", "se", "por", "mais"}
EN = {"the", "and", "of", "to", "is", "with", "for", "that", "this", "are", "be", "on", "it", "you", "in"}


# Configuração

def ler_json(caminho):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def achar_config_projeto(arquivo):
    for pasta in Path(arquivo).resolve().parents:
        cand = pasta / ".claude" / NOME_CONFIG
        if cand.is_file() and pasta != HOME:
            return pasta, ler_json(cand)
        if pasta == HOME:
            break
    return None, {}


def config(arquivo):
    """Junta a configuração global e a do projeto; a do projeto vence."""
    glob, (raiz, proj) = ler_json(HOME / ".claude" / NOME_CONFIG), achar_config_projeto(arquivo)
    cfg = {"raiz": raiz, "regras": {r: True for r in REGRAS}, "termos": {}, "anglicismos": dict(ANGLICISMOS),
           "permitir": set(), "ignorar_arquivos": []}
    for c in (glob, proj):
        cfg["regras"].update(c.get("regras") or {})
        cfg["termos"].update(c.get("termos") or {})
        cfg["anglicismos"].update(c.get("anglicismos") or {})
        cfg["permitir"] |= {p.lower() for p in c.get("permitir") or []}
        cfg["ignorar_arquivos"] += c.get("ignorar_arquivos") or []
    return cfg


def ignorado(arquivo, cfg):
    p = Path(arquivo).resolve()
    rel = str(p.relative_to(cfg["raiz"])) if cfg["raiz"] and cfg["raiz"] in p.parents else p.name
    return any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(p.name, g) for g in cfg["ignorar_arquivos"])


# Análise

def mascarar(texto):
    """Troca por espaços o que não é prosa (front matter, código, URLs, destinos de links, HTML), mantendo as posições."""
    branco = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    texto = re.sub(r"\A---\n.*?\n---\n", branco, texto, flags=re.S)
    texto = re.sub(r"^(```|~~~).*?(^\1[^\n]*$|\Z)", branco, texto, flags=re.S | re.M)
    texto = re.sub(r"`[^`\n]+`", branco, texto)
    texto = re.sub(r"\]\([^)\n]*\)", branco, texto)
    texto = re.sub(r"<[^>\n]+>", branco, texto)
    texto = re.sub(r"\b(?:https?://|www\.)\S+", branco, texto)
    return texto


def parece_ingles(texto):
    palavras = re.findall(r"\w+", texto.lower())
    return sum(w in EN for w in palavras) > sum(w in PT for w in palavras)


def palavra(termo, flags=re.I):
    return re.compile(r"(?<![\w-])" + re.escape(termo).replace(r"\ ", r"\s+") + r"(?![\w-])", flags)


def para_brasileiro(num):
    """1,234.56 -> 1.234,56"""
    return num.replace(",", "\0").replace(".", ",").replace("\0", ".")


def achados(texto, cfg):
    """Lista de (início, fim, regra, trecho, sugestão)."""
    t = mascarar(texto)
    regras, permitir, out = cfg["regras"], cfg["permitir"], []
    ocupado = []

    def add(m, regra, sugestao, trecho=None):
        if any(a < m.end() and m.start() < b for a, b in ocupado):
            return
        ocupado.append((m.start(), m.end()))
        out.append((m.start(), m.end(), regra, trecho or m.group(0), sugestao))

    if regras.get("termos"):
        for preferido, variantes in cfg["termos"].items():
            for v in variantes:
                flags = 0 if v.lower() == preferido.lower() else re.I
                for m in palavra(v, flags).finditer(t):
                    add(m, "termo", preferido)
        for grupo in GRUPOS:
            usos = {g: len(palavra(g).findall(t)) for g in grupo}
            if sum(1 for n in usos.values() if n) < 2:
                continue
            principal = max(grupo, key=lambda g: (usos[g], -grupo.index(g)))
            for g in grupo:
                if g != principal:
                    for m in palavra(g).finditer(t):
                        add(m, "termo inconsistente", f"{principal} (a forma mais usada no arquivo)")

    if regras.get("moeda"):
        for m in re.finditer(r"(?<![\w$])(R\$|US\$|\$|USD|BRL)\s?(\d[\d.,]*\d|\d)", t):
            simbolo, num = m.groups()
            americano = re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?|\d+\.\d{1,2}", num)
            br = para_brasileiro(num) if americano else num
            if simbolo == "$":
                add(m, "moeda", f"R$ {br} ou US$ {br}")
            elif americano or simbolo in ("R$", "US$") and not m.group(0)[len(simbolo)].isspace():
                add(m, "moeda", f"{SIMBOLOS.get(simbolo, simbolo)} {br}")

    if regras.get("datas"):
        for m in re.finditer(r"\b(0?[1-9]|1[0-2])/(1[3-9]|2\d|3[01])/(\d{4}|\d{2})\b", t):
            add(m, "data americana", f"{m.group(2)}/{int(m.group(1)):02d}/{m.group(3)}")
        for m in re.finditer(MESES_EN + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b", t):
            add(m, "data em inglês", "dd/mm/aaaa ou “10 de novembro de 2026”")
        for m in re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s?([AaPp])\.?\s?[Mm]\b", t):
            h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)
            add(m, "hora americana", f"{h}h{m.group(2) or ''}")

    if regras.get("numeros"):
        for m in re.finditer(r"(?<![\w.,])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\w,]|\.\d)", t):
            add(m, "número americano", para_brasileiro(m.group(0)))
        for m in re.finditer(r"(?<![\w.,])\d+\.\d+(?=\s?%)", t):
            add(m, "número americano", para_brasileiro(m.group(0)))

    if regras.get("anglicismos"):
        for termo, sugestao in cfg["anglicismos"].items():
            if termo.lower() not in permitir:
                for m in palavra(termo).finditer(t):
                    add(m, "anglicismo", sugestao)

    if regras.get("acentos"):
        for m in re.finditer(r"(?<![\w-])[A-Za-z][A-Za-z-]*(?![\w-])", t):
            w = m.group(0)
            lw = w.lower()
            if lw in permitir or lw in EXCECOES_SUFIXO:
                continue
            certo = SEM_ACENTO.get(lw)
            if not certo and len(lw) >= 5 and "-" not in lw:
                certo = next((lw[: -len(s)] + c for s, c in SUFIXOS if lw.endswith(s)), None)
            if certo:
                add(m, "sem acento", certo[0].upper() + certo[1:] if w[0].isupper() else certo)

    return sorted(out)


def com_linhas(texto, lista):
    inicios = [0] + [i + 1 for i, c in enumerate(texto) if c == "\n"]
    return [(bisect.bisect_right(inicios, a), regra, trecho, sug) for a, b, regra, trecho, sug in lista]


def formatar(itens):
    return [f"- L{l} {regra}: “{trecho}” → {sug}" for l, regra, trecho, sug in itens]


# Hook

def hook():
    try:
        dados = json.load(sys.stdin)
    except ValueError:
        return 0
    entrada = dados.get("tool_input") or {}
    caminho = entrada.get("file_path", "")
    if not caminho.lower().endswith((".md", ".markdown")) or dados.get("tool_name") not in ("Write", "Edit"):
        return 0
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except OSError:
        return 0
    cfg = config(caminho)
    if ignorado(caminho, cfg) or parece_ingles(mascarar(texto)):
        return 0
    lista = achados(texto, cfg)
    novo = entrada.get("new_string") if dados.get("tool_name") == "Edit" else None
    if novo is not None:
        trechos = [(m.start(), m.end()) for m in re.finditer(re.escape(novo), texto)] if novo else []
        lista = [x for x in lista if any(a <= x[0] < b for a, b in trechos)]
    if not lista:
        return 0
    itens = com_linhas(texto, lista)
    linhas = formatar(itens[:MAX_AVISOS])
    if len(itens) > MAX_AVISOS:
        linhas.append(f"- e mais {len(itens) - MAX_AVISOS}; use a skill pt-br-revisor para revisar o arquivo inteiro.")
    print(
        f"[pt-br-revisor] {Path(caminho).name}: {len(itens)} ponto(s) para revisar em pt-BR.\n" + "\n".join(linhas) +
        "\nCorrija o que fizer sentido no contexto. Se um termo for aceito no projeto, ponha-o em `permitir` "
        f"ou `termos` de .claude/{NOME_CONFIG}.",
        file=sys.stderr,
    )
    return 2


# Revisão de um arquivo inteiro

def revisar(argv):
    ap = argparse.ArgumentParser(prog="revisor.py revisar", description="Revisa um arquivo inteiro.")
    ap.add_argument("arquivo")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    a = ap.parse_args(argv)
    try:
        texto = Path(a.arquivo).read_text(encoding="utf-8")
    except OSError as e:
        sys.exit(f"Não consegui ler {a.arquivo}: {e}")
    cfg = config(a.arquivo)
    itens = com_linhas(texto, achados(texto, cfg))
    if a.json:
        print(json.dumps([{"linha": l, "regra": r, "trecho": t, "sugestao": s} for l, r, t, s in itens],
                         ensure_ascii=False, indent=2))
        return 0
    avisos = []
    if parece_ingles(mascarar(texto)):
        avisos.append("Atenção: o texto parece estar em inglês; o hook ignora arquivos assim.")
    if ignorado(a.arquivo, cfg):
        avisos.append("Atenção: este arquivo está em `ignorar_arquivos`; o hook não o revisa.")
    origem = cfg["raiz"] / ".claude" / NOME_CONFIG if cfg["raiz"] else "nenhuma (só os padrões)"
    print("\n".join(avisos + [f"{a.arquivo}: {len(itens)} ponto(s). Configuração do projeto: {origem}"] + formatar(itens)))
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["hook"]:
        sys.exit(hook())
    if sys.argv[1:2] == ["revisar"]:
        sys.exit(revisar(sys.argv[2:]))
    sys.exit(__doc__)
