import eltoque


def test_version_is_exposed() -> None:
    assert eltoque.__version__ == "0.1.0"


def test_all_names_resolve() -> None:
    for name in eltoque.__all__:
        assert hasattr(eltoque, name), name


def test_internal_helpers_are_not_exported() -> None:
    assert not any(name.startswith("_") and name != "__version__" for name in eltoque.__all__)
    assert "ClientConfig" not in eltoque.__all__
    assert "RetryPolicy" not in eltoque.__all__


def test_quickstart_shape_works_with_public_names_only() -> None:
    import httpx

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    with eltoque.ElToqueClient("fake.token", transport=transport) as client:
        assert client.get_latest_rates().data == {"ok": True}
