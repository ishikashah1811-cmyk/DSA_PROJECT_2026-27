import io
import json

from .conftest import make_client


def keys(obj):
    return set(obj)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "posts": 300}


def test_list_posts_shape_and_paging(client):
    r = client.get("/api/posts", params={"limit": 5, "offset": 0})
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 5
    assert keys(posts[0]) == {"id", "account", "caption", "timestamp", "hashtags", "likes", "comments", "followers"}
    page2 = client.get("/api/posts", params={"limit": 5, "offset": 5}).json()
    assert {p["id"] for p in posts}.isdisjoint({p["id"] for p in page2})
    assert client.get("/api/posts", params={"limit": 0}).status_code == 422


def test_import_csv(empty_client):
    csv_text = (
        "id,account,caption,timestamp,likes,comments,followers\n"
        "a1,ishika.shah,Sunset at the beach #goa,2025-01-01T10:00:00,10,2,500\n"
        "a2,ishika.shah,,2025-01-02T10:00:00,5,1,500\n"  # no caption -> skipped
        "a3,ishika.shah,Bad likes #x,2025-01-03T10:00:00,many,1,500\n"  # bad number -> skipped
        "a4,acc_07,Chai and rain #monsoon,1735725600,3,0,\n"  # unix timestamp, no followers
    )
    r = empty_client.post("/api/posts/import", files={"file": ("posts.csv", csv_text, "text/csv")})
    assert r.status_code == 200
    assert r.json() == {"imported": 2, "skipped": 2, "total_posts": 2}
    posts = {p["id"]: p for p in empty_client.get("/api/posts").json()}
    assert posts["a1"]["account"].startswith("acc_") and posts["a1"]["account"] != "ishika.shah"  # anonymized
    assert posts["a4"]["account"] == "acc_07" and posts["a4"]["followers"] is None
    assert posts["a1"]["hashtags"] == ["goa"]
    # Re-importing the same ids updates rather than duplicates.
    empty_client.post("/api/posts/import", files={"file": ("posts.csv", csv_text, "text/csv")})
    assert empty_client.get("/api/health").json()["posts"] == 2


def test_import_rejects_csv_without_caption_column(empty_client):
    r = empty_client.post("/api/posts/import", files={"file": ("x.csv", "id,text\n1,hello\n", "text/csv")})
    assert r.status_code == 422


def test_import_instagram_export_json(empty_client):
    export = [
        {"media": [{"uri": "media/posts/1.jpg", "creation_timestamp": 1735725600,
                    "title": "CafÃ© date ð\u009f\u0094¥ #coffee"}]},
        {"title": "Carousel day #travel #goa", "creation_timestamp": 1735812000,
         "media": [{"uri": "a.jpg", "creation_timestamp": 1735812000, "title": ""}]},
        {"media": [{"uri": "media/posts/3.jpg", "creation_timestamp": 1735898400, "title": ""}]},  # no caption
    ]
    r = empty_client.post(
        "/api/posts/import",
        files={"file": ("posts_1.json", json.dumps(export), "application/json")},
        data={"account": "my.handle", "followers": "1200"},
    )
    assert r.status_code == 200 and r.json() == {"imported": 2, "skipped": 1, "total_posts": 2}
    posts = empty_client.get("/api/posts").json()
    assert posts[0]["caption"] == "Café date 🔥 #coffee"  # mojibake repaired
    assert posts[1]["hashtags"] == ["travel", "goa"]
    assert all(p["followers"] == 1200 and p["account"].startswith("acc_") for p in posts)


def test_import_graph_api_json(empty_client):
    doc = {"data": [{"id": "1789", "caption": "Launch #sale", "timestamp": "2025-02-01T09:00:00+0000",
                     "like_count": 40, "comments_count": 3}]}
    r = empty_client.post("/api/posts/import", files={"file": ("media.json", json.dumps(doc), "application/json")})
    assert r.json()["imported"] == 1
    post = empty_client.get("/api/posts").json()[0]
    assert (post["id"], post["likes"], post["comments"]) == ("1789", 40, 3)
    bad = empty_client.post("/api/posts/import", files={"file": ("x.json", "{not json", "application/json")})
    assert bad.status_code == 422


def test_duplicates_run_and_clusters(client):
    r = client.post("/api/duplicates/run", json={"shingle_type": "char", "k": 4, "num_hashes": 128,
                                                  "bands": 32, "rows": 4, "threshold": 0.6})
    assert r.status_code == 200
    run = r.json()
    assert keys(run) == {"run_id", "n_posts", "n_flagged", "n_exact_groups", "n_candidates", "n_pairs",
                         "n_clusters", "runtime_ms"}
    assert run["n_posts"] == 300 and run["n_clusters"] > 0
    clusters = client.get("/api/duplicates/clusters").json()  # latest run
    assert len(clusters) == run["n_clusters"]
    assert keys(clusters[0]) == {"cluster_id", "size", "post_ids", "representative_id", "representative_caption",
                                 "min_sim", "avg_sim"}
    assert client.get("/api/duplicates/clusters", params={"run_id": run["run_id"]}).json() == clusters
    # Defaults when no body is sent.
    assert client.post("/api/duplicates/run").json()["n_clusters"] == run["n_clusters"]


def test_duplicates_errors(client, empty_client):
    assert empty_client.get("/api/duplicates/clusters").status_code == 404
    assert client.get("/api/duplicates/clusters", params={"run_id": 999}).status_code == 404
    r = client.post("/api/duplicates/run", json={"bands": 10, "rows": 4, "num_hashes": 128})
    assert r.status_code == 422 and "bands * rows" in r.json()["detail"]
    assert client.post("/api/duplicates/run", json={"threshold": 1.5}).status_code == 422
    assert empty_client.post("/api/duplicates/run").json()["n_posts"] == 0


def test_hashtag_suggest(client):
    r = client.get("/api/hashtags/suggest", params={"prefix": "#tr", "k": 3})
    assert r.status_code == 200
    tags = r.json()
    assert 1 <= len(tags) <= 3 and keys(tags[0]) == {"tag", "count"}
    assert all(t["tag"].startswith("tr") for t in tags)
    assert [t["count"] for t in tags] == sorted((t["count"] for t in tags), reverse=True)
    assert client.get("/api/hashtags/suggest", params={"prefix": "zzzz"}).json() == []


def test_hashtag_top(client):
    r = client.get("/api/hashtags/top", params={"k": 5, "min_count": 3})
    assert r.status_code == 200
    top = r.json()
    assert len(top) == 5 and keys(top[0]) == {"tag", "count", "mean_engagement", "score"}
    assert [t["score"] for t in top] == sorted((t["score"] for t in top), reverse=True)
    assert all(t["count"] >= 3 for t in top)
    assert client.get("/api/hashtags/top", params={"k": 0}).status_code == 422


def test_benchmark(client, tmp_path):
    rows = client.get("/api/benchmark").json()
    assert rows and keys(rows[0]) == {"n", "brute_ms", "lsh_ms", "recall", "candidates"}
    with make_client(tmp_path, "nobench", benchmark_path=tmp_path / "missing.json") as c:
        assert c.get("/api/benchmark").status_code == 404


def test_delete_posts_and_cors(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert client.delete("/api/posts").json()["total_posts"] == 0
    assert client.get("/api/health").json()["posts"] == 0
    assert client.get("/api/hashtags/suggest", params={"prefix": "t"}).json() == []


def test_upload_size_limit(tmp_path):
    with make_client(tmp_path, "small", seed_sample=False, max_upload_mb=0) as c:
        r = c.post("/api/posts/import", files={"file": ("big.csv", io.BytesIO(b"caption\nhello\n"), "text/csv")})
        assert r.status_code == 413
