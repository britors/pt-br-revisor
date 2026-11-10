# pt-br-revisor

[Português](#português) · [English](#english)

## Português

Plugin do [Claude Code](https://claude.com/claude-code) que revisa o português dos arquivos Markdown. Sempre que o Claude escreve ou edita um `.md`, o hook confere o trecho novo e aponta o que soa americano ou descuidado em pt-BR, com a linha e a sugestão.

### O que ele aponta

| Regra | Exemplo | Sugestão |
| --- | --- | --- |
| Anglicismo desnecessário | `deadline`, `feedback`, `default` | prazo, retorno, padrão |
| Data e hora americanas | `11/25/2026`, `November 10, 2026`, `3:30 PM` | 25/11/2026, 15h30 |
| Número americano | `1,000`, `12.5%` | 1.000, 12,5% |
| Moeda | `$1,250.50`, `R$1.234,56` | R$ 1.250,50 ou US$ 1.250,50, R$ 1.234,56 |
| Palavra sem acento | `nao`, `voce`, `configuracao`, `disponivel` | não, você, configuração, disponível |
| Termo inconsistente | `e-mail` e `email` no mesmo arquivo | a forma mais usada |
| Termo do projeto | `Github` (configurado) | GitHub |

Ignora blocos e trechos de código, URLs, destinos de links, HTML e front matter. Arquivos que parecem estar em inglês são pulados. Sem nada a apontar, o hook fica em silêncio e não gasta tokens.

### Instalação

No Claude Code 2.1.275 ou mais novo, dentro de uma sessão:

```
/plugin install pt-br-revisor --marketplace britors/pt-br-revisor
```

Em versões anteriores:

```
/plugin marketplace add britors/pt-br-revisor
/plugin install pt-br-revisor@pt-br-revisor
```

Precisa de `python3` no PATH.

### Revisar um arquivo inteiro

Peça ao Claude: "revise o português do README.md". A skill roda a revisão automática, confere cada ponto no contexto, corrige os claros e lista os duvidosos.

Também dá para rodar direto:

```
python3 skills/pt-br-revisor/scripts/revisor.py revisar docs/guia.md [--json]
```

### Configuração por projeto

Em `<projeto>/.claude/pt-br-revisor.json`, procurado a partir da pasta do arquivo. Para todos os projetos, use `~/.claude/pt-br-revisor.json`; o do projeto vence.

```json
{
  "termos": {"pull request": ["merge request"], "GitHub": ["Github", "github"]},
  "anglicismos": {"roadmap": "plano de evolução"},
  "permitir": ["deploy", "template"],
  "ignorar_arquivos": ["CHANGELOG.md", "docs/en/**"],
  "regras": {"anglicismos": true, "datas": true, "numeros": true, "moeda": true, "acentos": true, "termos": true}
}
```

- `termos`: a grafia preferida e as variantes a trocar por ela.
- `anglicismos`: palavras a apontar além da lista padrão, com a sugestão.
- `permitir`: palavras que não devem ser apontadas.
- `ignorar_arquivos`: padrões de arquivos que o hook não revisa.
- `regras`: liga ou desliga cada verificação.

### Estrutura

```
.claude-plugin/plugin.json                    manifesto
.claude-plugin/marketplace.json               marketplace de um plugin só
skills/pt-br-revisor/SKILL.md                 revisão de um arquivo inteiro
skills/pt-br-revisor/scripts/revisor.py       hook e revisão
hooks/hooks.json                              PostToolUse em Write e Edit
tests/test_revisor.py                         testes
```

Para rodar os testes: `python3 -m unittest discover -s tests`.

## English

[Claude Code](https://claude.com/claude-code) plugin that proofreads Brazilian Portuguese in Markdown files.

- A `PostToolUse` hook on `Write` and `Edit` of `.md` files flags unnecessary anglicisms, US-style dates, times, numbers and currency, words missing their accents and inconsistent terms, with the line and a suggestion. Code, URLs and English-language files are skipped.
- A per-project term list lives in `.claude/pt-br-revisor.json` (preferred terms, extra anglicisms, allowed words, ignored files, rules on/off).
- The `pt-br-revisor` skill reviews a whole file; `revisor.py revisar FILE.md` runs the automatic checks.

Install with `/plugin install pt-br-revisor --marketplace britors/pt-br-revisor`.

## Licença / License

[GPL-3.0](LICENSE)
