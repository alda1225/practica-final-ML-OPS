from src.datos import VARIABLES, dividir, generar, huella


def test_generacion_y_division_reproducibles():
    datos = generar()
    assert huella(datos) == huella(generar())
    assert len(VARIABLES) == 5 and len(datos) == 3000
    train, val, test = dividir(datos)
    assert [len(x) for x in (train, val, test)] == [1800, 600, 600]
    assert set(train.index).isdisjoint(val.index)
    assert set(train.index).isdisjoint(test.index)
    assert set(val.index).isdisjoint(test.index)
    for parte in (train, val, test):
        assert abs(parte.moroso.mean() - datos.moroso.mean()) < 0.01
