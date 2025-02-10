from flask import jsonify
import re
import time
from playwright.sync_api import sync_playwright

# Função para preencher o formulário
def preencher_formulario(page, valor, data_inicio, data_fim, indice_value, indice):
    page.fill("#txt1", f"{valor:.2f}")
    selecionar_data(page, "#comboDataAno2", "#comboDataMes2", "#comboDataDia2", data_inicio)
    selecionar_data(page, "#comboDataAno3", "#comboDataMes3", "#comboDataDia3", data_fim)

    try:
        page.select_option("#comboIndice4", value=indice_value)
    except:
        page.locator(f"//select[@id='comboIndice4']//option[contains(text(), '{indice}')]").click()

# Função para selecionar as datas
def selecionar_data(page, ano_seletor, mes_seletor, dia_seletor, data):
    dia, mes, ano = data.split("/")
    page.select_option(ano_seletor, ano)
    page.select_option(mes_seletor, mes)
    page.select_option(dia_seletor, dia)

# Função para capturar os dados da página
def capturar_dados(page):
    page.wait_for_selector("p:has-text('Os valores do índice utilizados neste cálculo foram')", timeout=10000)
    time.sleep(2)
    return " ".join(page.locator("p").all_text_contents())

# Função para capturar o valor atualizado
def capturar_valor_atualizado(page):
    try:
        elemento_valor = page.locator("b:has-text('Valor atualizado')").text_content()
        valor_atualizado = re.search(r"R\$\s*([\d,.]+)", elemento_valor)
        return valor_atualizado.group(1).replace(".", "").replace(",", ".") if valor_atualizado else None
    except:
        return None

# Função para extrair percentuais mensais corretamente
def extrair_percentuais(texto_completo):
    percentuais_mensais = []
    menor_percentual = None
    maior_percentual = None

    try:
        valores_texto = re.findall(r"([A-Za-zç]+-\d{4})\s=\s([-+]?\d+,\d+)%", texto_completo)

        def mes_para_numero(mes):
            meses = {
                "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Marco": 3, "Abril": 4, "Maio": 5, "Junho": 6,
                "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
            }
            return meses.get(mes, 0)

        valores_ordenados = sorted(
            valores_texto,
            key=lambda x: (int(x[0].split("-")[1]), mes_para_numero(x[0].split("-")[0]))

        )

        for mes_ano, percentual in valores_ordenados:
            percentual = percentual.replace(",", ".")
            percentuais_mensais.append([mes_ano, percentual])

            num_percentual = float(percentual)
            if menor_percentual is None or num_percentual < menor_percentual[1]:
                menor_percentual = (mes_ano, num_percentual)
            if maior_percentual is None or num_percentual > maior_percentual[1]:
                maior_percentual = (mes_ano, num_percentual)

    except:
        percentuais_mensais = []
        menor_percentual = None
        maior_percentual = None

    return percentuais_mensais, menor_percentual, maior_percentual

# Função principal para processar os dados
def processar_dados(dados):
    try:
        valor = float(dados.get("valor", 0))
        data_inicio = dados.get("dataInicio", "")
        data_fim = dados.get("dataFim", "")
        indice = dados.get("indice", "")
        indice_value = indice.replace("-", "").lower()

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=False)
            page = browser.new_page()
            page.goto("https://calculoexato.com.br/menu.aspx", wait_until="domcontentloaded")

            page.click("a[title='Cálculos financeiros']")
            page.click("text=Atualização de um valor por um índice financeiro")
            page.wait_for_selector("#txt1", timeout=5000)

            preencher_formulario(page, valor, data_inicio, data_fim, indice_value, indice)
            page.click("#btnContinuar")

            texto_completo = capturar_dados(page)

            valor_atualizado = capturar_valor_atualizado(page)
            if valor_atualizado is None:
                valor_atualizado = f"{valor:.2f}".replace(".", ",") 

            percentual_final = re.search(r"Em percentual:\s+([\d,]+)%", texto_completo)
            fator_multiplicacao = re.search(r"Em fator de multiplicação:\s+([\d,]+)", texto_completo)

            percentual_final = percentual_final.group(1).replace(".", ",") if percentual_final else None
            fator_multiplicacao = fator_multiplicacao.group(1).replace(",", ".") if fator_multiplicacao else None

            percentuais_mensais, menor_percentual, maior_percentual = extrair_percentuais(texto_completo)

            browser.close()

            resultado = {
                "success": "TRUE",
                "valor_original": f"{valor:.2f}",
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "indice": indice,
                "valor_atualizado": valor_atualizado,
                "percentual_final": percentual_final,
                "fator_multiplicacao": fator_multiplicacao,
                "percentuais_mensais": percentuais_mensais,
                "menor_percentual": f"{menor_percentual[0]} = {str(menor_percentual[1]).replace('.', ',')}%" if menor_percentual else "Erro ao capturar os percentuais.",
                "maior_percentual": f"{maior_percentual[0]} = {str(maior_percentual[1]).replace('.', ',')}%" if maior_percentual else "Erro ao capturar os percentuais.",
                "mensagem": "Consulta realizada com sucesso!"
            }

            return jsonify(resultado)

    except ModuleNotFoundError as e:
        return jsonify({"success": "FALSE", "mensagem": str(e)})
    except Exception as e:
        return jsonify({"success": "FALSE", "mensagem": f"Erro inesperado: {str(e)}"})
