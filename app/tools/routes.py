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
    result = None
    if request.method == "POST":
        f = request.form
        try:
            mode = (f.get("mode") or "van").lower()
            km_ida = float(f.get("km") or 0)
            show = f.get("show") == "1"
            num_colab = int(f.get("num_colaboradores") or 0)

            if mode == "van":
                carretinha = f.get("carretinha", "")
                vt, afsp, ashow, total, calc = calcular_van(num_colab, km_ida, carretinha, show)
            else:
                num_carros = int(f.get("num_carros") or 0)
                vt, afsp, ashow, total, calc = calcular_carro(num_carros, num_colab, km_ida, show)

            breakdown = []
            breakdown.append(f"Transporte: R$ {br_money(vt)}")
            breakdown.append(f"Adicional fora SP: R$ {br_money(afsp)}")
            if ashow:
                breakdown.append(f"Adicional show: R$ {br_money(ashow)}")
            breakdown += calc

            result = {
                "mode": mode,
                "total": br_money(total),
                "breakdown": breakdown,
                "num_colaboradores": f.get("num_colaboradores", ""),
                "num_carros": f.get("num_carros", ""),
                "km": f.get("km", ""),
                "carretinha": f.get("carretinha") == "1",
                "show": show,
            }
        except Exception as exc:
            result = {"mode": f.get("mode", "van"), "total": f"Erro: {exc}", "breakdown": []}

    return render_template("tools/transport_calculator.html", result=result)
