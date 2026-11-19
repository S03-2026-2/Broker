from app.servidor.registro import RegistroDeEventos


def test_registra_com_ids_crescentes_e_campos():
    r = RegistroDeEventos()
    a = r.registrar("publicada", "t", "m1", detalhe="x")
    b = r.registrar("entregue", "t", "m1", "fila-1", 2)
    assert (a["id"], b["id"]) == (1, 2)
    assert b["tipo"] == "entregue" and b["destino"] == "fila-1" and b["tentativa"] == 2
    assert "hora" in a


def test_listar_desde_devolve_so_os_novos():
    r = RegistroDeEventos()
    for _ in range(5):
        r.registrar("publicada")
    assert [e["id"] for e in r.listar(desde=3)] == [4, 5]


def test_listar_limita_aos_mais_recentes():
    r = RegistroDeEventos()
    for _ in range(10):
        r.registrar("publicada")
    assert [e["id"] for e in r.listar(limite=3)] == [8, 9, 10]


def test_capacidade_descarta_os_mais_antigos():
    r = RegistroDeEventos(capacidade=3)
    for _ in range(5):
        r.registrar("publicada")
    assert [e["id"] for e in r.listar()] == [3, 4, 5]


def test_listar_devolve_copias():
    r = RegistroDeEventos()
    r.registrar("publicada")
    r.listar()[0]["tipo"] = "adulterado"
    assert r.listar()[0]["tipo"] == "publicada"
