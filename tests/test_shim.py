import io, json

from relic5 import shim


def fake_encode(texts, model):
    return [[0.6, 0.8] for _ in texts]


def test_semantic_search_gets_a_vector():
    m = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "relic_search", "arguments": {"query": "x", "semantic": True, "model": "m"}}}
    a = shim.add_vector(m, fake_encode)["params"]["arguments"]
    assert a["vector"] == [0.6, 0.8] and "model" not in a and a["semantic"]


def test_everything_else_passes_through():
    for m in ({"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
              {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "relic_search", "arguments": {"query": "x"}}},
              {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "relic_search", "arguments": {"query": "x", "semantic": True, "vector": [1]}}}):
        assert shim.add_vector(m, fake_encode) == m


def test_serve_forwards_and_reports_an_unreachable_hub(monkeypatch):
    sent = []
    monkeypatch.setattr(shim, "forward", lambda url, msg: sent.append(msg) or {"jsonrpc": "2.0", "id": msg.get("id"), "result": {}})
    out = io.StringIO()
    shim.serve("http://hub", io.StringIO('{"jsonrpc":"2.0","id":1,"method":"ping"}\nnot json\n'), out, fake_encode)
    lines = [json.loads(l) for l in out.getvalue().splitlines()]
    assert lines[0]["result"] == {} and lines[1]["error"]["code"] == -32700 and sent[0]["method"] == "ping"
    def boom(url, msg):
        raise OSError("down")
    monkeypatch.setattr(shim, "forward", boom)
    out = io.StringIO()
    shim.serve("http://hub", io.StringIO('{"jsonrpc":"2.0","id":5,"method":"tools/list"}\n'), out, fake_encode)
    assert "hub unreachable" in json.loads(out.getvalue())["error"]["message"]


def test_policy_chooses_by_backlog(tmp_path, monkeypatch):
    from relic5 import worker
    monkeypatch.setattr(worker, "CONFIG", str(tmp_path / "none.toml"))   # the defaults, not this machine's config
    monkeypatch.setattr(worker.sys, "platform", "darwin")   # the ANE/gb300 policy is the Mac's; off a Mac see the next test
    assert worker.choose(810_000)[0] == "gb300" and worker.choose(1_200)[0] == "ane"
    cfg = tmp_path / "config.toml"
    cfg.write_text('[embed]\nbacklog_gb300 = 1000\nsmall = "mps"\n')
    monkeypatch.setattr(worker, "CONFIG", str(cfg))
    assert worker.choose(1_200) == ("gb300", "backlog 1,200 > 1,000: gb300") and worker.choose(10)[0] == "mps"


def test_off_a_mac_the_local_engine_does_every_size(tmp_path, monkeypatch):
    """Ours (issue #4): no ANE and no gb300 here, so auto is the one sentence-transformers engine, at any backlog."""
    from relic5 import worker
    monkeypatch.setattr(worker, "CONFIG", str(tmp_path / "none.toml"))
    monkeypatch.setattr(worker.sys, "platform", "linux")
    monkeypatch.setenv("RELIC5_ENGINE", "cuda")
    assert worker.choose(810_000)[0] == "cuda" and worker.choose(5)[0] == "cuda" and worker.query_engines() == ["cuda"]


def test_default_engine_is_asked_then_cuda_then_mps(monkeypatch):
    import relic5.encode as E
    monkeypatch.setenv("RELIC5_ENGINE", "ane")
    assert E.default_engine() == "ane"
    monkeypatch.delenv("RELIC5_ENGINE")
    assert E.default_engine() in ("cuda", "mps")


def test_a_local_hub_takes_the_shard_without_ssh(tmp_path, monkeypatch):
    from relic5 import worker
    monkeypatch.delenv("RELIC5_HUB_SSH", raising=False)
    monkeypatch.setenv("RELIC5_URL", "http://127.0.0.1:8795")
    assert worker.hub_local()
    monkeypatch.setenv("RELIC5_URL", "http://hub.example:8795")
    assert not worker.hub_local()
    monkeypatch.setenv("RELIC5_HUB_SSH", "local")
    assert worker.hub_local()
    monkeypatch.setattr(worker, "ROOT", str(tmp_path))
    worker.note("start", "x")
    assert (tmp_path / "logs" / "jobs.jsonl").read_text().count("\n") == 1


def test_a_failed_query_embedding_is_said_in_the_reply(monkeypatch):
    """The fallback to keyword hits is never silent: the reason comes back in `note`, before the hub's own note."""
    import relic5.encode as E, relic5.worker as W
    monkeypatch.setattr(W.sys, "platform", "darwin")
    monkeypatch.setattr(W, "policy", lambda: {"query": ["ane"]})
    def down(texts, model, engine):
        raise ConnectionError("ANE engine busy")
    monkeypatch.setattr(E, "encode", down)
    seen = []
    def hub(url, msg):
        seen.append(msg)
        body = {"hits": [], "note": "semantic needs the query embedded by the client: these are keyword hits"}
        return {"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": json.dumps(body)}]}}
    monkeypatch.setattr(shim, "forward", hub)
    out = io.StringIO()
    req = {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "relic_search", "arguments": {"query": "x", "semantic": True}}}
    shim.serve("http://hub", io.StringIO(json.dumps(req) + "\n"), out, None)
    note = json.loads(json.loads(out.getvalue())["result"]["content"][0]["text"])["note"]
    assert note.startswith("query embedding failed on this Mac (ane: ConnectionError: ANE engine busy)")
    assert "keyword hits" in note.split(" · ", 1)[1] and "_embed_failed" not in seen[0]   # never sent to the hub


def test_hub_keeps_both_notes(root):
    from relic5 import mcp
    from relic5.query import Relic5
    import duckdb
    from relic5 import fts
    from relic5.parts import Parts
    con = duckdb.connect()
    Parts(root).index(con, log=lambda s: None)
    fts.build(root, con, log=lambda s: None)
    ok, r = mcp.call_tool(Relic5(root, con), "relic_search", {"query": "hub", "semantic": True, "limit": 1}, "loopback")
    assert ok and r["note"].startswith("semantic needs the query embedded")
