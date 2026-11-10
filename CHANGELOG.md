# Changelog

## 1.0.0 — 10/11/2026

- Hook `PostToolUse` em `Write` e `Edit` de arquivos `.md`, que aponta no trecho novo, com linha e sugestão:
  - anglicismos desnecessários;
  - datas, horas, números e moeda no formato americano;
  - palavras sem acento;
  - termos inconsistentes no arquivo e termos fora da grafia do projeto.
- Ignora código, URLs, destinos de links, HTML, front matter e textos em inglês.
- Configuração por projeto em `.claude/pt-br-revisor.json` e global em `~/.claude/pt-br-revisor.json`: `termos`, `anglicismos`, `permitir`, `ignorar_arquivos` e `regras`.
- Skill `pt-br-revisor` e `scripts/revisor.py revisar` para revisar um arquivo inteiro.
- Testes e CI.
