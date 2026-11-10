"""Testes do pt-br-revisor: hook e revisão de arquivo, com HOME temporário."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "pt-br-revisor" / "scripts" / "revisor.py"


class Revisor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.projeto = self.home / "projeto"
        (self.projeto / "docs").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def arquivo(self, texto, nome="docs/leia.md"):
        p = self.projeto / nome
        p.write_text(texto, encoding="utf-8")
        return p

    def config(self, **kv):
        (self.projeto / ".claude").mkdir(exist_ok=True)
        (self.projeto / ".claude" / "pt-br-revisor.json").write_text(json.dumps(kv))

    def rodar(self, *args, entrada=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], input=entrada, capture_output=True, text=True,
            env={**os.environ, "HOME": str(self.home)},
        )

    def hook(self, caminho, nome="Write", **entrada):
        dados = {"tool_name": nome, "tool_input": {"file_path": str(caminho), **entrada}, "tool_response": {}}
        return self.rodar("hook", entrada=json.dumps(dados))

    def revisar(self, texto):
        r = self.rodar("revisar", str(self.arquivo(texto)), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return [(i["regra"], i["trecho"], i["sugestao"]) for i in json.loads(r.stdout)]

    # Regras
    def test_anglicismo(self):
        self.assertIn(("anglicismo", "deadline", "prazo"), self.revisar("O deadline é amanhã, para a equipe.\n"))

    def test_data_hora(self):
        r = self.revisar("A reunião é em 11/25/2026 às 3:30 PM, e não em November 10, 2026.\n")
        self.assertIn(("data americana", "11/25/2026", "25/11/2026"), r)
        self.assertIn(("hora americana", "3:30 PM", "15h30"), r)
        self.assertEqual(r[-1][0], "data em inglês")
        self.assertEqual(self.revisar("A reunião é em 10/11/2026, como de costume.\n"), [])

    def test_numeros_e_moeda(self):
        r = self.revisar("Custou $1,250.50 e R$1.234,56 para 1,000 pessoas, com 12.5% de desconto na versão 1.2.\n")
        self.assertIn(("moeda", "$1,250.50", "R$ 1.250,50 ou US$ 1.250,50"), r)
        self.assertIn(("moeda", "R$1.234,56", "R$ 1.234,56"), r)
        self.assertIn(("número americano", "1,000", "1.000"), r)
        self.assertIn(("número americano", "12.5", "12,5"), r)
        self.assertEqual(len(r), 4)

    def test_acentos(self):
        r = self.revisar("Voce nao precisa da configuracao, so do Disponivel e das opcoes de travel.\n")
        self.assertIn(("sem acento", "Voce", "Você"), r)
        self.assertIn(("sem acento", "nao", "não"), r)
        self.assertIn(("sem acento", "configuracao", "configuração"), r)
        self.assertIn(("sem acento", "Disponivel", "Disponível"), r)
        self.assertIn(("sem acento", "opcoes", "opções"), r)
        self.assertNotIn("travel", [t for _, t, _ in r])

    def test_termos_inconsistentes(self):
        r = self.revisar("Mande um e-mail para a equipe. Depois outro e-mail. Ou um email.\n")
        self.assertEqual(r, [("termo inconsistente", "email", "e-mail (a forma mais usada no arquivo)")])

    def test_ignora_codigo_e_urls(self):
        texto = "Use `deadline` e veja https://ex.com/deadline para a equipe.\n\n```\nnao $1,000.00\n```\n"
        self.assertEqual(self.revisar(texto), [])

    # Configuração por projeto
    def test_config_do_projeto(self):
        self.config(termos={"GitHub": ["Github"], "pull request": ["merge request"]},
                    anglicismos={"roadmap": "plano de evolução"}, permitir=["deadline"])
        r = self.revisar("O deadline do roadmap está no Github e no GitHub, num merge request da equipe.\n")
        self.assertEqual(r, [
            ("anglicismo", "roadmap", "plano de evolução"),
            ("termo", "Github", "GitHub"),
            ("termo", "merge request", "pull request"),
        ])

    def test_regras_desligadas(self):
        self.config(regras={"anglicismos": False})
        self.assertEqual(self.revisar("O deadline é amanhã, para a equipe.\n"), [])

    # Hook
    def test_hook_aponta_com_linha(self):
        p = self.arquivo("# Título\n\nO deadline é amanhã, para a equipe.\n")
        r = self.hook(p, content="")
        self.assertEqual(r.returncode, 2)
        self.assertIn("leia.md: 1 ponto(s)", r.stderr)
        self.assertIn("- L3 anglicismo: “deadline” → prazo", r.stderr)

    def test_hook_edit_so_o_trecho_novo(self):
        p = self.arquivo("O deadline é amanhã.\n\nA configuracao está pronta para a equipe.\n")
        r = self.hook(p, "Edit", old_string="x", new_string="A configuracao está pronta")
        self.assertEqual(r.returncode, 2)
        self.assertIn("configuracao", r.stderr)
        self.assertNotIn("deadline", r.stderr)

    def test_hook_silencioso(self):
        self.assertEqual(self.hook(self.arquivo("Tudo certo com o texto da equipe.\n")).returncode, 0)
        p = self.arquivo("nao deadline\n", "notas.txt")
        self.assertEqual(self.hook(p).returncode, 0)
        p = self.arquivo("The deadline is on the 11/25/2026 and it is fine.\n")
        self.assertEqual(self.hook(p).returncode, 0)
        p = self.arquivo("O deadline é amanhã, para a equipe.\n", "CHANGELOG.md")
        self.config(ignorar_arquivos=["CHANGELOG.md"])
        self.assertEqual(self.hook(p).returncode, 0)


if __name__ == "__main__":
    unittest.main()
