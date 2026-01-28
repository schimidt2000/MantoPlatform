from flask import Blueprint, render_template, request
from flask_login import login_required

tools_bp = Blueprint("tools", __name__)


def br_money(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_van(num_colab: int, km_ida: float, carretinha: str, show: bool):
    km_total = km_ida * 2
    tarifa = 5.5 if carretinha == "1" else 6.3
    vt = km_total * tarifa
    afsp = (num_colab * km_total) / 3
    ashow = (km_total / 6) if (show and km_total > 500) else 0
    total = vt + afsp + ashow
    calc = [
        f"Transporte = km_total x tarifa = {km_total:.0f} x {tarifa:.2f}",
        f"Adicional fora SP = colaboradores x km_total / 3 = {num_colab} x {km_total:.0f} / 3",
    ]
    if ashow:
        calc.append(f"Adicional show = km_total / 6 = {km_total:.0f} / 6")
    calc.append("Valor final = transporte + adicional fora SP" + (" + adicional show" if ashow else ""))
    return vt, afsp, ashow, total, calc


def calcular_carro(num_carros: int, num_colab: int, km_ida: float, show: bool):
    km_total = km_ida * 2
    vt = num_carros * 1.9 * km_total
    afsp = (num_colab * km_total) / 3
    ashow = (km_total / 6) if (show and km_total > 500) else 0
    total = vt + afsp + ashow
    calc = [
        f"Transporte = carros x 1,9 x km_total = {num_carros} x 1,9 x {km_total:.0f}",
        f"Adicional fora SP = colaboradores x km_total / 3 = {num_colab} x {km_total:.0f} / 3",
    ]
    if ashow:
        calc.append(f"Adicional show = km_total / 6 = {km_total:.0f} / 6")
    calc.append("Valor final = transporte + adicional fora SP" + (" + adicional show" if ashow else ""))
    return vt, afsp, ashow, total, calc


@tools_bp.route("/tools/calculadora-transporte", methods=["GET", "POST"])
@login_required
def calculadora_transporte():
    modo_get = (request.args.get("modo") or "van").lower()
    form = {
        "modo": modo_get,
        "num_colaboradores": "",
        "num_carros": "",
        "km_ida": "",
        "carretinha": "",
        "show": "",
    }

    resultado = None
    resumo = None
    if request.method == "POST":
        form.update(request.form.to_dict())
        try:
            km_ida = float(form["km_ida"])
            show = form.get("show") == "1"
            if form["modo"] == "van":
                vt, afsp, ashow, total, calc = calcular_van(
                    int(form["num_colaboradores"]),
                    km_ida,
                    form["carretinha"],
                    show,
                )
            else:
                vt, afsp, ashow, total, calc = calcular_carro(
                    int(form["num_carros"]),
                    int(form["num_colaboradores"]),
                    km_ida,
                    show,
                )
            resultado = br_money(total)
            resumo = {
                "valor_transporte": br_money(vt),
                "adicional_fora": br_money(afsp),
                "adicional_show": br_money(ashow),
                "calculo_linhas": calc,
            }
        except Exception as exc:
            resultado = f"Erro: {exc}"

    return render_template(
        "tools/transport_calculator.html",
        form=form,
        resultado=resultado,
        resumo=resumo,
    )
