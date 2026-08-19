from pathlib import Path

from quackvideo.domain.enums import ContentProfile, PipelineStage
from quackvideo.domain.models import ProjectConfig
from quackvideo.store import ArtifactStore, sha256_file, slugify


def test_slugify() -> None:
    assert slugify("Hello World!") == "hello-world"


def test_store_roundtrip(tmp_workspace: Path) -> None:
    store = ArtifactStore(ProjectConfig(workspace=tmp_workspace))
    state = store.create_episode("Pilot Episode", ContentProfile.PODCAST)
    loaded = store.load_state(state.episode_id)
    assert loaded.title == "Pilot Episode"
    assert loaded.profile == ContentProfile.PODCAST
    assert store.layout(state.episode_id).stage_dir(PipelineStage.INGEST).is_dir()


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "a.bin"
    path.write_bytes(b"hello")
    assert sha256_file(path) == sha256_file(path)
    assert len(sha256_file(path)) == 64
