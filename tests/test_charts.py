from frontend.charts import figure


def spec(kind="line", values=(10, 20, 15)):
    return {
        "kind": kind,
        "x": "period" if kind == "line" else "condition",
        "y": "visits",
        "rows": [
            {"period": f"2026-07-{i + 1:02d}", "condition": f"Group {i + 1}", "visits": v}
            for i, v in enumerate(values)
        ],
    }


def test_line_values_are_visible_without_hover():
    chart = figure(spec())
    assert "text" in chart.data[0].mode
    assert list(chart.data[0].text) == ["10", "20", "15"]
    assert chart.data[0].cliponaxis is False
    assert chart.layout.yaxis.showticklabels is True
    assert chart.layout.yaxis.title.text == "Recorded visits"


def test_bar_values_have_room_even_for_negative_comparisons():
    chart = figure(spec("bar", (-50, 100, 0)))
    assert chart.data[0].textposition == "outside"
    assert chart.data[0].cliponaxis is False
    assert chart.layout.xaxis.range[0] < -50
    assert chart.layout.xaxis.range[1] > 100


def test_dense_timeline_labels_remain_readable():
    data = spec()
    data["rows"] = [{"period": f"Day {i}", "visits": i} for i in range(90)]
    chart = figure(data)
    assert len(chart.data[0].text) == 90
    assert 2 <= sum(bool(label) for label in chart.data[0].text) <= 16
    assert chart.data[0].text[-1] == "89"


def test_long_category_names_wrap_instead_of_clipping():
    data = spec("bar")
    data["rows"][0]["condition"] = "A long recorded condition label that should remain readable"
    chart = figure(data)
    assert "<br>" in chart.layout.yaxis.ticktext[0]
    assert chart.layout.yaxis.automargin is True


def test_empty_chart_is_an_empty_state():
    data = spec()
    data["rows"] = []
    assert figure(data) is None


def test_chat_chart_reserves_space_for_condition_and_axis_labels():
    data = spec("bar", (888, 698, 510, 469, 414))
    for row, label in zip(data["rows"], ["Respiratory", "Fever", "Other", "Digestive", "Skin"]):
        row["condition"] = label
    chart = figure(data)
    assert chart.layout.margin.l >= 100
    assert chart.layout.margin.b >= 64
    assert list(chart.layout.yaxis.ticktext) == ["Respiratory", "Fever", "Other", "Digestive", "Skin"]


def test_wrapped_categories_receive_enough_vertical_space():
    data = spec("bar")
    short = figure(data)
    for row in data["rows"]:
        row["condition"] = "A long recorded condition label that should remain readable"
    wrapped = figure(data)
    assert wrapped.layout.height > short.layout.height
