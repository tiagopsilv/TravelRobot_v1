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

As promoções saem em `FrequentFlyersList_AAAAMMDD.csv`, uma linha por promoção ainda válida, com todas as fontes e todas as colunas. Uma coluna fica vazia quando a fonte não traz aquele dado.

Cada fonte ganha também o seu próprio CSV em `output/Promocoes/`, por exemplo `FrequentFlyersList_Smiles_AAAAMMDD.csv` ou `FrequentFlyersList_PontosPraVoarRadarPPV_AAAAMMDD.csv`. Ele traz só as colunas que aquela fonte preenche, sempre na mesma ordem. Os blogs usam um layout comum de notícia. As colunas de cada arquivo estão em `SOURCE_COLUMNS` e `FEED_COLUMNS`, em `src/travelrobot/storage.py`.

| Grupo | Colunas |
| --- | --- |
| Identificação | `data_execucao`, `fonte`, `programa`, `parceiro`, `titulo`, `descricao`, `link` |
| Categorização | `tipo` (acúmulo, transferência, compra de pontos, clubes), `categoria` (do site ou do post: Viagem, moda, saúde...), `exclusivo_clube` (sim/não) |
| Benefício | `beneficio` (como o site descreve, por exemplo "Bonificação até 120%"), `valor` (o número), `unidade` (o que o número mede: `pontos por R$`, `pontos por US$`, `% de bônus`, `% de desconto` ou `pontos`) |
| Comparação | `valor_clube` (o valor para assinantes do clube), `valor_normal` (a pontuação fora da promoção), `multiplicador` (`valor` ÷ `valor_normal`) |
| Prazo | `publicado_em` (data do post, nos blogs e no Radar PPV), `inicio`, `hora_inicio`, `fim`, `hora_fim`, `duracao_dias` (só quando início e fim são conhecidos), `dias_restantes` (0 = acaba hoje) |
| Condições | `prazo_credito_dias` (quando os pontos caem), `cupom`, `regras` (trecho do regulamento) |

Compare `valor` só entre linhas da mesma `unidade`: 10 pontos por real e 10% de bônus não são comparáveis. As taxas são normalizadas para 1 unidade da moeda: "3 pontos a cada 2 reais" vira 1,5 pontos por R$. Em `exclusivo_clube`, "não" quer dizer que o texto oferece o benefício também a quem não assina o clube; vazio quer dizer que a fonte não informa ou que o texto é ambíguo, por exemplo quando oferece algo aos demais clientes e nega outra coisa na mesma frase. O robô deduz isso do texto, então confira o regulamento antes de decidir.

- **Smiles:** o robô abre a página de promoções e lê o JSON que a própria página baixa para montar os cartões, que traz datas de início e fim e categoria. Ele não chama essa API diretamente, porque o `robots.txt` da Smiles não permite URLs com parâmetros. Entram também as promoções já anunciadas que ainda vão começar, identificadas pela coluna `inicio`. As horas de início e fim vão para `hora_inicio` e `hora_fim`.
- **Radar PPV:** é lido pela API pública do WordPress do Pontos pra Voar, que publica o resumo à noite, então pela manhã o robô usa o do dia anterior e descarta as linhas já vencidas. Cobre acúmulo por real gasto, transferência bonificada, compra de pontos e clubes de vários programas. A validade vem sem ano, que é deduzido da data do post. O conteúdo tem direitos reservados: serve para consulta, não para republicar.
- **Livelo:** lê os dados que o site entrega embutidos em duas páginas: a lista de parceiros, com os pontos por real e as datas de cada promoção de acúmulo, e a vitrine de ofertas, com as campanhas de transferência e clube. Nas campanhas, o benefício vem só em texto e costuma não ter data de fim.
- **Esfera:** lê as campanhas de acúmulo pela mesma API que a página de campanhas usa. Entram só as campanhas de até 62 dias: as demais são a pontuação normal da loja ou ações internas. A Esfera não publica as promoções de transferência nesse formato.
- **Blogs (Passageiro de Primeira, Pontos pra Voar e Melhores Cartões):** os feeds RSS dão as notícias do dia, inclusive de programas sem fonte própria, como LATAM Pass e Azul. O feed não traz validade, então entram as notícias dos últimos 3 dias que citam um programa conhecido. Programa, tipo e benefício são deduzidos do título, e a coluna `fim` só é preenchida em "último dia" e "só hoje". Os feeds ficam em `config/selectors.toml`, onde dá para incluir outros.

LATAM Pass e Azul Fidelidade não têm fonte oficial acessível: os sites dos dois respondem HTTP 403 ao robô, inclusive no `robots.txt`, e o robô não contorna bloqueios. As promoções deles chegam pelo Radar PPV e pelos blogs, incluindo os feeds do Pontos pra Voar dedicados a cada um dos dois programas. Cada blog pode ter vários feeds, e uma notícia repetida entre eles entra uma vez.

## Situação das fontes

Resultado do último teste real, em 13/11/2026:

| Fonte | Situação |
| --- | --- |
| Google Hotels | Funciona |
| Google Maps | Funciona |
| Smiles | Funciona |
| Pontos pra Voar (Radar PPV) | Funciona |
| Livelo | Bloqueada em 13/11/2026: respondeu HTTP 403 nas duas páginas (funcionava em 12/11) |
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
