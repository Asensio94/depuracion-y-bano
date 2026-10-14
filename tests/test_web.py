from wastewater.web import faecal_text, gap_sentences, plain_gap


def test_gap_sentences_carry_the_figures():
    a = {"collected": 90, "individual": 2, "untreated": 8, "failed": ["bod", "cod", "p"]}
    assert plain_gap("collection", a).startswith("El 8,0 % de sus aguas fecales")
    assert plain_gap("untreated", a) == "Vierte el 8,0 % de sus aguas fecales sin ningún tratamiento"
    assert plain_gap("secondary_performance", a).endswith("(DBO₅ y DQO por encima del límite)")
    assert plain_gap("stringent_performance", a) == "Vierte en una zona sensible más fósforo de lo permitido"


def test_faecal_limits_depend_on_the_water():
    assert "500 <i>E. coli</i> o más de 185" in faecal_text({"quality": "insuficiente", "type": "coastalBathingWater"})
    assert "900 <i>E. coli</i> o más de 330" in faecal_text({"quality": "insuficiente", "type": "riverBathingWater"})
    assert faecal_text({"quality": "buena", "type": "riverBathingWater"}) == ""


def test_uncollected_and_untreated_said_once():
    a = {"gaps": ["collection", "untreated"], "collected": 88, "individual": 0, "untreated": 12, "failed": []}
    assert gap_sentences(a) == [("collection", "El 12,0 % de sus aguas fecales no llega al alcantarillado y se vierte sin tratar")]
