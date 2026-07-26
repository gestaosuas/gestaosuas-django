import unicodedata

def strip_accents(text):
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    )


MONTH_LABELS = [
    (1, "JAN"),
    (2, "FEV"),
    (3, "MAR"),
    (4, "ABR"),
    (5, "MAI"),
    (6, "JUN"),
    (7, "JUL"),
    (8, "AGO"),
    (9, "SET"),
    (10, "OUT"),
    (11, "NOV"),
    (12, "DEZ"),
]

MONTH_OPTIONS = [
    (1, "Janeiro"),
    (2, "Fevereiro"),
    (3, "Marco"),
    (4, "Abril"),
    (5, "Maio"),
    (6, "Junho"),
    (7, "Julho"),
    (8, "Agosto"),
    (9, "Setembro"),
    (10, "Outubro"),
    (11, "Novembro"),
    (12, "Dezembro"),
]


def build_sparkline(values, width=92, height=34):
    if not values:
        return ""
    max_value = max(values) or 1
    step = width / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x_pos = round(index * step, 2)
        y_pos = round(height - ((value / max_value) * (height - 4)) - 2, 2)
        points.append(f"{x_pos},{y_pos}")
    return " ".join(points)


def build_column_points(values):
    peak = max(values) or 1
    return [
        {
            "label": label,
            "value": values[index],
            "height": max(10, round((values[index] / peak) * 100)) if values[index] else 10,
        }
        for index, (_month_num, label) in enumerate(MONTH_LABELS)
    ]


def build_donut_style(items):
    if not items:
        return "conic-gradient(#dbe5f3 0deg 360deg)"

    total = sum(item["value"] for item in items) or 1
    current = 0
    segments = []
    for item in items:
        span = (item["value"] / total) * 360
        start = round(current, 2)
        current += span
        end = round(current, 2)
        segments.append(f"{item['color']} {start}deg {end}deg")
    return "conic-gradient(" + ", ".join(segments) + ")"


def month_name_from_number(month):
    for month_num, label in MONTH_LABELS:
        if month_num == month:
            return label
    return str(month)


def build_period_label(selected_year, selected_month):
    if selected_month == "all":
        return f"JAN - DEZ {selected_year}"
    try:
        month_val = int(selected_month)
        return f"{month_name_from_number(month_val)} {selected_year}"
    except (ValueError, TypeError):
        return f"{selected_month} {selected_year}"


def build_year_range_from_years(years, fallback_year):
    numeric_years = sorted({int(year) for year in years if year}, reverse=True)
    if not numeric_years:
        return [fallback_year]
    if fallback_year not in numeric_years:
        numeric_years.insert(0, fallback_year)
    return numeric_years


def build_variation(values, selected_month):
    if not values:
        return None

    if selected_month != "all":
        try:
            current_index = max(0, int(selected_month) - 1)
            if current_index == 0:
                return None
            current_value = values[current_index]
            previous_value = values[current_index - 1]
        except (ValueError, TypeError):
            return None
    else:
        # Simplificacao para o 'all': comparar ultimo mes preenchido com o anterior?
        # Por enquanto mantendo nulo para 'all' para evitar complexidade extra
        return None

    if previous_value == 0:
        return {"value": 100, "is_up": True} if current_value > 0 else None
    
    diff = ((current_value - previous_value) / previous_value) * 100
    return {
        "value": abs(round(diff, 1)),
        "is_up": diff > 0,
    }


def safe_total(report, field_name):
    value = getattr(report, field_name, 0) if report else 0
    return int(value or 0)


def build_series(reports_by_month, field_name):
    return [safe_total(reports_by_month.get(month_num), field_name) for month_num, _label in MONTH_LABELS]


def build_series_or_none(reports_by_month, field_name):
    """Como build_series(), mas retorna None (nao 0) pros meses sem nenhuma
    linha de relatorio - permite o grafico desenhar uma lacuna real em vez de
    fingir que o valor foi zero. Nao reaproveita build_series() por design:
    troque com cuidado, essa distincao None-vs-0 e o ponto inteiro da funcao."""
    return [
        safe_total(reports_by_month[month_num], field_name) if month_num in reports_by_month else None
        for month_num, _label in MONTH_LABELS
    ]


def build_variation_or_none(reports_by_month, field_name, selected_month):
    """Variante de build_variation() que parte de reports_by_month (nao de uma
    serie ja achatada por build_series()) para distinguir "mes sem relatorio"
    de "mes com valor 0 real". No modo "all" (Ano Inteiro), compara o ultimo
    mes com relatorio lancado contra o mes imediatamente anterior a ele, em
    vez de sempre desistir (None) como build_variation() faz. Nunca fabrica
    uma comparacao contra um mes sem relatorio - se o mes anterior ao mes
    "atual" nao tem linha nenhuma, retorna None."""
    if selected_month != "all":
        try:
            current_month_num = int(selected_month)
        except (ValueError, TypeError):
            return None
        if current_month_num <= 1 or current_month_num not in reports_by_month:
            return None
        previous_month_num = current_month_num - 1
    else:
        reported_months = sorted(reports_by_month.keys())
        if len(reported_months) < 2:
            return None
        current_month_num = reported_months[-1]
        previous_month_num = current_month_num - 1

    if previous_month_num not in reports_by_month:
        return None

    current_value = safe_total(reports_by_month.get(current_month_num), field_name)
    previous_value = safe_total(reports_by_month.get(previous_month_num), field_name)

    if previous_value == 0:
        return {"value": 100, "is_up": True} if current_value > 0 else None

    diff = ((current_value - previous_value) / previous_value) * 100
    return {
        "value": abs(round(diff, 1)),
        "is_up": diff > 0,
    }


def current_or_total(reports_by_month, field_name, selected_month):
    if selected_month != "all":
        try:
            return safe_total(reports_by_month.get(int(selected_month)), field_name)
        except (ValueError, TypeError):
            return 0
    return sum(build_series(reports_by_month, field_name))


def sum_fields(report, fields):
    if not report:
        return 0
    total = 0
    for field_name in fields:
        total += int(getattr(report, field_name, 0) or 0)
    return total


def sum_fields_by_month(reports_by_month, fields):
    return [sum_fields(reports_by_month.get(month_num), fields) for month_num, _label in MONTH_LABELS]


def selected_or_total_fields(reports_by_month, fields, selected_month):
    if selected_month == "all":
        return sum(sum_fields_by_month(reports_by_month, fields))
    try:
        return sum_fields(reports_by_month.get(int(selected_month)), fields)
    except (ValueError, TypeError):
        return 0


def build_highlight_badge(items, empty_label="Sem destaque"):
    populated_items = [item for item in items if item.get("value", 0) > 0]
    if not populated_items:
        return {"label": empty_label, "value": ""}
    lead = max(populated_items, key=lambda x: x["value"])
    return {"label": lead["label"], "value": lead["value"]}
