# TravelRobot

Coleta preços e avaliações de hotéis (Google Hotels e Decolar), distância até um ponto de referência (Google Maps) e promoções de pontos e milhas (Smiles, Livelo, Esfera, o resumo diário Radar PPV e as notícias de três blogs de milhas). O resultado sai em CSV e HTML.

Reescrita em Python do projeto original em C#, que está preservado na pasta [`old code`](old%20code/).

## Instalação

Requer Python 3.12 ou superior.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
playwright install chromium
```

## Uso

Ajuste as buscas em `config/searches.toml` e rode a partir da raiz do projeto:

```powershell
python -m travelrobot            # usa config/searches.toml
python -m travelrobot --headed   # mostra o navegador
python -m travelrobot -v         # log detalhado
```

| Código de saída | Significado |
| --- | --- |
| 0 | Coletou ofertas (veja no resumo se houve falhas parciais) |
| 1 | Nenhuma oferta coletada |
| 2 | Configuração inválida |

A saída vai para `output/` e os logs para `logs/`. Os arquivos são regravados a cada etapa, então uma falha no meio preserva o que já foi coletado.

As colunas `preco` e `moeda` trazem o valor como o site exibe. No Google Hotels o preço é por noite, e a moeda depende da sessão: ele pode mostrar US$ mesmo com a página em português.

As avaliações vêm do resumo do Google: nota geral de 0 a 5 (`avaliacao_nota`), quantidade (`avaliacao_quantidade`), temas bem ou mal avaliados, com o número de menções (`temas_positivos`, `temas_negativos`), e notas de outros sites (`notas_outros_sites`). O Google não dá nota numérica por categoria.

As promoções saem em `FrequentFlyersList_AAAAMMDD.csv`, uma linha por promoção ainda válida, com `fonte`, `programa`, `parceiro`, `tipo`, `beneficio` (como o site descreve, por exemplo "Bonificação até 120%"), `valor` (só o número, para ordenar), `inicio`, `fim` e `link`.

- **Smiles:** o robô abre a página de promoções e lê o JSON que a própria página baixa para montar os cartões, que traz datas de início e fim e categoria. Ele não chama essa API diretamente, porque o `robots.txt` da Smiles não permite URLs com parâmetros. Entram também as promoções já anunciadas que ainda vão começar, identificadas pela coluna `inicio`. A hora de encerramento não é gravada, só a data.
- **Radar PPV:** é lido pela API pública do WordPress do Pontos pra Voar, que publica o resumo à noite, então pela manhã o robô usa o do dia anterior e descarta as linhas já vencidas. Cobre acúmulo por real gasto, transferência bonificada, compra de pontos e clubes de vários programas. A validade vem sem ano, que é deduzido da data do post. O conteúdo tem direitos reservados: serve para consulta, não para republicar.
- **Livelo:** lê os dados que o site entrega embutidos em duas páginas: a lista de parceiros, com os pontos por real e as datas de cada promoção de acúmulo, e a vitrine de ofertas, com as campanhas de transferência e clube. Nas campanhas, o benefício vem só em texto e costuma não ter data de fim.
- **Esfera:** lê as campanhas de acúmulo pela mesma API que a página de campanhas usa. Entram só as campanhas de até 62 dias: as demais são a pontuação normal da loja ou ações internas. A Esfera não publica as promoções de transferência nesse formato.
- **Blogs (Passageiro de Primeira, Pontos pra Voar e Melhores Cartões):** os feeds RSS dão as notícias do dia, inclusive de programas sem fonte própria, como LATAM Pass e Azul. O feed não traz validade, então entram as notícias dos últimos 3 dias que citam um programa conhecido. Programa, tipo e benefício são deduzidos do título, e a coluna `fim` só é preenchida em "último dia" e "só hoje". Os feeds ficam em `config/selectors.toml`, onde dá para incluir outros.

LATAM Pass e Azul Fidelidade não têm fonte oficial acessível: os sites dos dois respondem HTTP 403 ao robô, inclusive no `robots.txt`, e o robô não contorna bloqueios. As promoções deles chegam pelo Radar PPV e pelos blogs, incluindo os feeds do Pontos pra Voar dedicados a cada um dos dois programas. Cada blog pode ter vários feeds, e uma notícia repetida entre eles entra uma vez.

## Situação das fontes

Resultado do último teste real, em 10/11/2026:

| Fonte | Situação |
| --- | --- |
| Google Hotels | Funciona |
| Google Maps | Funciona |
| Smiles | Funciona |
| Pontos pra Voar (Radar PPV) | Funciona |
| Livelo | Funciona |
| Esfera | Funciona |
| Feeds RSS dos blogs | Funcionam |
| LATAM Pass e Azul Fidelidade | Bloqueadas: respondem HTTP 403 ao navegador automatizado |
| Decolar | Bloqueada: responde HTTP 403 ao navegador automatizado |

O robô não tenta contornar bloqueios. Ele registra a recusa no resumo e segue com as demais fontes.

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `config/searches.toml` | Cidades, datas e parâmetros de execução |
| `config/selectors.toml` | Seletores CSS e endereços de cada site |
| `src/travelrobot/sources/` | Uma fonte por site: `parse_*` é puro e a classe cuida da navegação |
| `src/travelrobot/pipeline.py` | Ordem das etapas, isolamento de falhas e gravação |
| `src/travelrobot/parsing.py` | Conversão de preços, notas e distâncias |
| `src/travelrobot/storage.py` | Gravação de CSV e HTML |

## Testes

```powershell
pytest
```

Os testes usam HTML sintético e trechos reais salvos em `tests/fixtures/`, sem acessar a internet. Eles validam a lógica, não se os seletores ainda batem com os sites reais.

## Quando um site muda

Os sites trocam suas classes CSS com frequência. Se uma fonte passar a retornar zero resultados, abra a página com `--headed` e atualize `config/selectors.toml`.

Confira também os termos de uso de cada site antes de usar a coleta automatizada.
