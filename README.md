# TravelRobot

Coleta preços e avaliações de hotéis (Google Hotels e Decolar), distância até um ponto de referência (Google Maps) e promoções de milhas (Smiles). O resultado sai em CSV e HTML.

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

## Situação das fontes

Resultado do último teste real, em 06/11/2026:

| Fonte | Situação |
| --- | --- |
| Google Hotels | Funciona |
| Google Maps | Funciona |
| Smiles | Funciona |
| Decolar | Bloqueada: responde HTTP 403 ao navegador automatizado |

O robô não tenta contornar bloqueios. Ele registra a recusa no resumo e segue com as demais fontes.

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `config/searches.toml` | Cidades, datas e parâmetros de execução |
| `config/selectors.toml` | Seletores CSS de cada site |
| `src/travelrobot/sources/` | Uma fonte por site: `parse_*` é puro e a classe cuida da navegação |
| `src/travelrobot/pipeline.py` | Ordem das etapas, isolamento de falhas e gravação |
| `src/travelrobot/parsing.py` | Conversão de preços, notas e distâncias |
| `src/travelrobot/storage.py` | Gravação de CSV e HTML |

## Testes

```powershell
pytest
```

Os testes usam HTML sintético e não acessam a internet. Eles validam a lógica, não se os seletores ainda batem com os sites reais.

## Quando um site muda

Os sites trocam suas classes CSS com frequência. Se uma fonte passar a retornar zero resultados, abra a página com `--headed` e atualize `config/selectors.toml`.

Confira também os termos de uso de cada site antes de usar a coleta automatizada.
