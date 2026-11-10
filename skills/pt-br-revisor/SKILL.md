---
name: pt-br-revisor
description: Esta skill deve ser usada quando o hook pt-br-revisor apontar problemas num arquivo .md, e quando o usuário pedir para "revisar o português", "revisar este arquivo", "corrigir acentos", "tirar os anglicismos" ou "padronizar os termos" de um texto. This skill should be used when the pt-br-revisor hook flags a .md file, and when the user asks to "review the Portuguese", "proofread this file", "fix accents", "remove anglicisms" or "standardize terms" in a Brazilian Portuguese text.
---

# Revisor pt-BR

O hook revisa só o trecho escrito ou editado. Esta skill revisa **um arquivo inteiro**.

O script fica em `scripts/revisor.py`, ao lado deste SKILL.md. Use o caminho absoluto.

## Revisar um arquivo

1. Rode a revisão automática:

   ```
   python3 <pasta desta skill>/scripts/revisor.py revisar <arquivo.md>
   ```

   A saída lista cada ponto com a linha, a regra, o trecho e a sugestão, e diz qual configuração do projeto foi usada.

2. Leia o arquivo e confira cada ponto no contexto. O script não entende o sentido: `review` pode ser nome de comando, `1,000` pode ser um decimal, `$` pode ser de uma variável. Ignore código, nomes próprios, comandos e citações.

3. Na mesma leitura, procure o que o script não pega, nas mesmas categorias:
   - anglicismos fora da lista, quando há um termo em português claro e usual;
   - datas, horas, números e valores no formato americano;
   - palavras sem acento ou com acento errado;
   - o mesmo conceito escrito de formas diferentes no arquivo.

4. Corrija com Edit os pontos claros. Liste ao usuário os duvidosos, com a sugestão, para ele decidir.

5. Se o usuário aceitar um termo de vez (por exemplo, "deploy" no projeto), ou quiser fixar uma grafia, proponha incluí-lo na configuração do projeto.

## Formato pt-BR

- Datas: `10/11/2026` ou `10 de novembro de 2026`. Horas: `15h30` ou `15:30`.
- Números: `1.234,56`; porcentagem: `12,5%`.
- Moeda: `R$ 1.234,56` e `US$ 10,50`, com espaço depois do símbolo.

## Configuração por projeto

Em `<projeto>/.claude/pt-br-revisor.json` (e, para todos os projetos, em `~/.claude/pt-br-revisor.json`):

```json
{
  "termos": {"pull request": ["merge request"], "GitHub": ["Github", "github"]},
  "anglicismos": {"roadmap": "plano de evolução"},
  "permitir": ["deploy", "template"],
  "ignorar_arquivos": ["CHANGELOG.md", "docs/en/**"],
  "regras": {"anglicismos": true, "datas": true, "numeros": true, "moeda": true, "acentos": true, "termos": true}
}
```

- `termos`: a grafia preferida e as variantes a trocar por ela. Se a variante só difere na caixa, a comparação respeita maiúsculas.
- `anglicismos`: palavras a apontar além da lista padrão, com a sugestão.
- `permitir`: palavras que não devem ser apontadas.
- `ignorar_arquivos`: padrões de arquivos que o hook não revisa.
- `regras`: liga ou desliga cada verificação.
